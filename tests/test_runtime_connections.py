import json
import time

import pytest
import requests
from fastapi.testclient import TestClient

import apps.api.server as server_module
from apps.api.artifacts import ArtifactStore
from apps.api.runtime_connections import RuntimeConnectionManager


class FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload or {"data": [{"id": "gemma3:4b"}]}
        self.text = json.dumps(self._payload)

    def json(self):
        return self._payload


@pytest.fixture()
def byok_env(monkeypatch):
    monkeypatch.setenv("KAAVAL_ALLOW_BYOK", "1")
    monkeypatch.setenv("KAAVAL_LIVE_RUNS_ENABLED", "1")
    monkeypatch.setenv("KAAVAL_DEPLOYMENT_MODE", "local")
    monkeypatch.delenv("KAAVAL_ALLOW_CUSTOM_ENDPOINTS", raising=False)


def test_connection_metadata_never_exposes_secret(byok_env, monkeypatch):
    monkeypatch.setattr(
        "apps.api.runtime_connections.requests.get",
        lambda *args, **kwargs: FakeResponse(),
    )
    manager = RuntimeConnectionManager()
    connection = manager.create(
        provider="fireworks",
        role="primary",
        model_id="accounts/fireworks/models/test-model",
        api_key="secret-key-value",
    )

    metadata = connection.public_metadata(manager.ttl_seconds)
    assert "secret-key-value" not in json.dumps(metadata)
    assert "api_key" not in metadata
    assert metadata["provider"] == "fireworks"
    assert connection.build_provider().tier == "local"


def test_hosted_mode_rejects_direct_local_endpoint(byok_env, monkeypatch):
    monkeypatch.setenv("KAAVAL_DEPLOYMENT_MODE", "hosted")
    manager = RuntimeConnectionManager()
    with pytest.raises(ValueError, match="unavailable from hosted mode"):
        manager.create(
            provider="ollama",
            role="primary",
            model_id="gemma3:4b",
            probe=False,
        )


def test_local_connection_rejects_model_not_in_runtime_inventory(
    byok_env, monkeypatch
):
    monkeypatch.setattr(
        "apps.api.runtime_connections.requests.get",
        lambda *args, **kwargs: FakeResponse(
            payload={"data": [{"id": "gemma4:12b"}, {"id": "qwen3.5:9b"}]}
        ),
    )
    manager = RuntimeConnectionManager()

    with pytest.raises(
        RuntimeError,
        match=(
            "model 'gemma3:4b' is not served.*"
            "gemma4:12b, qwen3.5:9b"
        ),
    ):
        manager.create(
            provider="ollama", role="primary", model_id="gemma3:4b"
        )


def test_hosted_custom_endpoint_rejects_private_address(byok_env, monkeypatch):
    monkeypatch.setenv("KAAVAL_DEPLOYMENT_MODE", "hosted")
    monkeypatch.setenv("KAAVAL_ALLOW_CUSTOM_ENDPOINTS", "1")
    manager = RuntimeConnectionManager()
    with pytest.raises(ValueError, match="public addresses"):
        manager.create(
            provider="openai_compatible",
            role="primary",
            model_id="gemma-tunnel",
            base_url="https://127.0.0.1/v1",
            probe=False,
        )


def test_connection_expiry_removes_secret_state(byok_env, monkeypatch):
    monkeypatch.setattr(
        "apps.api.runtime_connections.requests.get",
        lambda *args, **kwargs: FakeResponse(),
    )
    manager = RuntimeConnectionManager(ttl_seconds=1)
    connection = manager.create(
        provider="ollama", role="primary", model_id="gemma3:4b"
    )
    connection.last_accessed = time.time() - 2
    with pytest.raises(KeyError, match="expired"):
        manager.get(connection.connection_id)


def test_runtime_connection_drives_real_pipeline_and_live_readers(
    tmp_path, byok_env, monkeypatch
):
    monkeypatch.setattr(
        "apps.api.runtime_connections.requests.get",
        lambda *args, **kwargs: FakeResponse(),
    )

    def fake_post(self, url, json=None, headers=None, timeout=None):
        content = {
            "severity": "P1",
            "confidence": 0.98,
            "rationale": "All BGP sessions dropped with customer impact.",
        }
        return FakeResponse(
            payload={
                "choices": [{"message": {"content": __import__("json").dumps(content)}}],
                "usage": {"prompt_tokens": 30, "completion_tokens": 18},
            }
        )

    monkeypatch.setattr(requests.Session, "post", fake_post)
    manager = RuntimeConnectionManager()
    monkeypatch.setattr(server_module, "runtime_connection_manager", manager)
    store = ArtifactStore(
        artifacts_dir=tmp_path / "artifacts", sample_dir=tmp_path / "sample"
    )
    client = TestClient(server_module.create_app(store))

    connected = client.post(
        "/api/runtime-connections",
        json={
            "provider": "ollama",
            "role": "primary",
            "model_id": "gemma3:4b",
            "base_url": "http://host.docker.internal:11434/v1",
        },
    )
    assert connected.status_code == 200
    connection_id = connected.json()["connection_id"]

    response = client.post(
        "/api/runs",
        json={
            "task_input": (
                "Core router dropped all BGP sessions, sites lost upstream "
                "connectivity, and customer impact is confirmed."
            ),
            "contract_id": "telecom.severity_classification",
            "local_provider": "mock",
            "remote_provider": "mock",
            "confirm_spend": False,
            "failure_mode": None,
            "remote_failure_mode": None,
            "export_artifacts": False,
            "primary_connection_id": connection_id,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["result"]["status"] == "accepted"
    assert body["request"]["local_provider"] == "ollama"
    assert body["trajectory"][0]["provider"] == "ollama"
    assert body["telemetry"]["attempts_detail"][0]["provider"] == "ollama"
    assert body["telemetry"]["runtime"]["status"] == "configured"
    assert body["telemetry"]["runtime"]["profile"]["provider"] == "ollama"
    assert body["runtime_profile"]["model_id"] == "gemma3:4b"


def test_fireworks_byok_requires_per_run_confirmation(
    tmp_path, byok_env, monkeypatch
):
    monkeypatch.setattr(
        "apps.api.runtime_connections.requests.get",
        lambda *args, **kwargs: FakeResponse(),
    )
    manager = RuntimeConnectionManager()
    monkeypatch.setattr(server_module, "runtime_connection_manager", manager)
    client = TestClient(
        server_module.create_app(
            ArtifactStore(
                artifacts_dir=tmp_path / "artifacts",
                sample_dir=tmp_path / "sample",
            )
        )
    )
    connected = client.post(
        "/api/runtime-connections",
        json={
            "provider": "fireworks",
            "role": "primary",
            "model_id": "accounts/fireworks/models/test-model",
            "api_key": "secret-key-value",
        },
    ).json()
    response = client.post(
        "/api/runs",
        json={
            "task_input": "Customer impact confirmed.",
            "contract_id": "telecom.severity_classification",
            "local_provider": "mock",
            "remote_provider": "mock",
            "confirm_spend": False,
            "failure_mode": None,
            "remote_failure_mode": None,
            "export_artifacts": False,
            "primary_connection_id": connected["connection_id"],
        },
    )
    assert response.status_code == 403
    assert "confirm" in response.json()["detail"].lower()
    assert "secret-key-value" not in response.text
