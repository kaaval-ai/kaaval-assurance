"""Server-side gates: client flags acknowledge, only operator env authorizes.

Review findings: (1) client-supplied confirm_spend=true was the only thing
standing between an unauthenticated caller and the server's Fireworks
credential; (2) live-run artifact export wrote into the same artifacts/
directory the evidence dashboard loads from, so any caller could poison
displayed evidence. Both now require explicit server-side env flags and
default closed.
"""

import pytest
from fastapi.testclient import TestClient

from apps.api.artifacts import ArtifactStore
from apps.api.server import create_app

RUN_BODY = {
    "task_input": "Customer: charged twice for order #88231, refund the duplicate $129.99.",
    "contract_id": "support.refund_decision",
    "local_provider": "mock",
    "remote_provider": "mock",
}


@pytest.fixture()
def live_client(tmp_path, monkeypatch):
    monkeypatch.setenv("KAAVAL_LIVE_RUNS_ENABLED", "1")
    monkeypatch.delenv("KAAVAL_ALLOW_PAID_REMOTE", raising=False)
    monkeypatch.delenv("KAAVAL_ALLOW_ARTIFACT_EXPORT", raising=False)
    store = ArtifactStore(
        artifacts_dir=tmp_path / "artifacts", sample_dir=tmp_path / "sample"
    )
    return TestClient(create_app(store))


class TestPaidRemoteGate:
    def test_client_confirm_spend_alone_is_not_authorization(self, live_client):
        resp = live_client.post(
            "/api/runs",
            json={**RUN_BODY, "remote_provider": "fireworks", "confirm_spend": True},
        )
        assert resp.status_code == 403
        assert "KAAVAL_ALLOW_PAID_REMOTE" in resp.json()["detail"]

    def test_server_env_opens_the_gate(self, live_client, monkeypatch):
        monkeypatch.setenv("KAAVAL_ALLOW_PAID_REMOTE", "1")
        monkeypatch.delenv("FIREWORKS_API_KEY", raising=False)
        resp = live_client.post(
            "/api/runs",
            json={**RUN_BODY, "remote_provider": "fireworks", "confirm_spend": True},
        )
        # Past the gate: the failure (if any) is now about provider config,
        # never about the server-side authorization gate.
        assert "KAAVAL_ALLOW_PAID_REMOTE" not in resp.json().get("detail", "")

    def test_mock_remote_needs_no_gate(self, live_client):
        resp = live_client.post("/api/runs", json=RUN_BODY)
        assert resp.status_code == 200


class TestArtifactExportGate:
    def test_export_disabled_by_default(self, live_client):
        resp = live_client.post(
            "/api/runs", json={**RUN_BODY, "export_artifacts": True}
        )
        assert resp.status_code == 403
        assert "KAAVAL_ALLOW_ARTIFACT_EXPORT" in resp.json()["detail"]
        assert "curated offline" in resp.json()["detail"]

    def test_export_allowed_with_server_env(self, live_client, monkeypatch):
        written = []

        def fake_export(demo, out_dir):
            written.append(str(out_dir))
            return []

        monkeypatch.setenv("KAAVAL_ALLOW_ARTIFACT_EXPORT", "1")
        monkeypatch.setattr("apps.api.server.export_live_demo_artifacts", fake_export)
        resp = live_client.post(
            "/api/runs", json={**RUN_BODY, "export_artifacts": True}
        )
        assert resp.status_code == 200
        assert written  # export ran, through the stub

    def test_non_export_runs_unaffected(self, live_client):
        resp = live_client.post("/api/runs", json=RUN_BODY)
        assert resp.status_code == 200
        assert resp.json()["artifacts_written"] == []
