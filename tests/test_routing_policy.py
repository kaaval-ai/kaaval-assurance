import pytest

from kaaval_assurance.router import Router
from kaaval_assurance.routing_policy import (
    FORCE_REMOTE_MIN_DRIFT,
    TIGHTEN_MIN_DRIFT,
    apply_policy,
    policy_for_category,
    policy_from_drift,
)


class TestPolicyBands:
    @pytest.mark.parametrize("drift", [0.0, 0.1, 0.19])
    def test_low_drift_local_first(self, drift):
        p = policy_for_category("severity_classification", drift)
        assert p.action == "local_first"
        assert p.threshold == 0.0
        assert "local-first" in p.reason

    @pytest.mark.parametrize("drift", [0.20, 0.35, 0.49])
    def test_mid_drift_tightened(self, drift):
        p = policy_for_category("severity_classification", drift)
        assert p.action == "tightened"
        assert p.threshold == pytest.approx(drift)
        assert "tightened watch" in p.reason

    @pytest.mark.parametrize("drift", [0.50, 0.75, 1.0])
    def test_high_drift_forces_remote(self, drift):
        p = policy_for_category("severity_classification", drift)
        assert p.action == "force_remote"
        assert p.threshold == 1.0
        assert "pre-route to remote tier" in p.reason

    def test_band_edges(self):
        assert policy_for_category("c", TIGHTEN_MIN_DRIFT).action == "tightened"
        assert (
            policy_for_category("c", FORCE_REMOTE_MIN_DRIFT).action == "force_remote"
        )

    def test_deterministic(self):
        drift = {"a": 0.9, "b": 0.3, "c": 0.05}
        assert policy_from_drift(drift) == policy_from_drift(drift)

    def test_only_affected_categories_tighten(self):
        policies = policy_from_drift(
            {"severity_classification": 0.9, "incident_summary": 0.0}
        )
        assert policies["severity_classification"].action == "force_remote"
        assert policies["incident_summary"].action == "local_first"


class TestRouterWithPolicy:
    def test_default_router_unchanged_without_policy(self):
        router = Router()
        decision = router.choose_tier("severity_classification")
        assert decision.tier == "local"
        assert "healthy" in decision.reason
        assert "[" not in decision.reason  # no policy note attached

    def test_force_remote_category_preroutes_with_drift_context(self):
        router = Router()
        apply_policy(router, policy_from_drift({"severity_classification": 0.85}))
        decision = router.choose_tier("severity_classification")
        assert decision.tier == "remote"
        assert "forces remote tier" in decision.reason
        assert "ewma drift 0.85" in decision.reason
        assert "pre-route" in decision.reason

    def test_tightened_category_stays_local_with_context(self):
        router = Router()
        apply_policy(router, policy_from_drift({"next_action_recommendation": 0.3}))
        decision = router.choose_tier("next_action_recommendation")
        assert decision.tier == "local"
        assert "tightened watch" in decision.reason
        assert "ewma drift 0.30" in decision.reason

    def test_unaffected_category_not_touched(self):
        router = Router()
        apply_policy(router, policy_from_drift({"severity_classification": 0.9}))
        decision = router.choose_tier("incident_summary")
        assert decision.tier == "local"
        assert "healthy" in decision.reason
