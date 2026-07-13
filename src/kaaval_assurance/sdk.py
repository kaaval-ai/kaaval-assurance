"""Tier-0 SDK: in-process assurance with zero infrastructure change.

The adoption path for teams that will not put a proxy in front of
production traffic on day one. Wrap the function that produces a model
answer; Kaaval verifies the answer against an explicit task contract and
writes a replayable receipt. Nothing else about the call path changes.

    from kaaval_assurance.sdk import Kaaval, NoSafeAnswer

    kaaval = Kaaval(mode="shadow", receipts="kaaval-receipts.db")

    @kaaval.assure(contract="support.refund_decision")
    def decide_refund(task_input: str) -> str:
        return client.chat.completions.create(...).choices[0].message.content

Semantics, deliberately narrow (this is Tier 0 — no routing, no escalation):

- ``shadow`` mode NEVER changes behavior: the wrapped function's return
  value passes through untouched, conformant or not. Kaaval only records
  what it saw. This is the design-partner motion: run for two weeks, then
  read the receipts.
- ``enforce`` mode fails closed on answers: a non-conformant answer raises
  :class:`NoSafeAnswer` carrying the failed check IDs and receipt id —
  a typed failure, never an unsafe value with a warning flag.
- Exceptions raised by the wrapped function itself are recorded as
  ``provider_error`` receipts and re-raised unchanged in BOTH modes:
  Kaaval never swallows or transforms the caller's own infrastructure
  failures (fail-open for infra, fail-closed for answers).

Escalation, drift routing, and the sampled audit remain the pipeline /
gateway tier's job. The SDK reuses the same verifier and receipt store —
one engine, two entry points.
"""

from __future__ import annotations

import functools
import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Literal, Optional, TypeVar, Union

from .contracts import get_contract
from .models import ModelResponse, TrajectoryRow, VerificationResult
from .trajectory import TrajectoryStore
from .verifier import verify

F = TypeVar("F", bound=Callable[..., Any])

Mode = Literal["shadow", "enforce"]


class NoSafeAnswer(Exception):
    """Enforce-mode terminal outcome: the answer failed its contract.

    Carries everything needed to act on the failure programmatically —
    the caller decides whether to escalate, queue for human review, or
    return a typed refusal to its own downstream.
    """

    def __init__(
        self, contract_id: str, failures: list[str], receipt_id: str
    ) -> None:
        self.contract_id = contract_id
        self.failures = list(failures)
        self.receipt_id = receipt_id
        super().__init__(
            f"answer failed contract {contract_id!r} "
            f"(checks: {', '.join(failures)}); receipt {receipt_id}"
        )


@dataclass
class Decision:
    """What one assured call produced. Returned by ``last_decision()``."""

    receipt_id: str
    contract_id: str
    mode: Mode
    conformant: bool
    failures: list[str] = field(default_factory=list)
    checks_run: int = 0
    latency_ms: float = 0.0
    attempt_status: str = "completed"


def _to_raw_text(value: Any) -> str:
    """Model output as verbatim text for the receipt and the parser."""
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value)
    except (TypeError, ValueError):
        return str(value)


def _parse(value: Any) -> Optional[dict]:
    """Best-effort dict for the verifier, mirroring provider parsing."""
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except (ValueError, TypeError):
            return None
        return parsed if isinstance(parsed, dict) else None
    return None


class Kaaval:
    """In-process assurance: one instance per receipt store + mode."""

    def __init__(
        self,
        mode: Mode = "shadow",
        receipts: Union[str, TrajectoryStore] = ":memory:",
        provider_name: str = "sdk",
        model_id: str = "unspecified",
    ) -> None:
        if mode not in ("shadow", "enforce"):
            raise ValueError("mode must be 'shadow' or 'enforce'")
        self.mode: Mode = mode
        self._own_store = not isinstance(receipts, TrajectoryStore)
        self.store = (
            receipts
            if isinstance(receipts, TrajectoryStore)
            else TrajectoryStore(receipts, check_same_thread=False)
        )
        self.provider_name = provider_name
        self.model_id = model_id
        self._last: Optional[Decision] = None

    # -- public surface ---------------------------------------------------

    def assure(
        self,
        contract: str,
        *,
        model_id: Optional[str] = None,
    ) -> Callable[[F], F]:
        """Decorate a function whose return value is one model answer.

        The wrapped function's FIRST positional argument is treated as the
        task input for grounding rules; pass ``""`` semantics by using
        keyword-only arguments if that does not fit.
        """
        task_contract = get_contract(contract)  # fail fast on unknown id

        def decorator(fn: F) -> F:
            @functools.wraps(fn)
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                task_input = args[0] if args and isinstance(args[0], str) else ""
                receipt_id = f"sdk-{uuid.uuid4().hex[:12]}"
                started = time.perf_counter()
                try:
                    value = fn(*args, **kwargs)
                except Exception as exc:
                    latency = (time.perf_counter() - started) * 1000.0
                    self._record_error(
                        receipt_id, task_contract, task_input, exc, latency
                    )
                    raise  # the caller's own failure, unchanged
                latency = (time.perf_counter() - started) * 1000.0

                raw_text = _to_raw_text(value)
                response = ModelResponse(
                    request_id=receipt_id,
                    provider=self.provider_name,
                    model_id=model_id or self.model_id,
                    tier="local",
                    raw_text=raw_text,
                    parsed=_parse(value),
                    latency_ms=latency,
                )
                verification = verify(response, task_contract, task_input)
                self._record(
                    response, verification, task_contract, task_input
                )
                self._last = Decision(
                    receipt_id=receipt_id,
                    contract_id=task_contract.contract_id,
                    mode=self.mode,
                    conformant=verification.passed,
                    failures=list(verification.failures),
                    checks_run=verification.checks_run,
                    latency_ms=latency,
                )
                if self.mode == "enforce" and not verification.passed:
                    raise NoSafeAnswer(
                        task_contract.contract_id,
                        verification.failures,
                        receipt_id,
                    )
                return value

            return wrapper  # type: ignore[return-value]

        return decorator

    def last_decision(self) -> Optional[Decision]:
        """The most recent Decision this instance produced, if any."""
        return self._last

    def close(self) -> None:
        if self._own_store:
            self.store.close()

    def __enter__(self) -> "Kaaval":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    # -- internals ---------------------------------------------------------

    def _record(
        self,
        response: ModelResponse,
        verification: VerificationResult,
        contract: Any,
        task_input: str,
    ) -> None:
        self.store.append(
            TrajectoryRow(
                request_id=response.request_id,
                category=contract.category,
                contract_id=contract.contract_id,
                contract_version=contract.version,
                tier="local",
                provider=response.provider,
                model_id=response.model_id,
                verifier_passed=verification.passed,
                verifier_failures=verification.failures,
                latency_ms=response.latency_ms,
                task_input=task_input,
                raw_text=response.raw_text,
            )
        )

    def _record_error(
        self,
        receipt_id: str,
        contract: Any,
        task_input: str,
        exc: Exception,
        latency_ms: float,
    ) -> None:
        self.store.append(
            TrajectoryRow(
                request_id=receipt_id,
                category=contract.category,
                contract_id=contract.contract_id,
                contract_version=contract.version,
                tier="local",
                provider=self.provider_name,
                model_id=self.model_id,
                verifier_passed=False,
                verifier_failures=[f"transport:{type(exc).__name__}"],
                latency_ms=latency_ms,
                task_input=task_input,
                raw_text="",
                attempt_status="provider_error",
                error_type=type(exc).__name__,
                error_message="wrapped function raised",
            )
        )
        self._last = Decision(
            receipt_id=receipt_id,
            contract_id=contract.contract_id,
            mode=self.mode,
            conformant=False,
            failures=[f"transport:{type(exc).__name__}"],
            latency_ms=latency_ms,
            attempt_status="provider_error",
        )
