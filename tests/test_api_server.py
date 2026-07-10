"""Flight Deck API tests: artifact adapter truth rules + gated live runs.

No network, no secrets: providers are mock, artifact roots are tmp dirs.
"""

import json

import pytest
from fastapi.testclient import TestClient

from apps.api.artifacts import ArtifactStore
from apps.api.server import create_app

VALID_TELEMETRY = {
    "run_id": "r1",
    "requests": 2,
    "attempts": 3,
    "runtime": {"status": "planned"},
    "attempts_detail": [{"provider": "mock"}],
    "claims": [],
}
AMD_PROBE = {
    "system": {"cwd": "/workspace/x", "under_workspace": True},
    "commands": {
        "rocm_smi_product": {
            "available": True,
            "source": "measured",
            "output": "GPU[0] Card series: AMD Instinct",
        }
    },
}


VALID_TRAJECTORY = [{"request_id": "r1"}]

def make_store(tmp_path, artifacts=None, sample=None, manifest=None):
    a_dir = tmp_path / "artifacts"
    s_dir = tmp_path / "sample"
    a_dir.mkdir()
    s_dir.mkdir()
    for name, data in (artifacts or {}).items():
        (a_dir / name).write_text(
            data if isinstance(data, str) else json.dumps(data)
        )
    for name, data in (sample or {}).items():
        (s_dir / name).write_text(
            data if isinstance(data, str) else json.dumps(data)
        )
    if manifest:
        # Create manifest in artifacts by default unless specified otherwise
        (a_dir / "demo-live-manifest.json").write_text(json.dumps(manifest))
    return ArtifactStore(artifacts_dir=a_dir, sample_dir=s_dir)

def client_for(store):
    return TestClient(create_app(store))


class TestArtifactResolution:
    def test_real_artifact_preferred_over_sample(self, tmp_path):
        manifest_real = {
            "run_id": "real",
            "artifacts": {"telemetry": "demo-live-telemetry.json", "trajectory": "demo-live-trajectory.json"}
        }
        manifest_sample = {
            "run_id": "sample",
            "artifacts": {"telemetry": "demo-live-telemetry.json", "trajectory": "demo-live-trajectory.json"}
        }
        store = make_store(
            tmp_path,
            artifacts={"demo-live-telemetry.json": {**VALID_TELEMETRY, "run_id": "real"}, "demo-live-trajectory.json": [{"request_id": "real"}], "demo-live-manifest.json": manifest_real},
            sample={"demo-live-telemetry.json": {**VALID_TELEMETRY, "run_id": "sample"}, "demo-live-trajectory.json": [{"request_id": "sample"}], "demo-live-manifest.json": manifest_sample},
        )
        data, prov = store.resolve("telemetry")
        assert data["run_id"] == "real"
        assert prov["origin"] == "artifacts"

    def test_sample_fallback_labeled_sample(self, tmp_path):
        store = make_store(
            tmp_path, sample={"telemetry-truth.json": VALID_TELEMETRY, "trajectory-sample.json": [{"request_id": "r1"}]}
        )
        data, prov = store.resolve("telemetry")
        assert data is not None
        assert prov["origin"] == "sample"
        assert store.dashboard()["label"] == "SAMPLE"
        assert store.dashboard()["used_sample"] is True

    def test_missing_artifact_is_honestly_unavailable(self, tmp_path):
        store = make_store(tmp_path)
        data, prov = store.resolve("telemetry")
        assert data is None
        assert prov == {
            "available": False,
            "artifact": None,
            "origin": "not_available",
            "modified_at": None,
        }
        assert store.dashboard()["label"] == "UNAVAILABLE"

    def test_malformed_real_json_falls_through_to_sample(self, tmp_path):
        store = make_store(
            tmp_path,
            artifacts={"telemetry-truth.json": "{not json"},
            sample={"telemetry-truth.json": VALID_TELEMETRY, "trajectory-sample.json": [{"request_id": "r1"}]},
        )
        data, prov = store.resolve("telemetry")
        assert data["run_id"] == "r1"  # sample content, never a stale mix
        assert prov["origin"] == "sample"

    def test_alias_names_supported(self, tmp_path):
        manifest = {
            "run_id": "r1",
            "artifacts": {"telemetry": "demo-live-telemetry.json", "trajectory": "demo-live-trajectory.json"}
        }
        store = make_store(
            tmp_path,
            artifacts={"demo-live-telemetry.json": VALID_TELEMETRY, "demo-live-trajectory.json": [{"request_id": "r1"}], "demo-live-manifest.json": manifest},
        )
        data, prov = store.resolve("telemetry")
        assert data is not None
        assert prov["artifact"] == "demo-live-telemetry.json"

    def test_provenance_never_leaks_paths(self, tmp_path):
        store = make_store(
            tmp_path, sample={"telemetry-truth.json": VALID_TELEMETRY, "trajectory-sample.json": [{"request_id": "r1"}]}
        )
        payload = json.dumps(store.dashboard()["provenance"])
        assert str(tmp_path) not in payload
        assert "/Users/" not in payload and "/home/" not in payload


class TestDashboardLabels:
    def test_amd_measured_requires_coherent_bundle_with_all_checks(self, tmp_path):
        telemetry = {
            "run_id": "r1",
            "requests": 1,
            "attempts": 1,
            "attempts_detail": [{"provider": "vllm-gemma", "tier": "local"}],
            "runtime": {
                "profile": {
                    "provider": "vllm-gemma",
                    "endpoint_type": "openai_compatible",
                    "model_id": "gemma-test"
                }
            },
            "claims": []
        }
        probe = {
            "system": {"cwd": "/workspace", "under_workspace": True},
            "commands": {
                "rocm_smi_product": {
                    "available": True,
                    "source": "measured",
                    "output": "GPU"
                }
            },
            "endpoint": {
                "configured_model": "gemma-test",
                "configured_model_served": True
            }
        }
        manifest = {
            "run_id": "r1",
            "artifacts": {
                "telemetry": "demo-live-telemetry.json",
                "trajectory": "demo-live-trajectory.json",
                "runtime_probe": "runtime-probe.json"
            }
        }
        store = make_store(
            tmp_path,
            artifacts={
                "demo-live-telemetry.json": telemetry,
                "demo-live-trajectory.json": [{"request_id": "r1"}],
                "runtime-probe.json": probe,
                "demo-live-manifest.json": manifest
            }
        )
        dash = store.dashboard()
        assert dash["amd"]["status"] == "measured"
        assert dash["label"] == "MEASURED AMD RUN"
        assert dash["bundle_consistent"] is True

    def test_unrelated_amd_probe_fireworks_telemetry_not_amd(self, tmp_path):
        telemetry = {
            **VALID_TELEMETRY,
            "attempts_detail": [{"provider": "fireworks", "tier": "remote"}],
        }
        manifest = {
            "run_id": "r1",
            "artifacts": {
                "telemetry": "demo-live-telemetry.json",
                "trajectory": "demo-live-trajectory.json",
                "runtime_probe": "runtime-probe.json"
            }
        }
        store = make_store(
            tmp_path,
            artifacts={
                "demo-live-telemetry.json": telemetry,
                "demo-live-trajectory.json": [{"request_id": "r1"}],
                "runtime-probe.json": AMD_PROBE,
                "demo-live-manifest.json": manifest
            }
        )
        dash = store.dashboard()
        assert dash["amd"]["status"] == "pending"
        assert "no local vllm-gemma attempt" in dash["amd"]["reason"]
        assert dash["label"] == "CAPTURED FIREWORKS RUN"

    def test_unrelated_amd_probe_mock_telemetry_not_amd(self, tmp_path):
        telemetry = {
            **VALID_TELEMETRY,
            "attempts_detail": [{"provider": "mock", "tier": "local"}],
        }
        manifest = {
            "run_id": "r1",
            "artifacts": {
                "telemetry": "demo-live-telemetry.json",
                "trajectory": "demo-live-trajectory.json",
                "runtime_probe": "runtime-probe.json"
            }
        }
        store = make_store(
            tmp_path,
            artifacts={
                "demo-live-telemetry.json": telemetry,
                "demo-live-trajectory.json": [{"request_id": "r1"}],
                "runtime-probe.json": AMD_PROBE,
                "demo-live-manifest.json": manifest
            }
        )
        dash = store.dashboard()
        assert dash["amd"]["status"] == "pending"
        assert "no local vllm-gemma attempt" in dash["amd"]["reason"]
        assert dash["label"] == "CAPTURED LOCAL RUN"
        
    def test_vllm_telemetry_without_served_model_not_amd(self, tmp_path):
        telemetry = {
            "run_id": "r1",
            "attempts_detail": [{"provider": "vllm-gemma", "tier": "local"}],
            "runtime": {"profile": {"provider": "vllm-gemma", "endpoint_type": "openai_compatible", "model_id": "gemma-test"}},
            "claims": []
        }
        probe = {
            "commands": {"rocm_smi_product": {"available": True, "source": "measured"}},
            "endpoint": {"configured_model": "gemma-test", "configured_model_served": False}
        }
        manifest = {
            "run_id": "r1",
            "artifacts": {
                "telemetry": "demo-live-telemetry.json",
                "trajectory": "demo-live-trajectory.json",
                "runtime_probe": "runtime-probe.json"
            }
        }
        store = make_store(
            tmp_path,
            artifacts={
                "demo-live-telemetry.json": telemetry,
                "demo-live-trajectory.json": [{"request_id": "r1"}],
                "runtime-probe.json": probe,
                "demo-live-manifest.json": manifest
            }
        )
        dash = store.dashboard()
        assert dash["amd"]["status"] == "pending"
        assert "configured model not confirmed served" in dash["amd"]["reason"]

    def test_sample_probe_cannot_claim_measured(self, tmp_path):
        telemetry = {
            "run_id": "r1",
            "attempts_detail": [{"provider": "vllm-gemma", "tier": "local"}],
            "runtime": {"profile": {"provider": "vllm-gemma", "endpoint_type": "openai_compatible", "model_id": "gemma-test"}},
            "claims": []
        }
        probe = {
            "commands": {"rocm_smi_product": {"available": True, "source": "measured"}},
            "endpoint": {"configured_model": "gemma-test", "configured_model_served": True}
        }
        manifest = {
            "run_id": "r1",
            "artifacts": {
                "telemetry": "demo-live-telemetry.json",
                "trajectory": "demo-live-trajectory.json",
                "runtime_probe": "runtime-probe.json"
            }
        }
        store = make_store(
            tmp_path,
            sample={
                "demo-live-telemetry.json": telemetry,
                "demo-live-trajectory.json": [{"request_id": "r1"}],
                "runtime-probe.json": probe,
                "demo-live-manifest.json": manifest
            }
        )
        dash = store.dashboard()
        assert dash["amd"]["status"] != "measured"
        assert dash["label"] == "SAMPLE"

    def test_inconsistent_bundle_labeled_unverified(self, tmp_path):
        telemetry = {
            **VALID_TELEMETRY,
            "run_id": "r1",
        }
        trajectory = [{"request_id": "r2"}] # Mismatched run ID!
        manifest = {
            "run_id": "r1",
            "artifacts": {
                "telemetry": "demo-live-telemetry.json",
                "trajectory": "demo-live-trajectory.json"
            }
        }
        store = make_store(
            tmp_path,
            artifacts={
                "demo-live-telemetry.json": telemetry,
                "demo-live-trajectory.json": trajectory,
                "demo-live-manifest.json": manifest
            }
        )
        dash = store.dashboard()
        assert dash["bundle_consistent"] is False
        assert dash["label"] == "UNVERIFIED (INCONSISTENT BUNDLE)"

class TestApiEndpoints:
    def test_dashboard_endpoint_provenance(self, tmp_path):
        client = client_for(
            make_store(tmp_path, sample={"telemetry-truth.json": VALID_TELEMETRY})
        )
        body = client.get("/api/dashboard").json()
        assert body["label"] == "SAMPLE"
        assert body["provenance"]["telemetry"]["origin"] == "sample"
        assert body["provenance"]["trajectory"]["available"] is False

    def test_raw_endpoints_wrap_with_provenance(self, tmp_path):
        client = client_for(
            make_store(tmp_path, sample={"telemetry-truth.json": VALID_TELEMETRY})
        )
        body = client.get("/api/telemetry").json()
        assert body["available"] is True
        assert body["provenance"]["origin"] == "sample"
        missing = client.get("/api/runtime-probe").json()
        assert missing["available"] is False and missing["data"] is None

    def test_health(self, tmp_path):
        client = client_for(make_store(tmp_path))
        body = client.get("/api/health").json()
        assert body["status"] == "ok"
        assert body["live_runs_enabled"] in (True, False)

    def test_cors_allows_vite_dev_origin_without_credentials(self, tmp_path):
        client = client_for(make_store(tmp_path))
        resp = client.options(
            "/api/dashboard",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert resp.headers["access-control-allow-origin"] == "http://localhost:5173"
        assert "access-control-allow-credentials" not in resp.headers

    def test_cors_rejects_foreign_origin(self, tmp_path):
        client = client_for(make_store(tmp_path))
        resp = client.options(
            "/api/dashboard",
            headers={
                "Origin": "https://evil.example",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert "access-control-allow-origin" not in resp.headers

    def test_no_env_or_secret_leakage_in_dashboard(self, tmp_path, monkeypatch):
        monkeypatch.setenv("FIREWORKS_API_KEY", "sk-super-secret")
        client = client_for(
            make_store(tmp_path, sample={"telemetry-truth.json": VALID_TELEMETRY})
        )
        assert "sk-super-secret" not in client.get("/api/dashboard").text


RUN_BODY = {
    "task_input": "Core router CR-04 dropped all BGP sessions; region south offline.",
    "contract_id": "telecom.severity_classification",
    "local_provider": "mock",
    "remote_provider": "mock",
}


class TestLiveRuns:
    @pytest.fixture()
    def live_client(self, tmp_path, monkeypatch):
        monkeypatch.setenv("KAAVAL_LIVE_RUNS_ENABLED", "1")
        return client_for(make_store(tmp_path))

    def test_disabled_by_default(self, tmp_path, monkeypatch):
        monkeypatch.delenv("KAAVAL_LIVE_RUNS_ENABLED", raising=False)
        client = client_for(make_store(tmp_path))
        resp = client.post("/api/runs", json=RUN_BODY)
        assert resp.status_code == 403
        assert "disabled" in resp.json()["detail"]

    def test_live_mock_happy_path(self, live_client):
        resp = live_client.post("/api/runs", json=RUN_BODY)
        assert resp.status_code == 200
        body = resp.json()
        assert body["label"] == "LIVE RUN"
        assert body["result"]["verified"] is True
        assert body["result"]["escalated"] is False
        assert len(body["trajectory"]) == 1
        assert body["trajectory"][0]["provider"] == "mock"

    def test_local_failure_escalates_to_remote_rescue(self, live_client):
        resp = live_client.post(
            "/api/runs", json={**RUN_BODY, "failure_mode": "bad_enum"}
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["result"]["escalated"] is True
        assert body["result"]["verified"] is True
        rows = body["trajectory"]
        assert len(rows) == 2
        assert rows[0]["verifier_passed"] is False
        assert "enum:severity" in rows[0]["verifier_failures"]
        assert rows[1]["tier"] == "remote" and rows[1]["escalated"] is True

    def test_fireworks_rejected_without_confirmation(self, live_client, monkeypatch):
        monkeypatch.setenv("FIREWORKS_API_KEY", "k")
        resp = live_client.post(
            "/api/runs", json={**RUN_BODY, "remote_provider": "fireworks"}
        )
        assert resp.status_code == 403
        assert "confirm" in resp.json()["detail"].lower()

    def test_failure_injection_rejected_for_non_mock_local(self, live_client):
        resp = live_client.post(
            "/api/runs",
            json={**RUN_BODY, "local_provider": "ollama", "failure_mode": "bad_enum"},
        )
        assert resp.status_code == 422
        assert "mock" in resp.json()["detail"]

    def test_unknown_contract_rejected(self, live_client):
        resp = live_client.post(
            "/api/runs", json={**RUN_BODY, "contract_id": "telecom.nope"}
        )
        assert resp.status_code == 422

    def test_run_and_telemetry_share_request_id(self, live_client):
        body = live_client.post("/api/runs", json=RUN_BODY).json()
        run_id = body["run_id"]
        assert all(r["request_id"] == run_id for r in body["trajectory"])
        assert all(
            a["request_id"] == run_id
            for a in body["telemetry"]["attempts_detail"]
        )

    def test_no_credentials_in_live_response(self, live_client, monkeypatch):
        monkeypatch.setenv("FIREWORKS_API_KEY", "sk-super-secret")
        text = live_client.post("/api/runs", json=RUN_BODY).text
        assert "sk-super-secret" not in text
        assert "api_key" not in text.lower()

    def test_live_response_never_mislabeled_captured(self, live_client):
        body = live_client.post("/api/runs", json=RUN_BODY).json()
        assert body["mode"] == "live"
        assert body["label"] == "LIVE RUN"
        assert "SAMPLE" not in json.dumps(body)
