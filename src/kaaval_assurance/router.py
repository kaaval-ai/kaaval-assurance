"""Router: chooses the model tier per request category.

Default policy: local first for every category, escalate to remote when
Layer 1 rejects the local response. Layer-2 drift can tighten this per
category two ways:

  online   record_signal() updates a per-category EWMA after every local
           attempt and immediately re-derives category_thresholds via
           routing_policy — the very next request in that category sees the
           new posture. Remote-tier signals are ignored; only local attempts
           carry drift evidence. Disable with online_adaptation=False.
  batch    routing_policy.apply_policy() installs thresholds computed offline
           over a full evaluation run (used by the closed-loop demo, which
           disables online adaptation and applies phase-B drift by hand so
           its three teaching phases stay a controlled, discrete sequence).

Both paths write the same category_thresholds / category_policy_notes the
router reads at routing time, so choose_tier's behavior is identical either
way. With neither applied, behavior is the static local-first default.
"""

from .metrics import DEFAULT_EWMA_ALPHA
from .models import RoutingDecision, VerificationResult


class Router:
    def __init__(
        self,
        ewma_alpha: float = DEFAULT_EWMA_ALPHA,
        online_adaptation: bool = True,
    ) -> None:
        # Per-category escalation pressure in [0, 1].
        # 0.0 = always try local first; >= 1.0 = route straight to remote.
        # Populated by routing_policy.apply_policy (batch) or record_signal
        # (online) from Layer-2 drift scores.
        self.category_thresholds: dict[str, float] = {}
        # Human-readable policy context per category (drift band + action),
        # embedded in routing reasons so trajectory evidence is self-explaining.
        self.category_policy_notes: dict[str, str] = {}
        # Online Layer-2 EWMA smoothing factor and per-category drift state.
        # Every category starts from an explicit healthy seed of 0.0 (not
        # EwmaTracker's first-observation seed) so the first local failure in
        # a category always lands at exactly `ewma_alpha`, not 1.0.
        self.ewma_alpha = ewma_alpha
        self.online_adaptation = online_adaptation
        self._online_drift: dict[str, float] = {}

    def online_drift_for(self, category: str) -> float:
        """Read-only: current online Layer-2 drift for a category (0.0 seed)."""
        return self._online_drift.get(category, 0.0)

    def current_policy_for(self, category: str):
        """Read-only: the deterministic policy the current online drift maps to."""
        from .routing_policy import policy_for_category  # deferred: avoids import cycle

        return policy_for_category(category, self.online_drift_for(category))

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

    def record_signal(self, category: str, verifier_passed: bool, tier: str) -> None:
        """Online Layer 2 closure: update per-category drift after a local
        attempt, then immediately re-derive and apply this router's routing
        policy for that category so the next request in it is affected.

        Remote-tier signals are ignored — a remote rescue does not change
        what the local tier's reliability looks like. No-op when
        online_adaptation is False (the closed-loop demo disables this and
        applies batch policy by hand between its phases instead).
        """
        if tier != "local" or not self.online_adaptation:
            return

        from .routing_policy import policy_for_category  # deferred: avoids import cycle

        prior = self._online_drift.get(category, 0.0)
        observation = 0.0 if verifier_passed else 1.0
        drift = self.ewma_alpha * observation + (1 - self.ewma_alpha) * prior
        self._online_drift[category] = drift

        policy = policy_for_category(category, drift)
        self.category_thresholds[category] = policy.threshold
        self.category_policy_notes[category] = policy.reason
