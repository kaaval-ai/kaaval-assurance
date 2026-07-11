"""Part D: mock-only end-to-end seam — undersevere grounding failure ->
escalation -> recovery -> online EWMA closure -> pre-routing.

`undersevere` is a deterministic mock-tier failure mode (see
providers/mock.py FAILURE_MODES) used only to exercise this path in tests
and the reproducible demo. It never represents real Gemma behavior.
"""

import pytest

from kaaval_assurance.eval.dataset import load_dataset
from kaaval_assurance.pipeline import AssurancePipeline
from kaaval_assurance.providers import MockProvider
from kaaval_assurance.router import Router
from kaaval_assurance.trajectory import TrajectoryStore

STRESS_DATASET = "data/eval/telecom_stress.jsonl"
CATEGORY = "severity_classification"


def regional_outage_case():
    cases = {c.case_id: c for c in load_dataset(STRESS_DATASET)}
    return cases["sev-stress-001"]


def test_undersevere_grounding_catch_and_recover_drives_ewma_closure():
    case = regional_outage_case()
    assert case.contract_id == "telecom.severity_classification"

    store = TrajectoryStore(":memory:")
    try:
        router = Router()
        pipeline = AssurancePipeline(
            router=router,
            local_provider=MockProvider(tier="local", failure_mode="undersevere"),
            remote_provider=MockProvider(tier="remote", model_id="mock-remote-strong"),
            store=store,
        )

        # 1. First request: local undersevere P2 is caught by grounding and
        #    recovered by an escalation to the remote tier.
        result_1 = pipeline.handle_request(
            case.task_input, case.contract_id, request_id="e2e-1"
        )
        assert result_1.escalated
        assert result_1.attempts == 2
        assert result_1.verification.passed  # remote rescues
        assert result_1.response.tier == "remote"

        rows_1 = store.rows_for_request("e2e-1")
        assert len(rows_1) == 2
        local_row, remote_row = rows_1
        assert local_row.tier == "local"
        assert not local_row.verifier_passed
        assert local_row.verifier_failures == ["grounding:regional_outage_requires_p1"]
        assert remote_row.tier == "remote"
        assert remote_row.verifier_passed
        assert remote_row.escalated

        assert router.online_drift_for(CATEGORY) == pytest.approx(0.30)

        # 2. Second equivalent request: drift rises from 0.30 to 0.51.
        result_2 = pipeline.handle_request(
            case.task_input, case.contract_id, request_id="e2e-2"
        )
        assert result_2.escalated
        assert result_2.verification.passed
        assert router.online_drift_for(CATEGORY) == pytest.approx(0.51)
        assert router.current_policy_for(CATEGORY).action == "force_remote"

        # 3. Third equivalent request: pre-routed straight to remote.
        result_3 = pipeline.handle_request(
            case.task_input, case.contract_id, request_id="e2e-3"
        )
        assert result_3.attempts == 1
        assert not result_3.escalated  # no local attempt to escalate from
        assert result_3.response.tier == "remote"
        assert result_3.verification.passed
        assert "forces remote tier" in result_3.routing.reason
    finally:
        store.close()
