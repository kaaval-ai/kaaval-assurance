"""Runtime probe tests. All HTTP and host commands faked — no network."""

import json
import subprocess

import pytest
import requests

from kaaval_assurance.runtime_probe import (
    HOST_COMMANDS,
    PACKAGES_TO_CHECK,
    build_probe_report,
    check_packages,
    main,
    probe_command,
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


def fake_runner_missing(cmd):
    raise FileNotFoundError(cmd[0])


def make_fake_runner(stdout="ok", returncode=0):
    def runner(cmd):
        return subprocess.CompletedProcess(
            cmd, returncode=returncode, stdout=stdout, stderr=""
        )

    return runner


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


class TestEndpointProbe:
    def test_reachable_with_served_model(self):
        session = FakeSession(models=["google/gemma-3-12b-it"], version="0.9.1")
        result = probe_runtime(env=BASE_ENV, session=session)
        assert result.reachable is True
        assert result.served_models == ["google/gemma-3-12b-it"]
        assert result.configured_model_served is True
        assert result.family_consistent is True
        assert result.vllm_version == "0.9.1"
        assert result.source == "measured"
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

    def test_auth_header_only_when_key_set(self):
        session = FakeSession(models=["m"])
        probe_runtime(env=BASE_ENV, session=session)
        assert session.calls[0]["headers"] == {}
        session2 = FakeSession(models=["m"])
        probe_runtime(env=dict(BASE_ENV, VLLM_API_KEY="k"), session=session2)
        assert session2.calls[0]["headers"] == {"Authorization": "Bearer k"}


class TestHostProbes:
    def test_missing_command_is_not_available_not_an_exception(self):
        probe = probe_command(["rocm-smi", "--showproductname"], runner=fake_runner_missing)
        assert probe.available is False
        assert probe.source == "not_available"
        assert probe.error == "command not found"

    def test_successful_command_is_measured(self):
        probe = probe_command(
            ["vllm", "--version"], runner=make_fake_runner(stdout="0.9.1\n")
        )
        assert probe.available is True
        assert probe.source == "measured"
        assert probe.output == "0.9.1"

    def test_nonzero_exit_is_not_available(self):
        probe = probe_command(
            ["rocm-smi", "--showmeminfo", "vram"],
            runner=make_fake_runner(stdout="", returncode=3),
        )
        assert probe.available is False
        assert probe.source == "not_available"
        assert probe.error == "exit 3"

    def test_package_checks_cover_required_names(self):
        checks = {c.name: c for c in check_packages()}
        assert set(checks) == set(PACKAGES_TO_CHECK)
        # this test suite runs on requests + pydantic, so both must be found
        assert checks["requests"].importable is True
        assert checks["pydantic"].importable is True
        for check in checks.values():
            assert check.source == "measured"


class TestReport:
    def build(self, cwd="/Users/dev/repo", **kwargs):
        defaults = dict(
            env=BASE_ENV,
            session=FakeSession(models=["google/gemma-3-12b-it"]),
            runner=fake_runner_missing,  # host without rocm-smi/vllm CLI
            cwd=cwd,
        )
        defaults.update(kwargs)
        return build_probe_report(**defaults)

    def test_report_survives_host_without_any_tools(self):
        report = self.build()
        assert set(report.commands) == set(HOST_COMMANDS)
        for probe in report.commands.values():
            assert probe.available is False
            assert probe.source == "not_available"
        assert report.endpoint.reachable is True

    def test_workspace_detection(self):
        assert self.build(cwd="/workspace/kaaval-assurance").system.under_workspace
        assert self.build(cwd="/workspace").system.under_workspace
        assert not self.build(cwd="/workspaces/other").system.under_workspace

    def test_env_groups_redacted_and_tagged(self):
        env = dict(BASE_ENV, FIREWORKS_API_KEY="sk-secret", FIREWORKS_MODEL="m")
        report = self.build(env=env)
        assert report.env_source == "configured"
        assert report.env_fireworks["FIREWORKS_API_KEY"] == "***redacted***"
        assert report.env_fireworks["FIREWORKS_MODEL"] == "m"
        assert report.env_vllm["VLLM_MODEL"] == "google/gemma-3-12b-it"

    def test_skip_endpoint(self):
        report = self.build(include_endpoint=False, session=None)
        assert report.endpoint is None


class TestMain:
    def test_json_by_default_with_source_tags(self, capsys):
        session = FakeSession(models=["google/gemma-3-12b-it"])
        rc = main([], env=BASE_ENV, session=session, runner=fake_runner_missing)
        assert rc == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["system"]["source"] == "measured"
        assert payload["env_source"] == "configured"
        assert payload["commands"]["vllm_version"]["source"] == "not_available"
        assert payload["endpoint"]["source"] == "measured"

    def test_never_fails_when_endpoint_down(self, capsys):
        session = FakeSession(exc=requests.ConnectionError("refused"))
        rc = main([], env=BASE_ENV, session=session, runner=fake_runner_missing)
        assert rc == 0  # probing is data collection, not a gate by default

    def test_require_endpoint_gates_exit_code(self):
        down = FakeSession(exc=requests.ConnectionError("refused"))
        assert main(
            ["--require-endpoint"], env=BASE_ENV, session=down,
            runner=fake_runner_missing,
        ) == 1
        up = FakeSession(models=["google/gemma-3-12b-it"])
        assert main(
            ["--require-endpoint"], env=BASE_ENV, session=up,
            runner=fake_runner_missing,
        ) == 0

    def test_text_mode_redacts_and_states_policy(self, capsys):
        env = dict(BASE_ENV, FIREWORKS_API_KEY="sk-secret")
        session = FakeSession(models=["google/gemma-3-12b-it"], version="0.9.1")
        rc = main(["--text"], env=env, session=session, runner=fake_runner_missing)
        assert rc == 0
        out = capsys.readouterr().out
        assert "Gemma-first local tier" in out
        assert "***redacted***" in out
        assert "sk-secret" not in out
        assert "[not_available]" in out  # missing host tools shown honestly

    def test_output_file_written(self, tmp_path, capsys):
        out_file = tmp_path / "probe.json"
        session = FakeSession(models=["google/gemma-3-12b-it"])
        rc = main(
            ["--output", str(out_file)], env=BASE_ENV, session=session,
            runner=fake_runner_missing,
        )
        assert rc == 0
        on_disk = json.loads(out_file.read_text())
        assert on_disk["endpoint"]["served_models"] == ["google/gemma-3-12b-it"]

    def test_fallback_note_printed_on_family_mismatch(self, capsys):
        env = dict(BASE_ENV, VLLM_MODEL="Qwen/Qwen2-7B-Instruct")
        session = FakeSession(models=["Qwen/Qwen2-7B-Instruct"])
        main(["--text"], env=env, session=session, runner=fake_runner_missing)
        out = capsys.readouterr().out
        assert "truthfully" in out
        assert "VLLM_MODEL_FAMILY" in out


class TestEnvExample:
    def test_no_real_secrets_in_env_example(self):
        lines = [
            line.strip()
            for line in open(".env.example", encoding="utf-8")
            if line.strip() and not line.strip().startswith("#")
        ]
        for line in lines:
            key, _, value = line.partition("=")
            if {"KEY", "SECRET", "PASSWORD"} & set(key.upper().split("_")):
                assert value == "", f"{key} must be empty in .env.example"

    def test_required_keys_present(self):
        content = open(".env.example", encoding="utf-8").read()
        for key in [
            "FIREWORKS_API_KEY=", "FIREWORKS_MODEL=", "FIREWORKS_AUDIT_MODEL=",
            "VLLM_BASE_URL=http://localhost:8000/v1", "VLLM_MODEL=",
            "VLLM_HARDWARE_TARGET=amd-hackathon-gpu", "VLLM_ROCM_VERSION=",
            "VLLM_VERSION=", "VLLM_DTYPE=bfloat16", "VLLM_KV_CACHE_DTYPE=auto",
            "VLLM_ENABLE_PREFIX_CACHING=true",
            "VLLM_GPU_MEMORY_UTILIZATION=0.30",
            "VLLM_TENSOR_PARALLEL_SIZE=1", "VLLM_STRUCTURED_OUTPUTS=true",
        ]:
            assert key in content, key
