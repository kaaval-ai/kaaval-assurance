"""Runtime probe tests. All HTTP faked — no network, no live vLLM."""

import json

import pytest
import requests

from kaaval_assurance.runtime_probe import (
    RuntimeProbeResult,
    main,
    probe_runtime,
    redact_env,
)


class FakeResponse:
    def __init__(self, status_code=200, payload=None, text=None):
        self.status_code = status_code
        self._payload = payload if payload is not None else {}
        self.text = text if text is not None else json.dumps(self._payload)

    def json(self):
        return self._payload


class FakeSession:
    """Routes GETs by URL suffix; raises exc when configured."""

    def __init__(self, models=None, version=None, exc=None, models_status=200):
        self.models = models if models is not None else []
        self.version = version
        self.exc = exc
        self.models_status = models_status
        self.calls = []

    def get(self, url, headers=None, timeout=None):
        self.calls.append({"url": url, "headers": headers, "timeout": timeout})
        if self.exc is not None:
            raise self.exc
        if url.endswith("/version"):
            if self.version is None:
                raise requests.ConnectionError("no version endpoint")
            return FakeResponse(payload={"version": self.version})
        return FakeResponse(
            status_code=self.models_status,
            payload={"data": [{"id": m} for m in self.models]},
        )


BASE_ENV = {
    "VLLM_BASE_URL": "http://pod:8000/v1",
    "VLLM_MODEL": "google/gemma-3-12b-it",
    "VLLM_MODEL_FAMILY": "gemma",
}


class TestRedaction:
    def test_secrets_redacted_non_secrets_kept(self):
        env = {
            "FIREWORKS_API_KEY": "sk-secret",
            "VLLM_API_KEY": "vk-secret",
            "VLLM_MODEL": "google/gemma-3-12b-it",
            "KAAVAL_CONFIRM_SPEND": "0",
            "HOME": "/Users/nobody",  # non-prefixed: excluded entirely
        }
        redacted = redact_env(env)
        assert redacted["FIREWORKS_API_KEY"] == "***redacted***"
        assert redacted["VLLM_API_KEY"] == "***redacted***"
        assert redacted["VLLM_MODEL"] == "google/gemma-3-12b-it"
        assert redacted["KAAVAL_CONFIRM_SPEND"] == "0"
        assert "HOME" not in redacted
        assert "sk-secret" not in json.dumps(redacted)

    def test_empty_secret_not_masked(self):
        assert redact_env({"VLLM_API_KEY": ""})["VLLM_API_KEY"] == ""


class TestProbe:
    def test_reachable_with_served_model(self):
        session = FakeSession(models=["google/gemma-3-12b-it"], version="0.9.1")
        result = probe_runtime(env=BASE_ENV, session=session)
        assert result.reachable is True
        assert result.served_models == ["google/gemma-3-12b-it"]
        assert result.configured_model_served is True
        assert result.family_consistent is True
        assert result.vllm_version == "0.9.1"
        assert result.latency_ms is not None
        assert result.source == "measured"
        # /version probed at server root, outside /v1
        version_call = [c for c in session.calls if c["url"].endswith("/version")]
        assert version_call[0]["url"] == "http://pod:8000/version"

    def test_configured_model_not_served(self):
        session = FakeSession(models=["Qwen/Qwen2-7B-Instruct"])
        result = probe_runtime(env=BASE_ENV, session=session)
        assert result.reachable is True
        assert result.configured_model_served is False

    def test_family_mismatch_flagged_for_fallback(self):
        env = dict(BASE_ENV, VLLM_MODEL="Qwen/Qwen2-7B-Instruct")
        session = FakeSession(models=["Qwen/Qwen2-7B-Instruct"])
        result = probe_runtime(env=env, session=session)
        assert result.family_consistent is False  # fallback must relabel family

    def test_unreachable_endpoint(self):
        session = FakeSession(exc=requests.ConnectionError("refused"))
        result = probe_runtime(env=BASE_ENV, session=session)
        assert result.reachable is False
        assert "ConnectionError" in result.error
        assert result.served_models == []

    def test_http_error_reported(self):
        session = FakeSession(models_status=503)
        result = probe_runtime(env=BASE_ENV, session=session)
        assert result.reachable is False
        assert "HTTP 503" in result.error

    def test_missing_version_endpoint_tolerated(self):
        session = FakeSession(models=["google/gemma-3-12b-it"], version=None)
        result = probe_runtime(env=BASE_ENV, session=session)
        assert result.reachable is True
        assert result.vllm_version is None

    def test_no_model_configured(self):
        env = {"VLLM_BASE_URL": "http://pod:8000/v1"}
        session = FakeSession(models=["google/gemma-3-12b-it"])
        result = probe_runtime(env=env, session=session)
        assert result.configured_model is None
        assert result.configured_model_served is None
        assert result.family_consistent is None

    def test_auth_header_only_when_key_set(self):
        session = FakeSession(models=["m"])
        probe_runtime(env=BASE_ENV, session=session)
        assert session.calls[0]["headers"] == {}
        session2 = FakeSession(models=["m"])
        probe_runtime(env=dict(BASE_ENV, VLLM_API_KEY="k"), session=session2)
        assert session2.calls[0]["headers"] == {"Authorization": "Bearer k"}


class TestMain:
    def test_reachable_exit_0_and_redacted_output(self, capsys):
        env = dict(BASE_ENV, FIREWORKS_API_KEY="sk-secret")
        session = FakeSession(models=["google/gemma-3-12b-it"], version="0.9.1")
        rc = main([], env=env, session=session)
        assert rc == 0
        out = capsys.readouterr().out
        assert "reachable: yes" in out
        assert "Gemma-first local tier" in out
        assert "***redacted***" in out
        assert "sk-secret" not in out

    def test_unreachable_exit_1(self, capsys):
        session = FakeSession(exc=requests.ConnectionError("refused"))
        rc = main([], env=BASE_ENV, session=session)
        assert rc == 1
        assert "reachable: no" in capsys.readouterr().out

    def test_json_and_output_file(self, tmp_path, capsys):
        out_file = tmp_path / "probe.json"
        session = FakeSession(models=["google/gemma-3-12b-it"])
        rc = main(
            ["--json", "--output", str(out_file)], env=BASE_ENV, session=session
        )
        assert rc == 0
        printed = json.loads(capsys.readouterr().out)
        assert printed["reachable"] is True
        on_disk = json.loads(out_file.read_text())
        assert on_disk["served_models"] == ["google/gemma-3-12b-it"]
        assert on_disk["source"] == "measured"

    def test_fallback_note_printed_on_family_mismatch(self, capsys):
        env = dict(BASE_ENV, VLLM_MODEL="Qwen/Qwen2-7B-Instruct")
        session = FakeSession(models=["Qwen/Qwen2-7B-Instruct"])
        main([], env=env, session=session)
        out = capsys.readouterr().out
        assert "recorded" in out and "truthfully" in out
        assert "VLLM_MODEL_FAMILY" in out
