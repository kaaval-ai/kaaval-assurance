"""Layer 3 audit data models.

Detection is model-generated: a challenger model inspects an accepted answer
and reports structured violations. Aggregation and thresholding over that
structured output are deterministic code. Never describe the detection step
itself as deterministic.
"""

from typing import Literal, Optional

from pydantic import BaseModel, Field

Severity = Literal["minor", "major", "critical"]
AuditVerdict = Literal["pass", "fail", "error"]
CalibrationStatus = Literal["passed", "failed", "skipped"]


class AuditViolation(BaseModel):
    check_id: str
    severity: Severity
    field: Optional[str] = None
    description: str
    evidence: str
    # Phrased as guidance to verify ("Verify X specifically"), never as an
    # asserted failure. Feeds escalation repair hints later.
    repair_hint: Optional[str] = None


class ChallengerOutput(BaseModel):
    """The strict JSON shape the challenger must return."""

    result: Literal["pass", "fail"]
    violations: list[AuditViolation] = Field(default_factory=list)


def aggregate_verdict(output: ChallengerOutput) -> Literal["pass", "fail"]:
    """Deterministic aggregation over model-generated detection output:
    fail iff the challenger verdict is fail or any violation is major/critical.
    """
    if output.result == "fail":
        return "fail"
    if any(v.severity in ("major", "critical") for v in output.violations):
        return "fail"
    return "pass"


class AuditResult(BaseModel):
    """One completed audit of one accepted answer."""

    request_id: str
    category: str
    contract_id: str
    audit_provider: str
    audit_model_id: str
    result: AuditVerdict  # "error" = challenger output failed schema validation
    violations: list[AuditViolation] = Field(default_factory=list)
    parse_ok: bool = True
    latency_ms: float = 0.0
    cost_usd: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cached_tokens: Optional[int] = None  # provider-reported prompt-cache hits
    # Optional model-output confidence telemetry derived from logprobs when
    # the provider returns them. None when unavailable — never fabricated.
    confidence_proxy: Optional[float] = None


class AuditCalibrationReport(BaseModel):
    """Challenger false-positive calibration against known-good gold answers.

    A false positive is a fail verdict against a gold answer (the deterministic
    aggregation already folds major/critical violations into fail). This is a
    hard gate: if status is not "passed", audit results may be shown but must
    not be presented as trusted evidence. Audit is display-only in this build.
    """

    total_gold: int
    false_positives: int
    false_positive_rate: float
    threshold: float
    status: CalibrationStatus
    parse_errors: int = 0
    flagged_case_ids: list[str] = Field(default_factory=list)


class AuditRunSummary(BaseModel):
    """Sampled offline audit summary for one eval run. Reporting only —
    audit signals do not enter Layer-2 EWMA in this build.
    """

    audit_provider: str
    audit_model_id: str
    trusted: bool  # calibration passed; all results remain display-only
    calibration: AuditCalibrationReport
    sample_rate: float
    seed: int
    accepted_answers: int  # Layer-1-passing answers eligible for sampling
    sampled: int
    passed: int
    failed: int
    errors: int  # challenger outputs that failed schema validation
    violations_by_severity: dict[str, int] = Field(default_factory=dict)
    total_cost_usd: float = 0.0
    cost_per_sampled_usd: Optional[float] = None
    cost_per_verified_accepted_usd: Optional[float] = None
    audit_tokens: int = 0  # remote challenger tokens spent on audit
    # Sum of provider-reported cached prompt tokens across audit calls;
    # None when the provider reported none. Telemetry only, never estimated.
    cached_tokens_total: Optional[int] = None
