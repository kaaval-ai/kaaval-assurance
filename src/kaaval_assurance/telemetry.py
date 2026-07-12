"""Telemetry Truth Layer: every judge-facing claim maps to a stored field.

build_telemetry_summary is deterministic code over trajectory rows, eval
metrics, the audit summary, and the configured runtime profile. Each claim
carries a source tag:

    measured        derived from stored rows / run results
    configured      from RuntimeProfile / env config, recorded not measured
    not_available   the provider or run did not produce this value
    planned         intended deployment state not yet executed

Runtime metrics are never fabricated: without an AMD Developer Cloud run the
runtime block reports configured/planned, and cost savings appear only when
an always-remote baseline run exists.
"""

from collections import Counter
from typing import Literal, Optional

from pydantic import BaseModel, Field

from .audit.models import AuditRunSummary
from .eval.runner import EvalRunReport
from .models import RuntimeProfile, TrajectoryRow
from .routing_policy import FORCE_REMOTE_MIN_DRIFT, TIGHTEN_MIN_DRIFT

SourceKind = Literal["measured", "configured", "not_available", "planned"]


class ProviderMix(BaseModel):
    attempts_by_provider: dict[str, int] = Field(default_factory=dict)
    requests_by_first_tier: dict[str, int] = Field(default_factory=dict)
    local_attempts: int = 0
    remote_attempts: int = 0
    audit_calls: int = 0


class RuntimeTelemetry(BaseModel):
    status: Literal["configured", "planned"]  # "measured" arrives only with a
    # real deployment run; nothing in mock mode may claim it
    profile: Optional[RuntimeProfile] = None
    cached_tokens_total: Optional[int] = None  # None = provider did not report
    note: str = ""


class VerificationTelemetry(BaseModel):
    local_verified_rate: float
    final_verified_rate: float
    failures_by_check: dict[str, int] = Field(default_factory=dict)


class GoldEvaluationTelemetry(BaseModel):
    """Deterministic correctness evidence over scorable reference fields."""

    scored_cases: int = 0
    correct_cases: int = 0
    accuracy: Optional[float] = None
    false_accept_count: int = 0
    false_accept_rate: Optional[float] = None
    false_reject_count: int = 0
    false_reject_rate: Optional[float] = None
    scope: str = (
        "enum, numeric, boolean, and scalar-array fields only; free text unscored"
    )


class RoutingTelemetry(BaseModel):
    escalation_rate: float
    preroute_remote_rate: float
    ewma_drift_by_category: dict[str, float] = Field(default_factory=dict)
    high_drift_categories: list[str] = Field(default_factory=list)  # >= 0.50
    watch_categories: list[str] = Field(default_factory=list)  # 0.20 - 0.50


class AuditTelemetry(BaseModel):
    enabled: bool
    sampled: int = 0
    accepted_answers: int = 0
    trusted: Optional[bool] = None
    calibration_status: Optional[str] = None
    calibration_fp_rate: Optional[float] = None
    calibration_threshold: Optional[float] = None
    passed: int = 0
    failed: int = 0
    errors: int = 0
    violations_by_severity: dict[str, int] = Field(default_factory=dict)
    audit_tokens: int = 0
    calibration_scope: str = "false_positive_only"
    routing_integration: str = "display_only"


class CostTelemetry(BaseModel):
    total_cost_usd: float
    local_cost_usd: float
    remote_cost_usd: float
    audit_cost_usd: float
    cost_per_verified_answer_usd: Optional[float]
    audit_cost_per_verified_accepted_usd: Optional[float]
    # All savings fields stay None unless an always-remote baseline exists.
    remote_calls_avoided: Optional[int] = None
    remote_calls_avoided_rate: Optional[float] = None
    remote_tokens_avoided: Optional[int] = None
    estimated_cost_saved_vs_always_remote_usd: Optional[float] = None


class AttemptTelemetry(BaseModel):
    """Per-attempt proof record derived from a trajectory row (measured)."""

    request_id: str
    contract_id: str
    category: str
    provider: str
    model_id: str
    tier: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cached_tokens: Optional[int] = None  # not persisted per-row; None = not reported
    latency_ms: float
    cost_usd: float
    verifier_passed: bool
    verifier_failure_count: int
    verifier_failure_types: list[str] = Field(default_factory=list)  # check prefixes
    verifier_failures: list[str] = Field(default_factory=list)  # full check ids
    escalated: bool = False
    escalation_reason: Optional[str] = None
    attempt_status: Literal["completed", "provider_error"] = "completed"
    error_type: Optional[str] = None
    error_message: Optional[str] = None


class ClaimSupport(BaseModel):
    claim: str
    value: str
    source: SourceKind
    field: str  # telemetry field path backing the claim


class TelemetrySummary(BaseModel):
    run_id: str
    requests: int
    attempts: int
    latency_ms_p50: float
    latency_ms_p95: float
    provider_mix: ProviderMix
    runtime: RuntimeTelemetry
    verification: VerificationTelemetry
    evaluation: GoldEvaluationTelemetry = Field(
        default_factory=GoldEvaluationTelemetry
    )
    routing: RoutingTelemetry
    audit: AuditTelemetry
    cost: CostTelemetry
    attempts_detail: list[AttemptTelemetry] = Field(default_factory=list)
    claims: list[ClaimSupport] = Field(default_factory=list)


class AlwaysRemoteBaseline(BaseModel):
    """Aggregates from a cached always-remote run (run once, reuse)."""

    requests: int
    remote_calls: int
    remote_tokens: int
    total_cost_usd: float


def baseline_from_rows(rows: list[TrajectoryRow]) -> AlwaysRemoteBaseline:
    remote = [r for r in rows if r.tier == "remote"]
    return AlwaysRemoteBaseline(
        requests=len({r.request_id for r in rows}),
        remote_calls=len(remote),
        remote_tokens=sum(r.prompt_tokens + r.completion_tokens for r in remote),
        total_cost_usd=sum(r.cost_usd for r in rows),
    )


def _fmt_cost(value: Optional[float]) -> str:
    return "n/a" if value is None else f"${value:.4f}"


def _group(rows: list[TrajectoryRow]) -> dict[str, list[TrajectoryRow]]:
    grouped: dict[str, list[TrajectoryRow]] = {}
    for row in rows:
        grouped.setdefault(row.request_id, []).append(row)
    return grouped


def build_telemetry_summary(
    report: EvalRunReport,
    rows: list[TrajectoryRow],
    runtime_profile: Optional[RuntimeProfile] = None,
    always_remote_baseline: Optional[AlwaysRemoteBaseline] = None,
) -> TelemetrySummary:
    m = report.metrics
    audit: Optional[AuditRunSummary] = report.audit
    grouped = _group(rows)
    n_requests = len(grouped)

    local_rows = [r for r in rows if r.tier == "local"]
    remote_rows = [r for r in rows if r.tier == "remote"]
    local_verified = sum(
        1
        for attempts in grouped.values()
        if attempts[0].tier == "local"
        and not any(a.escalated for a in attempts)
        and attempts[-1].verifier_passed
    )
    final_verified = sum(
        1 for attempts in grouped.values() if attempts[-1].verifier_passed
    )

    provider_mix = ProviderMix(
        attempts_by_provider=dict(Counter(r.provider for r in rows)),
        requests_by_first_tier=dict(
            Counter(attempts[0].tier for attempts in grouped.values())
        ),
        local_attempts=len(local_rows),
        remote_attempts=len(remote_rows),
        audit_calls=audit.sampled if audit else 0,
    )

    drift = {c: cat.ewma_drift for c, cat in m.by_category.items()}
    routing = RoutingTelemetry(
        escalation_rate=m.escalation_rate,
        preroute_remote_rate=m.preroute_remote_rate,
        ewma_drift_by_category=drift,
        high_drift_categories=sorted(
            c for c, d in drift.items() if d >= FORCE_REMOTE_MIN_DRIFT
        ),
        watch_categories=sorted(
            c
            for c, d in drift.items()
            if TIGHTEN_MIN_DRIFT <= d < FORCE_REMOTE_MIN_DRIFT
        ),
    )

    verification = VerificationTelemetry(
        local_verified_rate=local_verified / n_requests if n_requests else 0.0,
        final_verified_rate=final_verified / n_requests if n_requests else 0.0,
        failures_by_check=dict(m.failure_counts),
    )
    evaluation = GoldEvaluationTelemetry(
        scored_cases=report.gold_scored_cases,
        correct_cases=report.gold_correct_cases,
        accuracy=report.gold_accuracy,
        false_accept_count=report.false_accept_count,
        false_accept_rate=report.false_accept_rate,
        false_reject_count=report.false_reject_count,
        false_reject_rate=report.false_reject_rate,
    )

    audit_telemetry = AuditTelemetry(enabled=audit is not None)
    if audit is not None:
        audit_telemetry = AuditTelemetry(
            enabled=True,
            sampled=audit.sampled,
            accepted_answers=audit.accepted_answers,
            trusted=audit.trusted,
            calibration_status=audit.calibration.status,
            calibration_fp_rate=audit.calibration.false_positive_rate,
            calibration_threshold=audit.calibration.threshold,
            passed=audit.passed,
            failed=audit.failed,
            errors=audit.errors,
            violations_by_severity=dict(audit.violations_by_severity),
            audit_tokens=audit.audit_tokens,
        )

    local_cost = sum(r.cost_usd for r in local_rows)
    remote_cost = sum(r.cost_usd for r in remote_rows)
    audit_cost = audit.total_cost_usd if audit else 0.0
    total_cost = local_cost + remote_cost + audit_cost

    cost = CostTelemetry(
        total_cost_usd=total_cost,
        local_cost_usd=local_cost,
        remote_cost_usd=remote_cost,
        audit_cost_usd=audit_cost,
        cost_per_verified_answer_usd=m.cost_per_verified_usd,
        audit_cost_per_verified_accepted_usd=(
            audit.cost_per_verified_accepted_usd if audit else None
        ),
    )
    if always_remote_baseline is not None and always_remote_baseline.remote_calls:
        current_remote_tokens = sum(
            r.prompt_tokens + r.completion_tokens for r in remote_rows
        )
        cost.remote_calls_avoided = (
            always_remote_baseline.remote_calls - len(remote_rows)
        )
        cost.remote_calls_avoided_rate = (
            cost.remote_calls_avoided / always_remote_baseline.remote_calls
        )
        cost.remote_tokens_avoided = (
            always_remote_baseline.remote_tokens - current_remote_tokens
        )
        cost.estimated_cost_saved_vs_always_remote_usd = (
            always_remote_baseline.total_cost_usd - total_cost
        )

    if runtime_profile is not None:
        runtime = RuntimeTelemetry(
            status="configured",
            profile=runtime_profile,
            cached_tokens_total=audit.cached_tokens_total if audit else None,
            note=(
                "serving settings recorded from configuration; ROCm/vLLM "
                "versions recorded when deployed"
            ),
        )
    else:
        runtime = RuntimeTelemetry(
            status="planned",
            cached_tokens_total=audit.cached_tokens_total if audit else None,
            note=(
                "mock local tier in this run; Gemma via vLLM on AMD Developer "
                "Cloud is the planned deployment"
            ),
        )

    reason_by_request = {r.request_id: r.routing_reason for r in report.results}
    attempts_detail = []
    for row in rows:
        failure_types = sorted({f.split(":", 1)[0] for f in row.verifier_failures})
        attempts_detail.append(
            AttemptTelemetry(
                request_id=row.request_id,
                contract_id=row.contract_id,
                category=row.category,
                provider=row.provider,
                model_id=row.model_id,
                tier=row.tier,
                prompt_tokens=row.prompt_tokens,
                completion_tokens=row.completion_tokens,
                total_tokens=row.prompt_tokens + row.completion_tokens,
                latency_ms=row.latency_ms,
                cost_usd=row.cost_usd,
                verifier_passed=row.verifier_passed,
                verifier_failure_count=len(row.verifier_failures),
                verifier_failure_types=failure_types,
                verifier_failures=row.verifier_failures,
                escalated=row.escalated,
                escalation_reason=(
                    reason_by_request.get(row.request_id) if row.escalated else None
                ),
                attempt_status=row.attempt_status,
                error_type=row.error_type,
                error_message=row.error_message,
            )
        )

    claims = _build_claims(
        verification, evaluation, routing, audit_telemetry, cost, runtime
    )

    return TelemetrySummary(
        run_id=report.run_id,
        requests=n_requests,
        attempts=len(rows),
        latency_ms_p50=m.latency_ms_p50,
        latency_ms_p95=m.latency_ms_p95,
        provider_mix=provider_mix,
        runtime=runtime,
        verification=verification,
        evaluation=evaluation,
        routing=routing,
        audit=audit_telemetry,
        cost=cost,
        attempts_detail=attempts_detail,
        claims=claims,
    )


def _build_claims(
    verification: VerificationTelemetry,
    evaluation: GoldEvaluationTelemetry,
    routing: RoutingTelemetry,
    audit: AuditTelemetry,
    cost: CostTelemetry,
    runtime: RuntimeTelemetry,
) -> list[ClaimSupport]:
    claims = [
        ClaimSupport(
            claim="Local Layer-1 contract-conformance rate",
            value=f"{verification.local_verified_rate:.1%}",
            source="measured",
            field="verification.local_verified_rate",
        ),
        ClaimSupport(
            claim="Final Layer-1 contract-conformance rate",
            value=f"{verification.final_verified_rate:.1%}",
            source="measured",
            field="verification.final_verified_rate",
        ),
        ClaimSupport(
            claim="Escalation rate",
            value=f"{routing.escalation_rate:.1%}",
            source="measured",
            field="routing.escalation_rate",
        ),
        ClaimSupport(
            claim="Preroute remote rate",
            value=f"{routing.preroute_remote_rate:.1%}",
            source="measured",
            field="routing.preroute_remote_rate",
        ),
        ClaimSupport(
            claim="High-drift categories",
            value=", ".join(routing.high_drift_categories) or "none",
            source="measured",
            field="routing.high_drift_categories",
        ),
    ]
    if evaluation.accuracy is not None:
        claims.extend(
            [
                ClaimSupport(
                    claim="Gold critical-field accuracy",
                    value=(
                        f"{evaluation.accuracy:.1%} "
                        f"({evaluation.correct_cases}/{evaluation.scored_cases})"
                    ),
                    source="measured",
                    field="evaluation.accuracy",
                ),
                ClaimSupport(
                    claim="Gold false-accept rate",
                    value=f"{evaluation.false_accept_rate:.1%}",
                    source="measured",
                    field="evaluation.false_accept_rate",
                ),
            ]
        )
    else:
        claims.append(
            ClaimSupport(
                claim="Gold critical-field accuracy",
                value="n/a (no reference-answer fields scored in this run)",
                source="not_available",
                field="evaluation.accuracy",
            )
        )
    if audit.enabled:
        claims.append(
            ClaimSupport(
                claim="Layer 3 FP calibration passed",
                value=(
                    "yes; display-only, not a routing input"
                    if audit.trusted
                    else "no; display-only"
                ),
                source="measured",
                field="audit.trusted",
            )
        )
        if audit.calibration_status == "skipped":
            claims.append(
                ClaimSupport(
                    claim="Calibration FP rate",
                    value="skipped (results untrusted)",
                    source="not_available",
                    field="audit.calibration_status",
                )
            )
        else:
            claims.append(
                ClaimSupport(
                    claim="Calibration FP rate",
                    value=(
                        f"{audit.calibration_fp_rate:.1%} / threshold "
                        f"{audit.calibration_threshold:.1%}"
                    ),
                    source="measured",
                    field="audit.calibration_fp_rate",
                )
            )
    else:
        claims.append(
            ClaimSupport(
                claim="Layer 3 FP calibration passed",
                value="no audit in this run",
                source="not_available",
                field="audit.enabled",
            )
        )
    claims.append(
        ClaimSupport(
            claim="Cost per contract-conformant answer",
            value=_fmt_cost(cost.cost_per_verified_answer_usd),
            source="configured",
            field="cost.cost_per_verified_answer_usd",
        )
    )
    if audit.enabled:
        claims.append(
            ClaimSupport(
                claim="Audit cost per Layer-1-accepted answer",
                value=_fmt_cost(cost.audit_cost_per_verified_accepted_usd),
                source="measured",
                field="cost.audit_cost_per_verified_accepted_usd",
            )
        )
    if cost.remote_calls_avoided_rate is not None:
        claims.append(
            ClaimSupport(
                claim="Remote calls avoided vs always-remote",
                value=f"{cost.remote_calls_avoided_rate:.1%} "
                f"(cost saved {_fmt_cost(cost.estimated_cost_saved_vs_always_remote_usd)})",
                source="measured",
                field="cost.remote_calls_avoided_rate",
            )
        )
    else:
        claims.append(
            ClaimSupport(
                claim="Remote calls avoided vs always-remote",
                value="n/a (no always-remote baseline)",
                source="not_available",
                field="cost.remote_calls_avoided_rate",
            )
        )
    if runtime.profile is not None:
        p = runtime.profile
        rocm = p.rocm_version or "recorded at deployment"
        vllm = p.vllm_version or "recorded at deployment"
        runtime_label = (
            "Ollama"
            if p.provider == "ollama"
            else "vLLM"
            if p.provider == "vllm-gemma"
            else p.provider
        )
        claims.append(
            ClaimSupport(
                claim="Runtime",
                value=(
                    f"{p.model_family or 'model'} '{p.model_id}' via {runtime_label}, "
                    f"target {p.hardware_target}; dtype {p.dtype}, "
                    f"kv-cache {p.kv_cache_dtype}, tp {p.tensor_parallel_size}; "
                    f"ROCm {rocm}, vLLM {vllm}"
                ),
                source="configured",
                field="runtime.profile",
            )
        )
    else:
        claims.append(
            ClaimSupport(
                claim="Runtime",
                value=(
                    "Gemma via vLLM planned for AMD Developer Cloud; mock local "
                    "tier in this run"
                ),
                source="planned",
                field="runtime.status",
            )
        )
    return claims


def render_summary_text(summary: TelemetrySummary) -> str:
    lines = ["=== telemetry truth summary ==="]
    lines.extend(
        f"{c.claim}: {c.value} [{c.source}]" for c in summary.claims
    )
    return "\n".join(lines)


def render_summary_markdown(summary: TelemetrySummary) -> str:
    lines = [
        "# Telemetry truth summary",
        "",
        f"Run `{summary.run_id}` — {summary.requests} requests, "
        f"{summary.attempts} attempts, latency p50 "
        f"{summary.latency_ms_p50:.1f}ms / p95 {summary.latency_ms_p95:.1f}ms.",
        "",
        "| Claim | Value | Source |",
        "|---|---|---|",
    ]
    lines.extend(
        f"| {c.claim} | {c.value} | {c.source} |" for c in summary.claims
    )
    lines.append("")
    lines.append(
        "Sources: measured = derived from stored trajectory rows; configured = "
        "recorded runtime settings, not measurements; not_available = the "
        "provider or run did not produce this value; planned = intended "
        "deployment not yet executed."
    )
    return "\n".join(lines)
