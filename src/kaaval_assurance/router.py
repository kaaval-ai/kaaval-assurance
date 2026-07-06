"""Router: chooses the model tier per request category.

Jul 5 scope: static policy — local first for every category, escalate to
remote when Layer 1 rejects the local response. The per-category threshold
map is the seam Layer 2 (EWMA drift tracking) tightens from Jul 6 onward;
record_signal is a no-op until then.
"""

from .models import RoutingDecision, VerificationResult


class Router:
    def __init__(self) -> None:
        # Layer 2 seam: per-category escalation pressure in [0, 1].
        # 0.0 = always try local first; 1.0 = route straight to remote.
        # Static at 0.0 for Jul 5; EWMA-driven tightening lands Jul 6.
        self.category_thresholds: dict[str, float] = {}

    def choose_tier(self, category: str) -> RoutingDecision:
        threshold = self.category_thresholds.get(category, 0.0)
        if threshold >= 1.0:
            return RoutingDecision(
                tier="remote",
                reason=(
                    f"category '{category}' routing threshold {threshold:.2f} "
                    "forces remote tier"
                ),
            )
        return RoutingDecision(
            tier="local",
            reason=(
                f"category '{category}' healthy (threshold {threshold:.2f}); "
                "local Gemma tier first"
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
        """Layer 2 seam. EWMA update lands Jul 6; no-op for Jul 5 mock path."""
