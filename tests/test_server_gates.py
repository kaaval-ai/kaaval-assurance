"""Server-side gates: client flags acknowledge, only operator env authorizes.

Review findings: (1) client-supplied confirm_spend=true was the only thing
standing between an unauthenticated caller and the server's Fireworks
credential; (2) live-run artifact export wrote into the same artifacts/
directory the evidence dashboard loads from, so any caller could poison
displayed evidence. Both now require explicit server-side env flags and
default closed.
"""

from pathlib import Path

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
    monkeypatch.delenv("KAAVAL_ALLOW_DIAGNOSTIC_RAW", raising=False)
    store = ArtifactStore(
        artifacts_dir=tmp_path / "artifacts", sample_dir=tmp_path / "sample"
    )
    return TestClient(
        create_app(store, export_root=tmp_path / "live-exports")
    )


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
        assert resp.status_code == 422
        assert "FIREWORKS_API_KEY" in resp.json()["detail"]
        assert "KAAVAL_ALLOW_PAID_REMOTE" not in resp.json()["detail"]

    def test_server_gate_does_not_replace_per_run_confirmation(
        self, live_client, monkeypatch
    ):
        monkeypatch.setenv("KAAVAL_ALLOW_PAID_REMOTE", "1")
        resp = live_client.post(
            "/api/runs",
            json={**RUN_BODY, "remote_provider": "fireworks", "confirm_spend": False},
        )
        assert resp.status_code == 403
        assert "confirm" in resp.json()["detail"].lower()
        assert "KAAVAL_ALLOW_PAID_REMOTE" not in resp.json()["detail"]

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
        assert len(written) == 1
        assert Path(written[0]).name == resp.json()["run_id"]
        assert Path(written[0]).parent.name == "live-exports"

    def test_authorized_exports_cannot_clobber_curated_evidence(
        self, tmp_path, monkeypatch
    ):
        monkeypatch.setenv("KAAVAL_LIVE_RUNS_ENABLED", "1")
        monkeypatch.setenv("KAAVAL_ALLOW_ARTIFACT_EXPORT", "1")
        curated_root = tmp_path / "artifacts"
        curated_root.mkdir()
        sealed_manifest = curated_root / "demo-live-manifest.json"
        sealed_manifest.write_text("sealed AMD evidence\n", encoding="utf-8")
        export_root = tmp_path / "live-exports"
        store = ArtifactStore(
            artifacts_dir=curated_root, sample_dir=tmp_path / "sample"
        )
        client = TestClient(create_app(store, export_root=export_root))

        first = client.post(
            "/api/runs", json={**RUN_BODY, "export_artifacts": True}
        )
        second = client.post(
            "/api/runs", json={**RUN_BODY, "export_artifacts": True}
        )

        assert first.status_code == second.status_code == 200
        assert first.json()["run_id"] != second.json()["run_id"]
        for body in (first.json(), second.json()):
            run_dir = export_root / body["run_id"]
            assert (run_dir / "demo-live-manifest.json").exists()
            assert all(name.startswith(f'{body["run_id"]}/') for name in body["artifacts_written"])
        assert sealed_manifest.read_text(encoding="utf-8") == "sealed AMD evidence\n"

    def test_non_export_runs_unaffected(self, live_client):
        resp = live_client.post("/api/runs", json=RUN_BODY)
        assert resp.status_code == 200
        assert resp.json()["artifacts_written"] == []


class TestGateVisibility:
    def test_health_reports_operator_capabilities(self, live_client, monkeypatch):
        closed = live_client.get("/api/health").json()
        assert closed["paid_remote_allowed"] is False
        assert closed["artifact_export_allowed"] is False
        assert closed["diagnostic_raw_allowed"] is False

        monkeypatch.setenv("KAAVAL_ALLOW_PAID_REMOTE", "1")
        monkeypatch.setenv("KAAVAL_ALLOW_ARTIFACT_EXPORT", "1")
        monkeypatch.setenv("KAAVAL_ALLOW_DIAGNOSTIC_RAW", "1")
        opened = live_client.get("/api/health").json()
        assert opened["paid_remote_allowed"] is True
        assert opened["artifact_export_allowed"] is True
        assert opened["diagnostic_raw_allowed"] is True
