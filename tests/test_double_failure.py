"""The unhappy end: both tiers fail Layer 1; the answer is honestly unverified.

remote_failure_mode (mock remote only) demonstrates that the escalation
tier's output is verified exactly like the local tier's — malformed output
from the expensive model is never accepted because it was expensive, and a
remote failure is never Layer-2 signal about local health.
"""

import pytest
from fastapi.testclient import TestClient

from apps.api.artifacts import ArtifactStore
from apps.api.server import create_app
from kaaval_assurance.demo import run_live_demo
from kaaval_assurance.router import Router

INCIDENT = "Customer: charged twice for order #88231, refund the duplicate $129.99."

RUN_BODY = {
    "task_input": INCIDENT,
    "contract_id": "support.refund_decision",
    "local_provider": "mock",
    "remote_provider": "mock",
}


class TestDoubleFailurePath:
    def test_both_tiers_failing_returns_unverified(self):
        demo = run_live_demo(
            task_input=INCIDENT,
            contract_id="support.refund_decision",
            failure_mode="out_of_range",
            remote_failure_mode="out_of_range",
        )
        assert demo.result.escalated
        assert demo.result.attempts == 2
        assert not demo.result.verification.passed
        assert "range:refund_amount_usd" in demo.result.verification.failures
        assert demo.local_row is not None and not demo.local_row.verifier_passed
        assert demo.remote_row is not None and not demo.remote_row.verifier_passed

    def test_remote_failure_never_feeds_local_drift(self):
        router = Router()
        demo = run_live_demo(
            task_input=INCIDENT,
            contract_id="support.refund_decision",
            failure_mode="bad_enum",
            remote_failure_mode="bad_enum",
            router=router,
        )
        assert not demo.result.verification.passed
        # One local failure only: 0.0 -> 0.3. The remote failure is the
        # remote tier's problem, not local-drift signal.
        assert router.online_drift_for("refund_decision") == pytest.approx(0.3)

    def test_remote_injection_requires_mock_remote_api(self, tmp_path, monkeypatch):
        monkeypatch.setenv("KAAVAL_LIVE_RUNS_ENABLED", "1")
        store = ArtifactStore(
            artifacts_dir=tmp_path / "artifacts", sample_dir=tmp_path / "sample"
        )
        client = TestClient(create_app(store))
        resp = client.post(
            "/api/runs",
            json={
                **RUN_BODY,
                "remote_provider": "fireworks",
                "remote_failure_mode": "bad_enum",
            },
        )
        assert resp.status_code == 422
        assert "mock remote" in resp.json()["detail"]

    def test_double_failure_visible_through_api(self, tmp_path, monkeypatch):
        monkeypatch.setenv("KAAVAL_LIVE_RUNS_ENABLED", "1")
        store = ArtifactStore(
            artifacts_dir=tmp_path / "artifacts", sample_dir=tmp_path / "sample"
        )
        client = TestClient(create_app(store))
        body = client.post(
            "/api/runs",
            json={
                **RUN_BODY,
                "failure_mode": "out_of_range",
                "remote_failure_mode": "out_of_range",
            },
        ).json()
        assert body["result"]["verified"] is False
        assert body["result"]["escalated"] is True
        assert "range:refund_amount_usd" in body["result"]["failures"]
        rows = body["trajectory"]
        assert len(rows) == 2
        assert not rows[0]["verifier_passed"] and not rows[1]["verifier_passed"]
