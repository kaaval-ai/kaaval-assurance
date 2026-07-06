"""Core data models shared across the assurance plane."""

from datetime import datetime, timezone
from typing import Literal, Optional

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ModelResponse(BaseModel):
    """A single model generation, from any provider tier."""

    request_id: str
    provider: str  # "mock" | "vllm-gemma" | "fireworks" (later)
    model_id: str
    tier: Literal["local", "remote"]
    raw_text: str
    parsed: Optional[dict] = None  # JSON parse attempt; None if unparseable
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: float = 0.0
    cost_usd: float = 0.0
    # White-box seam: per-token logprobs from vLLM when serving open weights
    # on AMD infrastructure. Always None for mock and closed-API tiers.
    logprobs: Optional[list[float]] = None
    created_at: datetime = Field(default_factory=_utcnow)


class VerificationResult(BaseModel):
    """Layer 1 outcome: deterministic contract checks over one response."""

    passed: bool
    checks_run: int
    failures: list[str] = Field(default_factory=list)  # failed check IDs


class RoutingDecision(BaseModel):
    """Router output. `reason` feeds the routing-reason feed in the demo."""

    tier: Literal["local", "remote"]
    reason: str


class TrajectoryRow(BaseModel):
    """One replayable row per model attempt.

    audit_* fields are reserved for Layer 3 (sampled adversarial audit) and
    stay NULL until that lands; the schema exists now so trajectory data
    collected from day one remains forward-compatible.
    """

    request_id: str
    ts: datetime = Field(default_factory=_utcnow)
    category: str
    contract_id: str
    contract_version: str
    tier: Literal["local", "remote"]
    provider: str
    model_id: str
    verifier_passed: bool
    verifier_failures: list[str] = Field(default_factory=list)
    escalated: bool = False
    latency_ms: float = 0.0
    cost_usd: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    # Replayability: full input and raw output are stored verbatim.
    task_input: str = ""
    raw_text: str = ""
    # Layer 3 seams (populated from Jul 7 onward).
    audit_sampled: bool = False
    audit_result: Optional[str] = None  # "pass" | "fail" | None
    audit_violations: Optional[list[dict]] = None


class PipelineResult(BaseModel):
    """What one end-to-end request produced."""

    request_id: str
    response: ModelResponse
    verification: VerificationResult
    routing: RoutingDecision
    escalated: bool
    attempts: int
