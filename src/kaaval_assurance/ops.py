"""Public, content-free operations records for Kaaval operator surfaces.

The web console and ``kaaval top`` should consume these records instead of
re-running verification or reading the private trajectory database schema.
The first adapter is intentionally a bounded process-local snapshot; a durable
history API and SSE stream are the next protocol step documented in
``docs/k-top-requirements.md``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import PurePosixPath, PureWindowsPath
from typing import Literal, Sequence
from urllib.parse import urlsplit

from pydantic import BaseModel, Field

from .metrics import percentile
from .models import TrajectoryRow

OpsOutcome = Literal[
    "conformant",
    "recovered",
    "no_safe_answer",
    "provider_error",
    "unknown",
]


class OpsAttempt(BaseModel):
    """One redacted model attempt safe for an operator summary feed."""

    ordinal: int
    timestamp: datetime
    provider: str
    model_id: str
    tier: Literal["local", "remote"]
    attempt_status: Literal["completed", "provider_error"]
    contract_conformant: bool
    failed_check_ids: list[str] = Field(default_factory=list)
    escalated: bool = False
    latency_ms: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    recorded_cost_usd: float = 0.0
    error_type: str | None = None
    audit_sampled: bool = False
    audit_result: str | None = None


class OpsDecision(BaseModel):
    """One assured decision, potentially containing multiple attempts."""

    decision_id: str
    session_id: str
    timestamp: datetime
    category: str
    contract_id: str
    contract_version: str
    contract_hash: str | None = None
    final_outcome: OpsOutcome
    provenance: Literal["live", "sample"]
    authority: Literal["enforced", "display_only"] = "enforced"
    attempts: list[OpsAttempt]
    recorded_model_call_latency_sum_ms: float
    recorded_cost_usd: float
    content_redaction: Literal["withheld"] = "withheld"


class OpsRoutingState(BaseModel):
    """Current Layer-2 state; EWMA is verifier-failure trend, not accuracy."""

    session_id: str
    category: str
    verifier_failure_ewma: float
    action: Literal["local_first", "tightened", "force_remote"]
    reason: str


class OpsTotals(BaseModel):
    sessions: int = 0
    decisions: int = 0
    attempts: int = 0
    calls_last_minute: int | None = 0
    final_contract_conformance_rate: float | None = None
    recovered: int = 0
    no_safe_answer: int = 0
    provider_errors: int = 0
    escalations: int = 0
    p95_recorded_model_call_latency_sum_ms: float | None = None
    recorded_cost_usd: float = 0.0
    decision_window_truncated: bool = False


class OpsService(BaseModel):
    service: str = "kaaval-assurance"
    runtime_version: str
    deployment_mode: str
    live_runs_enabled: bool
    execution_mode: Literal["enforce", "unavailable"] = "enforce"
    redaction: Literal["content_withheld"] = "content_withheld"


class OpsSnapshot(BaseModel):
    """Experimental v0.1 snapshot consumed by K Top's quick MVP."""

    schema_version: Literal["0.1"] = "0.1"
    generated_at: datetime
    provenance: Literal["live", "sample"]
    authority: Literal["enforced", "display_only", "unavailable"]
    service: OpsService
    totals: OpsTotals
    routing: list[OpsRoutingState] = Field(default_factory=list)
    decisions: list[OpsDecision] = Field(default_factory=list)


@dataclass(frozen=True)
class OpsSessionInput:
    """Server-only bridge from a live session into the public schema."""

    session_id: str
    rows: Sequence[TrajectoryRow]
    routing: Sequence[OpsRoutingState] = field(default_factory=tuple)
    window_truncated: bool = False


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _public_model_id(value: str) -> str:
    """Preserve normal model IDs while withholding path/URL-shaped values."""

    model_id = value.strip()
    windows_absolute = (
        len(model_id) >= 3
        and model_id[1] == ":"
        and model_id[2] in {"/", "\\"}
    ) or model_id.startswith("\\\\")
    relative_path = model_id.startswith(("./", "../", ".\\", "..\\"))
    if model_id.startswith(("/", "~/")) or windows_absolute or relative_path:
        path = (
            PureWindowsPath(model_id)
            if windows_absolute or "\\" in model_id
            else PurePosixPath(model_id)
        )
        return f"local-model:{path.name or 'redacted'}"
    try:
        parsed = urlsplit(model_id)
    except ValueError:
        return "redacted-model-id"
    if parsed.scheme == "file":
        file_path = parsed.path
        path = (
            PureWindowsPath(file_path)
            if "\\" in file_path
            or (len(file_path) >= 2 and file_path[1] == ":")
            else PurePosixPath(file_path)
        )
        return f"local-model:{path.name or 'redacted'}"
    if parsed.scheme and parsed.netloc:
        return f"remote-model:{parsed.hostname or 'redacted'}"
    return model_id


def _outcome(rows: Sequence[TrajectoryRow]) -> OpsOutcome:
    if not rows:
        return "unknown"
    final = rows[-1]
    if final.verifier_passed:
        if len(rows) > 1 and any(not row.verifier_passed for row in rows[:-1]):
            return "recovered"
        return "conformant"
    if final.attempt_status == "provider_error":
        return "provider_error"
    return "no_safe_answer"


def _decision(
    session_id: str,
    rows: Sequence[TrajectoryRow],
    provenance: Literal["live", "sample"],
) -> OpsDecision:
    first = rows[0]
    attempts = [
        OpsAttempt(
            ordinal=index,
            timestamp=_as_utc(row.ts),
            provider=row.provider,
            model_id=_public_model_id(row.model_id),
            tier=row.tier,
            attempt_status=row.attempt_status,
            contract_conformant=row.verifier_passed,
            failed_check_ids=list(row.verifier_failures),
            escalated=row.escalated,
            latency_ms=row.latency_ms,
            prompt_tokens=row.prompt_tokens,
            completion_tokens=row.completion_tokens,
            recorded_cost_usd=row.cost_usd,
            error_type=row.error_type,
            audit_sampled=row.audit_sampled,
            audit_result=row.audit_result,
        )
        for index, row in enumerate(rows, start=1)
    ]
    return OpsDecision(
        decision_id=first.request_id,
        session_id=session_id,
        timestamp=max(_as_utc(row.ts) for row in rows),
        category=first.category,
        contract_id=first.contract_id,
        contract_version=first.contract_version,
        final_outcome=_outcome(rows),
        provenance=provenance,
        authority="enforced" if provenance == "live" else "display_only",
        attempts=attempts,
        recorded_model_call_latency_sum_ms=sum(row.latency_ms for row in rows),
        recorded_cost_usd=sum(row.cost_usd for row in rows),
    )


def build_ops_snapshot(
    sessions: Sequence[OpsSessionInput],
    *,
    runtime_version: str,
    deployment_mode: str,
    live_runs_enabled: bool,
    provenance: Literal["live", "sample"] = "live",
    generated_at: datetime | None = None,
    decision_limit: int = 500,
) -> OpsSnapshot:
    """Build one bounded snapshot without prompt or response content."""

    now = _as_utc(generated_at or datetime.now(timezone.utc))
    decisions: list[OpsDecision] = []
    routing: list[OpsRoutingState] = []
    for session in sessions:
        grouped: dict[str, list[TrajectoryRow]] = {}
        for row in session.rows:
            grouped.setdefault(row.request_id, []).append(row)
        decisions.extend(
            _decision(session.session_id, rows, provenance)
            for rows in grouped.values()
            if rows
        )
        routing.extend(session.routing)

    decisions.sort(key=lambda item: item.timestamp, reverse=True)
    all_decisions = decisions
    conformant = sum(
        decision.final_outcome in {"conformant", "recovered"}
        for decision in all_decisions
    )
    model_call_latency_sums = [
        decision.recorded_model_call_latency_sum_ms for decision in all_decisions
    ]
    one_minute_ago = now - timedelta(minutes=1)
    per_session_truncated = any(session.window_truncated for session in sessions)
    window_truncated = per_session_truncated or len(all_decisions) > decision_limit
    totals = OpsTotals(
        sessions=len(sessions),
        decisions=len(all_decisions),
        attempts=sum(len(decision.attempts) for decision in all_decisions),
        calls_last_minute=(
            None
            if window_truncated
            else sum(
                decision.timestamp >= one_minute_ago for decision in all_decisions
            )
        ),
        final_contract_conformance_rate=(
            conformant / len(all_decisions) if all_decisions else None
        ),
        recovered=sum(
            decision.final_outcome == "recovered" for decision in all_decisions
        ),
        no_safe_answer=sum(
            decision.final_outcome == "no_safe_answer"
            for decision in all_decisions
        ),
        provider_errors=sum(
            decision.final_outcome == "provider_error"
            for decision in all_decisions
        ),
        escalations=sum(
            any(attempt.escalated for attempt in decision.attempts)
            for decision in all_decisions
        ),
        p95_recorded_model_call_latency_sum_ms=(
            percentile(model_call_latency_sums, 95)
            if model_call_latency_sums
            else None
        ),
        recorded_cost_usd=sum(
            decision.recorded_cost_usd for decision in all_decisions
        ),
        decision_window_truncated=window_truncated,
    )
    return OpsSnapshot(
        generated_at=now,
        provenance=provenance,
        authority=(
            "display_only"
            if provenance == "sample"
            else "enforced"
            if all_decisions
            else "unavailable"
        ),
        service=OpsService(
            runtime_version=runtime_version,
            deployment_mode=deployment_mode,
            live_runs_enabled=live_runs_enabled,
            execution_mode="enforce" if live_runs_enabled else "unavailable",
        ),
        totals=totals,
        routing=sorted(
            routing, key=lambda item: (item.category, item.session_id)
        ),
        decisions=all_decisions[: max(0, decision_limit)],
    )
