"""End-to-end request path: contract -> route -> generate -> verify -> store.

One attempt per tier, maximum two attempts: local first, remote escalation
only when Layer 1 rejects the local response. Every attempt writes its own
replayable trajectory row. Layer 3 audit (sampled, offline, never inline)
attaches after this path returns — it must never gate the live response.
"""

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
        self.router.record_signal(category, verification.passed)

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

        response = provider.generate(request_id, task_input, contract)
        verification = verify(response, contract)
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
                response = self.remote.generate(request_id, task_input, contract)
                verification = verify(response, contract)
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
