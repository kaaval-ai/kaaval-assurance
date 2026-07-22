"""The experimental live operations adapter uses real session stores safely."""

import json

import pytest
from fastapi.testclient import TestClient

from apps.api.artifacts import ArtifactStore
from apps.api.server import SessionManager, create_app, session_manager


RUN_BODY = {
    "task_input": "PRIVATE-CUSTOMER-CONTENT charged twice for a $120 order.",
    "contract_id": "support.refund_decision",
    "local_provider": "mock",
    "remote_provider": "mock",
}


def _clear_sessions():
    with session_manager.lock:
        for session in session_manager.sessions.values():
            with session.lock:
                session.store.close()
        session_manager.sessions.clear()


@pytest.fixture(autouse=True)
def isolated_sessions():
    _clear_sessions()
    yield
    _clear_sessions()


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("KAAVAL_LIVE_RUNS_ENABLED", "1")
    store = ArtifactStore(
        artifacts_dir=tmp_path / "artifacts",
        sample_dir=tmp_path / "sample",
    )
    return TestClient(create_app(store))


def test_empty_snapshot_is_live_but_has_no_claimed_rate(client):
    body = client.get("/api/ops/snapshot").json()
    assert body["schema_version"] == "0.1"
    assert body["provenance"] == "live"
    assert body["totals"]["decisions"] == 0
    assert body["totals"]["final_contract_conformance_rate"] is None
    assert body["decisions"] == []


def test_live_run_appears_as_redacted_recovered_decision(client):
    run = client.post(
        "/api/runs", json={**RUN_BODY, "failure_mode": "bad_enum"}
    )
    assert run.status_code == 200

    snapshot_response = client.get("/api/ops/snapshot")
    assert snapshot_response.status_code == 200
    body = snapshot_response.json()
    decision = next(
        item for item in body["decisions"] if item["decision_id"] == run.json()["run_id"]
    )
    assert decision["final_outcome"] == "recovered"
    assert decision["authority"] == "enforced"
    assert len(decision["attempts"]) == 2
    assert decision["attempts"][0]["failed_check_ids"] == ["enum:decision"]
    assert decision["attempts"][1]["escalated"] is True
    assert body["routing"][0]["verifier_failure_ewma"] == 0.3
    assert body["routing"][0]["action"] == "tightened"

    payload = json.dumps(body)
    assert "PRIVATE-CUSTOMER-CONTENT" not in payload
    assert "task_input" not in payload
    assert "raw_text" not in payload
    assert "error_message" not in payload


def test_double_contract_failure_is_no_safe_answer(client):
    run = client.post(
        "/api/runs",
        json={
            **RUN_BODY,
            "failure_mode": "bad_enum",
            "remote_failure_mode": "bad_enum",
        },
    )
    assert run.status_code == 200
    assert run.json()["result"]["status"] == "no_safe_answer"

    body = client.get("/api/ops/snapshot").json()
    decision = next(
        item for item in body["decisions"] if item["decision_id"] == run.json()["run_id"]
    )
    assert decision["final_outcome"] == "no_safe_answer"
    assert all(not attempt["contract_conformant"] for attempt in decision["attempts"])


def test_reset_removes_session_decisions_from_snapshot(client):
    run = client.post("/api/runs", json=RUN_BODY).json()
    session_id = run["session"]["session_id"]
    assert client.get("/api/ops/snapshot").json()["totals"]["decisions"] == 1

    reset = client.post(f"/api/live-sessions/{session_id}/reset")
    assert reset.status_code == 200
    assert client.get("/api/ops/snapshot").json()["totals"]["decisions"] == 0


def test_hosted_mode_is_closed_until_tenant_auth_exists(client, monkeypatch):
    monkeypatch.setenv("KAAVAL_DEPLOYMENT_MODE", "hosted")
    response = client.get("/api/ops/snapshot")
    assert response.status_code == 403
    assert "authenticated" in response.json()["detail"]


def test_read_only_snapshot_does_not_evict_at_session_capacity():
    manager = SessionManager()
    try:
        for _ in range(64):
            with manager.checkout(None, "mock", "mock"):
                pass
        before = set(manager.sessions)

        snapshot_inputs = manager.ops_inputs()

        assert len(snapshot_inputs) == 64
        assert set(manager.sessions) == before
    finally:
        with manager.lock:
            for session in manager.sessions.values():
                with session.lock:
                    session.store.close()
            manager.sessions.clear()
