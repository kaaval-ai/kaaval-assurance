"""Router: chooses the model tier per request category.

Default policy: local first for every category, escalate to remote when
Layer 1 rejects the local response. The closed loop tightens this per
category: routing_policy maps Layer-2 EWMA drift onto category_thresholds
(escalation pressure in [0, 1]; >= 1.0 pre-routes the category to the remote
tier) plus a human-readable policy note that surfaces in every routing
reason. With no policy applied, behavior is identical to the static default.
"""

from .models import RoutingDecision, VerificationResult


class Router:
    def __init__(self) -> None:
        # Per-category escalation pressure in [0, 1].
        # 0.0 = always try local first; >= 1.0 = route straight to remote.
        # Populated by routing_policy.apply_policy from Layer-2 drift scores.
        self.category_thresholds: dict[str, float] = {}
        # Human-readable policy context per category (drift band + action),
        # embedded in routing reasons so trajectory evidence is self-explaining.
        self.category_policy_notes: dict[str, str] = {}

    def choose_tier(self, category: str) -> RoutingDecision:
        threshold = self.category_thresholds.get(category, 0.0)
        note = self.category_policy_notes.get(category)
        suffix = f" [{note}]" if note else ""

        if threshold >= 1.0:
            return RoutingDecision(
                tier="remote",
                reason=(
                    f"category '{category}' routing threshold {threshold:.2f} "
                    f"forces remote tier{suffix}"
                ),
            )
        if threshold > 0.0:
            return RoutingDecision(
                tier="local",
                reason=(
                    f"category '{category}' under tightened watch "
                    f"(threshold {threshold:.2f}); local Gemma tier first{suffix}"
                ),
            )
        return RoutingDecision(
            tier="local",
            reason=(
                f"category '{category}' healthy (threshold {threshold:.2f}); "
                f"local Gemma tier first{suffix}"
            ),
        )

    def should_escalate(
        self, category: str, verification: VerificationResult
    ) -> RoutingDecision | None:
        """After a local attempt: escalate iff Layer 1 rejected it."""
        if verification.passed:
            return None
        return RoutingDecision(
            tier="remote",
            reason=(
                f"layer-1 verification failed ({', '.join(verification.failures)}); "
                "escalating to remote tier"
            ),
        )

    def record_signal(self, category: str, verifier_passed: bool) -> None:
        """Layer 2 seam: online per-request EWMA update (batch policy applies
        via routing_policy between eval phases; per-request updates later)."""
