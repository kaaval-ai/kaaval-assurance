"""The boundary fails closed: transport errors are recorded, routed, typed.

External review finding: provider.generate() was unwrapped, so a vLLM
timeout escaped as an exception — no trajectory row, no escalation, and
"every attempt is recorded" was false for the most production-likely
failure. These tests pin the fixed behavior for the three scenarios the
review demanded: local outage, remote outage, and double-invalid output.
"""

import pytest
from fastapi.testclient import TestClient

from apps.api.artifacts import ArtifactStore
from apps.api.server import create_app
from kaaval_assurance.models import ModelResponse
from kaaval_assurance.pipeline import AssurancePipeline
from kaaval_assurance.providers import MockProvider, Provider
from kaaval_assurance.router import Router
from kaaval_assurance.trajectory import TrajectoryStore

INCIDENT = (
    "Core router CR-04 dropped all BGP sessions at 02:13; downstream OLT "
    "sites in region south lost upstream connectivity. Customer impact "
    "confirmed across 40k subscribers."
)
CONTRACT = "telecom.severity_classification"


class OutageProvider(Provider):
    """A provider whose endpoint is down: every call raises."""

    def __init__(self, tier: str, exc: Exception | None = None):
        self.provider_name = f"outage-{tier}"
        self.model_id = f"outage-model-{tier}"
        self.tier = tier
        self.exc = exc or ConnectionError("connection refused")
        self.calls = 0

    def generate(self, request_id, task_input, contract) -> ModelResponse:
        self.calls += 1
        raise self.exc


@pytest.fixture()
def store():
    s = TrajectoryStore(":memory:")
    yield s
    s.close()


def make_pipeline(store, local, remote):
    return AssurancePipeline(
        router=Router(),
        local_provider=local,
        remote_provider=remote,
        store=store,
    )


class TestLocalOutage:
    def test_local_outage_recorded_and_rescued_remotely(self, store):
        local = OutageProvider("local")
        pipeline = make_pipeline(
            store, local, MockProvider(tier="remote", model_id="mock-remote-strong")
        )
        result = pipeline.handle_request(INCIDENT, CONTRACT)

        assert local.calls == 1
        assert result.escalated
        assert result.attempts == 2
        assert result.verification.passed  # remote rescued the outage
        assert result.response.tier == "remote"

        rows = store.all_rows()
        assert len(rows) == 2  # the outage attempt IS recorded
        assert rows[0].tier == "local"
        assert not rows[0].verifier_passed
        assert rows[0].verifier_failures == ["transport:ConnectionError"]
        assert rows[0].raw_text == ""
        assert rows[0].attempt_status == "provider_error"
        assert rows[0].error_type == "ConnectionError"
        assert rows[0].error_message == "provider generation failed"
        assert rows[1].tier == "remote"
        assert rows[1].verifier_passed

    def test_local_outage_feeds_drift_like_a_failure(self, store):
        # Deliberate design: a local tier that keeps timing out should lose
        # traffic to remote exactly like one producing malformed output.
        router = Router()
        pipeline = AssurancePipeline(
            router=router,
            local_provider=OutageProvider("local"),
            remote_provider=MockProvider(tier="remote", model_id="mock-remote-strong"),
            store=store,
        )
        pipeline.handle_request(INCIDENT, CONTRACT)
        assert router.online_drift_for("severity_classification") == pytest.approx(0.3)


class TestRemoteOutage:
    def test_escalation_into_dead_remote_returns_typed_failure(self, store):
        pipeline = make_pipeline(
            store,
            MockProvider(tier="local", failure_mode="missing_field"),
            OutageProvider("remote", TimeoutError("read timed out")),
        )
        result = pipeline.handle_request(INCIDENT, CONTRACT)

        assert result.escalated
        assert result.attempts == 2
        assert not result.verification.passed
        assert result.status == "no_safe_answer"
        assert result.accepted_response is None
        assert result.verification.failures == ["transport:TimeoutError"]
        assert result.response.parsed is None  # typed failure, not an answer

        rows = store.all_rows()
        assert len(rows) == 2
        assert not rows[0].verifier_passed  # local Layer-1 failure
        assert rows[1].verifier_failures == ["transport:TimeoutError"]


class TestTotalOutage:
    def test_both_tiers_down_still_records_everything(self, store):
        pipeline = make_pipeline(
            store, OutageProvider("local"), OutageProvider("remote")
        )
        result = pipeline.handle_request(INCIDENT, CONTRACT)

        assert result.escalated
        assert result.attempts == 2
        assert not result.verification.passed
        assert result.response.parsed is None
        rows = store.all_rows()
        assert len(rows) == 2
        assert all(not r.verifier_passed for r in rows)
        assert all(r.verifier_failures[0].startswith("transport:") for r in rows)


class TestApiFailClosed:
    @pytest.fixture()
    def live_client(self, tmp_path, monkeypatch):
        monkeypatch.setenv("KAAVAL_LIVE_RUNS_ENABLED", "1")
        store = ArtifactStore(
            artifacts_dir=tmp_path / "artifacts", sample_dir=tmp_path / "sample"
        )
        return TestClient(create_app(store))

    DOUBLE_INVALID = {
        "task_input": INCIDENT,
        "contract_id": CONTRACT,
        "local_provider": "mock",
        "remote_provider": "mock",
        "failure_mode": "bad_enum",
        "remote_failure_mode": "bad_enum",
    }

    def test_unverified_answer_withheld_by_default(self, live_client):
        body = live_client.post("/api/runs", json=self.DOUBLE_INVALID).json()
        assert body["result"]["status"] == "no_safe_answer"
        assert body["result"]["contract_conformant"] is False
        assert body["result"]["verified"] is False
        assert body["result"]["answer"] is None
        assert body["result"]["raw_text"] == ""
        assert body["result"]["unverified_output_withheld"] is True
        assert all(row["raw_text"] == "" for row in body["trajectory"])
        assert all(row["raw_text_withheld"] for row in body["trajectory"])

    def test_inspection_surface_requires_operator_gate(self, live_client):
        response = live_client.post(
            "/api/runs", json={**self.DOUBLE_INVALID, "include_unverified_raw": True}
        )
        assert response.status_code == 403
        assert "KAAVAL_ALLOW_DIAGNOSTIC_RAW" in response.json()["detail"]

    def test_operator_gated_diagnostics_never_become_answer(
        self, live_client, monkeypatch
    ):
        monkeypatch.setenv("KAAVAL_ALLOW_DIAGNOSTIC_RAW", "1")
        body = live_client.post(
            "/api/runs", json={**self.DOUBLE_INVALID, "include_unverified_raw": True}
        ).json()
        assert body["result"]["status"] == "no_safe_answer"
        assert body["result"]["verified"] is False
        assert body["result"]["answer"] is None
        assert body["result"]["diagnostic_raw_text"]
        assert body["result"]["unverified_output_withheld"] is False
        assert all(row["raw_text"] for row in body["trajectory"])
        assert not any(row["raw_text_withheld"] for row in body["trajectory"])

    def test_verified_answer_always_returned(self, live_client):
        body = live_client.post(
            "/api/runs",
            json={
                "task_input": INCIDENT,
                "contract_id": CONTRACT,
                "local_provider": "mock",
                "remote_provider": "mock",
            },
        ).json()
        assert body["result"]["status"] == "accepted"
        assert body["result"]["contract_conformant"] is True
        assert body["result"]["verified"] is True
        assert body["result"]["answer"] is not None
        assert body["result"]["unverified_output_withheld"] is False
