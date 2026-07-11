"""Part A: online Layer-2 EWMA closure on Router.record_signal."""

import pytest

from kaaval_assurance.pipeline import AssurancePipeline
from kaaval_assurance.providers import MockProvider
from kaaval_assurance.router import Router
from kaaval_assurance.trajectory import TrajectoryStore

INCIDENT = (
    "Core router CR-04 dropped all BGP sessions at 02:13; downstream OLT sites "
    "in region south lost upstream connectivity. Customer impact confirmed."
)
CONTRACT = "telecom.severity_classification"
CATEGORY = "severity_classification"


def make_pipeline(store, router, local_failure=None):
    return AssurancePipeline(
        router=router,
        local_provider=MockProvider(tier="local", failure_mode=local_failure),
        remote_provider=MockProvider(tier="remote", model_id="mock-remote-strong"),
        store=store,
    )


class TestOnlineDriftUpdates:
    def test_healthy_local_pass_leaves_drift_zero(self):
        store = TrajectoryStore(":memory:")
        try:
            router = Router()
            pipeline = make_pipeline(store, router)
            pipeline.handle_request(INCIDENT, CONTRACT)
            assert router.online_drift_for(CATEGORY) == 0.0
            assert router.current_policy_for(CATEGORY).action == "local_first"
        finally:
            store.close()

    def test_one_local_failure_gives_030_and_tightened_watch(self):
        store = TrajectoryStore(":memory:")
        try:
            router = Router()
            pipeline = make_pipeline(store, router, local_failure="bad_enum")
            pipeline.handle_request(INCIDENT, CONTRACT)
            assert router.online_drift_for(CATEGORY) == pytest.approx(0.30)
            assert router.current_policy_for(CATEGORY).action == "tightened"
        finally:
            store.close()

    def test_two_local_failures_give_051_and_force_remote(self):
        store = TrajectoryStore(":memory:")
        try:
            router = Router()
            pipeline = make_pipeline(store, router, local_failure="bad_enum")
            pipeline.handle_request(INCIDENT, CONTRACT, request_id="r1")
            pipeline.handle_request(INCIDENT, CONTRACT, request_id="r2")
            assert router.online_drift_for(CATEGORY) == pytest.approx(0.51)
            assert router.current_policy_for(CATEGORY).action == "force_remote"
        finally:
            store.close()

    def test_remote_rescue_does_not_alter_drift(self):
        store = TrajectoryStore(":memory:")
        try:
            router = Router()
            pipeline = make_pipeline(store, router, local_failure="bad_enum")
            result = pipeline.handle_request(INCIDENT, CONTRACT)
            assert result.escalated  # local failed, remote rescued
            drift_after_escalation = router.online_drift_for(CATEGORY)
            assert drift_after_escalation == pytest.approx(0.30)  # only the local signal counted
        finally:
            store.close()

    def test_third_request_pre_routes_remote_after_two_failures(self):
        store = TrajectoryStore(":memory:")
        try:
            router = Router()
            pipeline = make_pipeline(store, router, local_failure="bad_enum")
            pipeline.handle_request(INCIDENT, CONTRACT, request_id="r1")
            pipeline.handle_request(INCIDENT, CONTRACT, request_id="r2")

            decision = router.choose_tier(CATEGORY)
            assert decision.tier == "remote"
            assert "forces remote tier" in decision.reason
            assert "ewma drift 0.51" in decision.reason

            result = pipeline.handle_request(INCIDENT, CONTRACT, request_id="r3")
            assert result.response.tier == "remote"
            assert result.attempts == 1  # pre-routed, no local attempt at all
        finally:
            store.close()

    def test_unaffected_categories_stay_local_first(self):
        store = TrajectoryStore(":memory:")
        try:
            router = Router()
            pipeline = make_pipeline(store, router, local_failure="bad_enum")
            pipeline.handle_request(INCIDENT, CONTRACT, request_id="r1")
            pipeline.handle_request(INCIDENT, CONTRACT, request_id="r2")

            other_decision = router.choose_tier("incident_summary")
            assert other_decision.tier == "local"
            assert "healthy" in other_decision.reason
            assert router.online_drift_for("incident_summary") == 0.0
        finally:
            store.close()

    def test_disabled_online_adaptation_is_a_no_op(self):
        store = TrajectoryStore(":memory:")
        try:
            router = Router(online_adaptation=False)
            pipeline = make_pipeline(store, router, local_failure="bad_enum")
            pipeline.handle_request(INCIDENT, CONTRACT, request_id="r1")
            pipeline.handle_request(INCIDENT, CONTRACT, request_id="r2")
            assert router.online_drift_for(CATEGORY) == 0.0
            assert router.choose_tier(CATEGORY).tier == "local"
        finally:
            store.close()
