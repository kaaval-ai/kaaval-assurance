"""Closed-loop routing policy: Layer-2 drift -> per-category thresholds.

Deterministic and transparent by design. The EWMA drift score for a category
maps to a routing posture through fixed bands:

    drift < 0.20            local-first (threshold 0.0)
    0.20 <= drift < 0.50    local-first under tightened watch (threshold = drift)
    drift >= 0.50           pre-route the category to the remote tier (1.0)

No probabilistic behavior, no model calls: the same drift input always
produces the same thresholds, so every routing change in the demo is
explainable from stored trajectory rows.
"""

from typing import Literal

from pydantic import BaseModel

from .router import Router

TIGHTEN_MIN_DRIFT = 0.20
FORCE_REMOTE_MIN_DRIFT = 0.50

PolicyAction = Literal["local_first", "tightened", "force_remote"]


class CategoryPolicy(BaseModel):
    category: str
    drift: float
    threshold: float
    action: PolicyAction
    reason: str


def policy_for_category(category: str, drift: float) -> CategoryPolicy:
    if drift >= FORCE_REMOTE_MIN_DRIFT:
        return CategoryPolicy(
            category=category,
            drift=drift,
            threshold=1.0,
            action="force_remote",
            reason=(
                f"ewma drift {drift:.2f} >= {FORCE_REMOTE_MIN_DRIFT:.2f}; "
                "pre-route to remote tier"
            ),
        )
    if drift >= TIGHTEN_MIN_DRIFT:
        return CategoryPolicy(
            category=category,
            drift=drift,
            threshold=drift,
            action="tightened",
            reason=(
                f"ewma drift {drift:.2f} in "
                f"[{TIGHTEN_MIN_DRIFT:.2f}, {FORCE_REMOTE_MIN_DRIFT:.2f}); "
                "tightened watch"
            ),
        )
    return CategoryPolicy(
        category=category,
        drift=drift,
        threshold=0.0,
        action="local_first",
        reason=f"ewma drift {drift:.2f} < {TIGHTEN_MIN_DRIFT:.2f}; local-first",
    )


def policy_from_drift(drift_by_category: dict[str, float]) -> dict[str, CategoryPolicy]:
    """Map per-category EWMA drift scores to routing policies. Pure function."""
    return {
        category: policy_for_category(category, drift)
        for category, drift in sorted(drift_by_category.items())
    }


def apply_policy(router: Router, policies: dict[str, CategoryPolicy]) -> None:
    """Install policy thresholds + human-readable notes on the router."""
    for category, policy in policies.items():
        router.category_thresholds[category] = policy.threshold
        router.category_policy_notes[category] = policy.reason
