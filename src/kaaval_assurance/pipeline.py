"""End-to-end request path: contract -> route -> generate -> verify -> store.

One attempt per request, or two attempts when local-first routing fails Layer 1:
the router may pre-route high-drift categories directly to remote, otherwise
it tries local first and escalates only when Layer 1 rejects the local response.
Every attempt writes its own replayable trajectory row. Layer 3 audit (sampled, offline, never inline)
attaches after this path returns — it must never gate the live response.

This boundary fails closed. A provider that raises (timeout, connection
refused, HTTP error) is not an escaped exception: the attempt is recorded as
a failed trajectory row with a `transport:<ExceptionType>` failure ID, and a
local transport failure escalates exactly like a Layer-1 rejection. Transport
failures feed the same Layer-2 signal as verification failures on purpose: a
local tier that keeps timing out should lose traffic to the remote tier just
like one that keeps producing malformed output.
"""

import time
import uuid
from typing import Optional

from .contracts import get_contract
from .models import (
    ModelResponse,
    PipelineResult,
    RoutingDecision,
    VerificationResult,
)
from .providers import Provider
from .router import Router
from .trajectory import TrajectoryStore
from .verifier import verify
from .models import TrajectoryRow


class AssurancePipeline:
    def __init__(
        self,
        router: Router,
        local_provider: Provider,
        remote_provider: Provider,
        store: TrajectoryStore,
    ):
        self.router = router
        self.local = local_provider
        self.remote = remote_provider
        self.store = store

    def _record(
        self,
        response: ModelResponse,
        verification: VerificationResult,
        contract_id: str,
        contract_version: str,
        category: str,
        task_input: str,
        escalated: bool,
    ) -> None:
        self.store.append(
            TrajectoryRow(
                request_id=response.request_id,
                category=category,
                contract_id=contract_id,
                contract_version=contract_version,
                tier=response.tier,
                provider=response.provider,
                model_id=response.model_id,
                verifier_passed=verification.passed,
                verifier_failures=verification.failures,
                escalated=escalated,
                latency_ms=response.latency_ms,
                cost_usd=response.cost_usd,
                prompt_tokens=response.prompt_tokens,
                completion_tokens=response.completion_tokens,
                task_input=task_input,
                raw_text=response.raw_text,
            )
        )
        self.router.record_signal(category, verification.passed, response.tier)

    def _attempt(
        self, provider: Provider, request_id: str, task_input: str, contract
    ) -> tuple[ModelResponse, VerificationResult]:
        """One generation attempt that never raises.

        A provider/transport failure becomes a failed attempt with a
        `transport:<ExceptionType>` check ID and parsed=None — recorded and
        routed like any other Layer-1 failure, never an escaped exception.
        """
        started = time.perf_counter()
        try:
            response = provider.generate(request_id, task_input, contract)
        except Exception as e:  # any provider failure is an infra failure here
            response = ModelResponse(
                request_id=request_id,
                provider=provider.provider_name,
                model_id=provider.model_id,
                tier=provider.tier,
                raw_text=f"[transport failure] {type(e).__name__}: {e}",
                parsed=None,
                latency_ms=(time.perf_counter() - started) * 1000.0,
            )
            verification = VerificationResult(
                passed=False,
                checks_run=0,
                failures=[f"transport:{type(e).__name__}"],
            )
            return response, verification
        return response, verify(response, contract, task_input)

    def handle_request(
        self,
        task_input: str,
        contract_id: str,
        contract_version: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> PipelineResult:
        request_id = request_id or str(uuid.uuid4())
        contract = get_contract(contract_id, contract_version)

        routing = self.router.choose_tier(contract.category)
        provider = self.local if routing.tier == "local" else self.remote

        response, verification = self._attempt(
            provider, request_id, task_input, contract
        )
        attempts = 1
        escalated = False
        self._record(
            response,
            verification,
            contract.contract_id,
            contract.version,
            contract.category,
            task_input,
            escalated=False,
        )

        if routing.tier == "local":
            escalation = self.router.should_escalate(contract.category, verification)
            if escalation is not None:
                routing = escalation
                escalated = True
                response, verification = self._attempt(
                    self.remote, request_id, task_input, contract
                )
                attempts += 1
                self._record(
                    response,
                    verification,
                    contract.contract_id,
                    contract.version,
                    contract.category,
                    task_input,
                    escalated=True,
                )

        return PipelineResult(
            request_id=request_id,
            response=response,
            verification=verification,
            routing=routing,
            escalated=escalated,
            attempts=attempts,
        )
