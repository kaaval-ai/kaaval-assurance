"""Provider factory, Ollama provider, and attempt telemetry tests.

No network anywhere: Ollama/Fireworks HTTP is faked or never invoked.
"""

import json

import pytest

from kaaval_assurance.compare import (
    default_comparison_providers,
    export_model_comparison,
    run_model_comparison,
)
from kaaval_assurance.contracts import get_contract
from kaaval_assurance.demo import run_live_demo
from kaaval_assurance.eval import load_dataset
from kaaval_assurance.eval.cli import main as cli_main
from kaaval_assurance.eval.runner import run_eval
from kaaval_assurance.pipeline import AssurancePipeline
from kaaval_assurance.providers import (
    MockProvider,
    OllamaError,
    OllamaProvider,
    SpendConfirmationRequired,
    create_local_provider,
    create_remote_provider,
    ollama_config_from_env,
)
from kaaval_assurance.providers.vllm import base_url_host
from kaaval_assurance.router import Router
from kaaval_assurance.telemetry import build_telemetry_summary
from kaaval_assurance.trajectory import TrajectoryStore

GOLD = "data/eval/telecom_gold.jsonl"
SEVERITY = get_contract("telecom.severity_classification")
VALID_JSON = json.dumps(
    {"severity": "P1", "confidence": 0.9, "rationale": "regional outage"}
)

OLLAMA_ENV = {
    "OLLAMA_MODEL": "gemma-test:12b",
    "OLLAMA_MODEL_FAMILY": "gemma",
}


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self.status_code = status_code
        self._payload = payload
        self.text = json.dumps(payload)

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, content=VALID_JSON):
        self.content = content
        self.calls = []

    def post(self, url, json=None, headers=None, timeout=None):
        self.calls.append({"url": url, "json": json, "headers": headers})
        return FakeResponse(
            {
                "choices": [{"message": {"content": self.content}}],
                "usage": {"prompt_tokens": 50, "completion_tokens": 20},
            }
        )


class TestFactory:
    def test_creates_mock_local(self):
        provider = create_local_provider("mock", failure_mode="bad_enum")
        assert isinstance(provider, MockProvider)
        assert provider.tier == "local"

    def test_creates_ollama_from_env_without_network(self):
        provider = create_local_provider("ollama", env=OLLAMA_ENV)
        assert isinstance(provider, OllamaProvider)
        assert provider.provider_name == "ollama"
        assert provider.model_id == "gemma-test:12b"
        assert provider.config.base_url == "http://127.0.0.1:11434/v1"
        assert provider.config.timeout_seconds == 120.0

    def test_ollama_requires_model(self):
        with pytest.raises(ValueError, match="OLLAMA_MODEL"):
            create_local_provider("ollama", env={})

    def test_failure_injection_rejected_for_real_providers(self):
        with pytest.raises(ValueError, match="mock local provider only"):
            create_local_provider("ollama", env=OLLAMA_ENV, failure_mode="bad_enum")

    def test_unknown_names_rejected(self):
        with pytest.raises(ValueError, match="unknown local provider"):
            create_local_provider("gpt4")
        with pytest.raises(ValueError, match="unknown remote provider"):
            create_remote_provider("openai")

    def test_fireworks_requires_spend_confirmation(self):
        with pytest.raises(SpendConfirmationRequired):
            create_remote_provider("fireworks", env={"FIREWORKS_API_KEY": "k"})

    def test_fireworks_with_confirmation_builds_without_network(self):
        provider = create_remote_provider(
            "fireworks", env={"FIREWORKS_API_KEY": "k"}, confirm_spend=True
        )
        assert provider.provider_name == "fireworks"
        assert provider.tier == "remote"


class TestOllamaTelemetryLabels:
    def test_response_and_profile_labeled_ollama(self):
        session = FakeSession()
        provider = OllamaProvider(
            ollama_config_from_env(OLLAMA_ENV), session=session
        )
        response = provider.generate("r1", "incident text", SEVERITY)
        assert response.provider == "ollama"
        assert response.tier == "local"
        assert response.parsed is not None

        profile = provider.runtime_profile()
        assert profile.provider == "ollama"
        assert profile.endpoint_type == "openai_compatible"
        assert profile.base_url_host == "127.0.0.1:11434"
        assert profile.hardware_target == "local-mac-ollama"
        assert profile.model_family == "gemma"
        # vLLM engine knobs are not inherited as false claims
        assert profile.dtype == "" and profile.kv_cache_dtype == ""

    def test_transport_failure_uses_ollama_error_identity(self):
        class MissingModelSession:
            def post(self, url, json=None, headers=None, timeout=None):
                return FakeResponse(
                    {"error": {"message": "model not found"}}, status_code=404
                )

        provider = OllamaProvider(
            ollama_config_from_env(OLLAMA_ENV), session=MissingModelSession()
        )

        with pytest.raises(OllamaError, match="ollama HTTP 404"):
            provider.generate("r-missing", "incident text", SEVERITY)

    def test_base_url_host_never_leaks_path_or_scheme(self):
        assert base_url_host("http://user:pass@pod:8000/v1") == "pod:8000"
        assert base_url_host("https://api.example.test/v1") == "api.example.test"

    def test_error_messages_say_ollama(self):
        import requests

        from kaaval_assurance.providers.vllm import VllmError

        class ExplodingSession:
            def post(self, *a, **k):
                raise requests.ConnectionError("refused")

        provider = OllamaProvider(
            ollama_config_from_env(OLLAMA_ENV), session=ExplodingSession()
        )
        with pytest.raises(VllmError, match="ollama request failed"):
            provider.generate("r1", "x", SEVERITY)


class TestCli:
    def test_cli_accepts_ollama_and_fails_cleanly_unconfigured(
        self, monkeypatch, capsys
    ):
        monkeypatch.delenv("OLLAMA_MODEL", raising=False)
        rc = cli_main(["--dataset", GOLD, "--local-provider", "ollama"])
        assert rc == 2
        assert "OLLAMA_MODEL" in capsys.readouterr().err

    def test_cli_rejects_failure_mode_with_ollama(self, capsys):
        rc = cli_main(
            ["--dataset", GOLD, "--local-provider", "ollama",
             "--failure-mode", "bad_enum"]
        )
        assert rc == 2
        assert "mock local" in capsys.readouterr().err

    def test_cli_requires_spend_confirmation_for_fireworks(self, monkeypatch, capsys):
        monkeypatch.setenv("FIREWORKS_API_KEY", "test-key")
        rc = cli_main(["--dataset", GOLD, "--remote-provider", "fireworks"])
        assert rc == 2
        assert "spends credits" in capsys.readouterr().err


class TestLiveDemoWithProviders:
    def test_live_demo_with_injected_ollama_provider(self):
        provider = OllamaProvider(
            ollama_config_from_env(OLLAMA_ENV), session=FakeSession()
        )
        demo = run_live_demo(
            "CR-04 BGP flap",
            "telecom.severity_classification",
            local_provider=provider,
        )
        assert demo.result.verification.passed
        assert demo.rows[0].provider == "ollama"
        assert demo.rows[0].model_id == "gemma-test:12b"

    def test_live_demo_rejects_failure_mode_with_custom_provider(self):
        provider = OllamaProvider(
            ollama_config_from_env(OLLAMA_ENV), session=FakeSession()
        )
        with pytest.raises(ValueError, match="mock local tier only"):
            run_live_demo(
                "x", "telecom.severity_classification",
                failure_mode="bad_enum", local_provider=provider,
            )


class TestAttemptTelemetry:
    def test_attempt_fields_present_and_measured_from_rows(self):
        store = TrajectoryStore(":memory:")
        try:
            pipeline = AssurancePipeline(
                Router(),
                MockProvider(tier="local", failure_mode="bad_enum"),
                MockProvider(tier="remote", model_id="mock-remote-strong"),
                store,
            )
            report = run_eval(pipeline, load_dataset(GOLD))
            rows = []
            for r in report.results:
                rows.extend(store.rows_for_request(r.request_id))
            telemetry = build_telemetry_summary(report, rows)
        finally:
            store.close()

        assert len(telemetry.attempts_detail) == len(rows) == 24
        local_fail = next(
            a for a in telemetry.attempts_detail
            if a.tier == "local" and not a.verifier_passed
        )
        assert local_fail.provider == "mock"
        assert local_fail.contract_id and local_fail.category
        assert local_fail.total_tokens == (
            local_fail.prompt_tokens + local_fail.completion_tokens
        )
        # sev-001 is the first local failure in dataset order and also trips
        # the regional-outage grounding rule alongside its enum failure.
        assert local_fail.verifier_failure_count == 2
        assert local_fail.verifier_failure_types == ["enum", "grounding"]
        assert local_fail.escalation_reason is None

        escalated = next(a for a in telemetry.attempts_detail if a.escalated)
        assert escalated.tier == "remote"
        assert "layer-1 verification failed" in escalated.escalation_reason
        assert escalated.latency_ms > 0

    def test_ollama_runtime_claim_names_ollama_not_vllm(self):
        provider = OllamaProvider(
            ollama_config_from_env(OLLAMA_ENV), session=FakeSession()
        )
        store = TrajectoryStore(":memory:")
        try:
            pipeline = AssurancePipeline(
                Router(),
                provider,
                MockProvider(tier="remote", model_id="mock-remote-strong"),
                store,
            )
            report = run_eval(pipeline, load_dataset(GOLD)[:1])
            rows = []
            for r in report.results:
                rows.extend(store.rows_for_request(r.request_id))
            telemetry = build_telemetry_summary(
                report, rows, runtime_profile=provider.runtime_profile()
            )
        finally:
            store.close()

        runtime_claim = next(c for c in telemetry.claims if c.claim == "Runtime")
        assert "via Ollama" in runtime_claim.value
        assert "via vLLM" not in runtime_claim.value


class TestComparisonHelper:
    def providers(self):
        return {
            "mock-baseline": MockProvider(tier="local"),
            "ollama-gemma": OllamaProvider(
                ollama_config_from_env(OLLAMA_ENV), session=FakeSession()
            ),
            "ollama-qwen": OllamaProvider(
                ollama_config_from_env(
                    {**OLLAMA_ENV, "OLLAMA_MODEL": "qwen-test:7b",
                     "OLLAMA_MODEL_FAMILY": "qwen"}
                ),
                session=FakeSession(content="I think severity is high."),
            ),
        }

    def test_comparison_runs_all_candidates(self):
        report = run_model_comparison(
            "CR-04 BGP flap, region south down",
            "telecom.severity_classification",
            self.providers(),
            case_id="sev-001",
        )
        by_label = {e.label: e for e in report.entries}
        assert by_label["mock-baseline"].verifier_passed is True
        assert by_label["ollama-gemma"].verifier_passed is True
        assert by_label["ollama-qwen"].verifier_passed is False
        assert by_label["ollama-qwen"].verifier_failures == ["json_parse"]

    def test_dead_endpoint_recorded_not_raised(self):
        import requests

        class ExplodingSession:
            def post(self, *a, **k):
                raise requests.ConnectionError("refused")

        providers = {
            "mock-baseline": MockProvider(tier="local"),
            "ollama-gemma": OllamaProvider(
                ollama_config_from_env(OLLAMA_ENV), session=ExplodingSession()
            ),
        }
        report = run_model_comparison(
            "x", "telecom.severity_classification", providers
        )
        dead = next(e for e in report.entries if e.label == "ollama-gemma")
        assert dead.error is not None
        assert dead.verifier_passed is None

    def test_default_providers_respect_configuration(self):
        assert set(default_comparison_providers({})) == {"mock-baseline"}
        with_gemma = default_comparison_providers(OLLAMA_ENV)
        assert "ollama-gemma" in with_gemma
        with_both = default_comparison_providers(
            {**OLLAMA_ENV, "OLLAMA_QWEN_MODEL": "qwen-test:7b"}
        )
        assert set(with_both) == {"mock-baseline", "ollama-gemma", "ollama-qwen"}
        assert with_both["ollama-qwen"].config.model_family == "qwen"

    def test_export_artifacts_no_secrets(self, tmp_path):
        report = run_model_comparison(
            "CR-04 BGP flap", "telecom.severity_classification", self.providers()
        )
        paths = export_model_comparison(report, tmp_path)
        assert {p.name for p in paths} == {
            "model-comparison.json", "model-comparison.md",
        }
        payload = json.loads((tmp_path / "model-comparison.json").read_text())
        assert len(payload["entries"]) == 3
        md = (tmp_path / "model-comparison.md").read_text()
        assert "Gemma is the preferred model family" in md
        assert "proof target" in md
        for path in paths:
            content = path.read_text()
            for marker in ("api_key", "API_KEY", "Bearer ", "sk-", "fw-"):
                assert marker not in content, f"{marker!r} in {path.name}"
