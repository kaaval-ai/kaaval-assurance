"""Layer 2: metrics aggregation and EWMA drift tracking over trajectory rows.

Operates purely on replayable assurance telemetry (verifier outcomes, tiers,
latency, cost) — deterministic code over stored rows, no model calls and no
hidden reasoning. The EWMA drift score per category is the signal the router
consumes to tighten per-category thresholds in the closed loop.
"""

import math
from collections import Counter
from typing import Optional

from pydantic import BaseModel, Field

from .models import TrajectoryRow

DEFAULT_EWMA_ALPHA = 0.3


class EwmaTracker:
    """Exponentially weighted moving average of a failure indicator.

    update(1.0) on a failed local attempt, update(0.0) on a pass. The first
    observation seeds the average. Higher value = category drifting worse.
    """

    def __init__(self, alpha: float = DEFAULT_EWMA_ALPHA):
        if not 0.0 < alpha <= 1.0:
            raise ValueError("alpha must be in (0, 1]")
        self.alpha = alpha
        self._value: Optional[float] = None

    def update(self, observation: float) -> float:
        if self._value is None:
            self._value = observation
        else:
            self._value = self.alpha * observation + (1 - self.alpha) * self._value
        return self._value

    @property
    def value(self) -> float:
        return self._value if self._value is not None else 0.0


def percentile(values: list[float], p: float) -> float:
    """Linear-interpolation percentile, p in [0, 100]. 0.0 on empty input."""
    if not values:
        return 0.0
    s = sorted(values)
    k = (len(s) - 1) * p / 100.0
    lo = math.floor(k)
    hi = math.ceil(k)
    if lo == hi:
        return float(s[int(k)])
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


class CategoryMetrics(BaseModel):
    category: str
    requests: int
    attempts: int
    pass_rate: float  # requests whose final attempt passed Layer 1
    local_pass_rate: float  # requests resolved locally, no escalation
    escalation_rate: float
    failure_counts: dict[str, int] = Field(default_factory=dict)  # check id -> n
    latency_ms_p50: float
    latency_ms_p95: float
    total_cost_usd: float
    cost_per_verified_usd: Optional[float]  # None when nothing verified
    ewma_drift: float  # EWMA of local-attempt failure indicator


class MetricsReport(BaseModel):
    requests: int
    attempts: int
    pass_rate: float
    escalation_rate: float
    failure_counts: dict[str, int] = Field(default_factory=dict)
    latency_ms_p50: float
    latency_ms_p95: float
    total_cost_usd: float
    cost_per_verified_usd: Optional[float]
    ewma_alpha: float
    by_category: dict[str, CategoryMetrics] = Field(default_factory=dict)


def _group_by_request(rows: list[TrajectoryRow]) -> dict[str, list[TrajectoryRow]]:
    """Group attempt rows per request, preserving row order within and across."""
    grouped: dict[str, list[TrajectoryRow]] = {}
    for row in rows:
        grouped.setdefault(row.request_id, []).append(row)
    return grouped


def _summarize(
    rows: list[TrajectoryRow], alpha: float
) -> tuple[dict, dict[str, int], float]:
    """Shared per-slice computation. Returns (fields, failure_counts, drift)."""
    grouped = _group_by_request(rows)
    n_requests = len(grouped)

    final_passed = 0
    escalated = 0
    request_latencies: list[float] = []
    for attempts in grouped.values():
        if attempts[-1].verifier_passed:
            final_passed += 1
        if any(a.escalated for a in attempts):
            escalated += 1
        request_latencies.append(sum(a.latency_ms for a in attempts))

    failure_counts: Counter = Counter()
    for row in rows:
        failure_counts.update(row.verifier_failures)

    ewma = EwmaTracker(alpha)
    for row in rows:  # chronological: rows arrive id-ordered
        if row.tier == "local":
            ewma.update(0.0 if row.verifier_passed else 1.0)

    total_cost = sum(r.cost_usd for r in rows)
    fields = {
        "requests": n_requests,
        "attempts": len(rows),
        "pass_rate": final_passed / n_requests if n_requests else 0.0,
        "escalation_rate": escalated / n_requests if n_requests else 0.0,
        "latency_ms_p50": percentile(request_latencies, 50),
        "latency_ms_p95": percentile(request_latencies, 95),
        "total_cost_usd": total_cost,
        "cost_per_verified_usd": total_cost / final_passed if final_passed else None,
    }
    return fields, dict(failure_counts), ewma.value


def aggregate(
    rows: list[TrajectoryRow], alpha: float = DEFAULT_EWMA_ALPHA
) -> MetricsReport:
    """Aggregate Layer-2 metrics over trajectory rows (id/chronological order)."""
    overall, overall_failures, _ = _summarize(rows, alpha)

    by_category: dict[str, CategoryMetrics] = {}
    categories = sorted({r.category for r in rows})
    for category in categories:
        cat_rows = [r for r in rows if r.category == category]
        fields, failures, drift = _summarize(cat_rows, alpha)
        grouped = _group_by_request(cat_rows)
        local_pass = sum(
            1 for attempts in grouped.values() if not any(a.escalated for a in attempts)
            and attempts[-1].verifier_passed
        )
        by_category[category] = CategoryMetrics(
            category=category,
            failure_counts=failures,
            local_pass_rate=local_pass / len(grouped) if grouped else 0.0,
            ewma_drift=drift,
            **fields,
        )

    return MetricsReport(
        failure_counts=overall_failures,
        ewma_alpha=alpha,
        by_category=by_category,
        **{k: v for k, v in overall.items()},
    )
