"""VllmProvider tests. All HTTP faked — no vLLM server, no network."""

import json

import pytest
import requests

from kaaval_assurance.contracts import get_contract
from kaaval_assurance.pipeline import AssurancePipeline
from kaaval_assurance.providers import MockProvider
from kaaval_assurance.providers.fireworks import FireworksConfig, FireworksProvider
from kaaval_assurance.providers.vllm import (
    DEFAULT_BASE_URL,
    VllmConfig,
    VllmError,
    VllmProvider,
)
from kaaval_assurance.router import Router
from kaaval_assurance.trajectory import TrajectoryStore
from kaaval_assurance.verifier import verify

SEVERITY = get_contract("telecom.severity_classification")

VALID_SEVERITY_JSON = json.dumps(
    {"severity": "P2", "confidence": 0.8, "rationale": "redundancy lost"}
)


class FakeResponse:
    def __init__(self, status_code=200, payload=None, text=None):
        self.status_code = status_code
        self._payload = payload if payload is not None else {}
        self.text = text if text is not None else json.dumps(self._payload)

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, response=None, exc=None):
        self.response = response
        self.exc = exc
        self.calls = []

    def post(self, url, json=None, headers=None, timeout=None):
        self.calls.append(
            {"url": url, "json": json, "headers": headers, "timeout": timeout}
        )
        if self.exc is not None:
            raise self.exc
        return self.response


def chat_payload(content, usage=None):
    payload = {"choices": [{"message": {"content": content}}]}
    if usage is not None:
        payload["usage"] = usage
    return payload


def make_config(**overrides):
    defaults = dict(model="gemma-3-12b-it")
    defaults.update(overrides)
    return VllmConfig(**defaults)


class TestConfig:
    def test_from_env_reads_all_vars(self):
        env = {
            "VLLM_MODEL": "gemma-3-12b-it",
            "VLLM_BASE_URL": "http://10.0.0.5:8000/v1/",
            "VLLM_TIMEOUT_SECONDS": "30",
            "VLLM_API_KEY": "local-token",
            "VLLM_DTYPE": "float16",
            "VLLM_KV_CACHE_DTYPE": "auto",
            "VLLM_ENABLE_PREFIX_CACHING": "false",
            "VLLM_GPU_MEMORY_UTILIZATION": "0.85",
            "VLLM_TENSOR_PARALLEL_SIZE": "2",
            "VLLM_STRUCTURED_OUTPUTS": "false",
            "VLLM_MAX_CONTEXT_TOKENS": "8192",
            "VLLM_ROCM_VERSION": "6.3",
            "VLLM_VERSION": "0.8.4",
            "VLLM_COST_PER_PROMPT_TOKEN": "0.000001",
        }
        cfg = VllmConfig.from_env(env)
        assert cfg.model == "gemma-3-12b-it"
        assert cfg.base_url == "http://10.0.0.5:8000/v1"  # slash stripped
        assert cfg.timeout_seconds == 30.0
        assert cfg.api_key == "local-token"
        assert cfg.dtype == "float16"
        assert cfg.kv_cache_dtype == "auto"
        assert cfg.enable_prefix_caching is False
        assert cfg.gpu_memory_utilization == pytest.approx(0.85)
        assert cfg.tensor_parallel_size == 2
        assert cfg.structured_outputs is False
        assert cfg.max_context_tokens == 8192
        assert cfg.rocm_version == "6.3"
        assert cfg.vllm_version == "0.8.4"
        assert cfg.cost_per_prompt_token == pytest.approx(1e-6)

    def test_from_env_defaults(self):
        cfg = VllmConfig.from_env({"VLLM_MODEL": "gemma-3-12b-it"})
        assert cfg.base_url == DEFAULT_BASE_URL
        assert cfg.timeout_seconds == 60.0
        assert cfg.api_key == ""
        assert cfg.dtype == "bfloat16"
        assert cfg.kv_cache_dtype == "fp8"
        assert cfg.enable_prefix_caching is True
        assert cfg.gpu_memory_utilization == pytest.approx(0.92)
        assert cfg.tensor_parallel_size == 1
        assert cfg.structured_outputs is True
        assert cfg.max_context_tokens is None
        assert cfg.hardware_target == "amd-hackathon-gpu"

    def test_missing_model_raises(self):
        with pytest.raises(ValueError, match="VLLM_MODEL"):
            VllmConfig.from_env({})


class TestRuntimeProfile:
    def test_profile_records_configured_settings(self):
        provider = VllmProvider(
            make_config(rocm_version="6.3", vllm_version="0.8.4",
                        max_context_tokens=8192)
        )
        p = provider.runtime_profile()
        assert p.provider == "vllm-gemma"
        assert p.model_id == "gemma-3-12b-it"
        assert p.served_model_name == "gemma-3-12b-it"
        assert p.hardware_target == "amd-hackathon-gpu"
        assert p.rocm_version == "6.3"
        assert p.vllm_version == "0.8.4"
        assert p.dtype == "bfloat16"
        assert p.kv_cache_dtype == "fp8"
        assert p.tensor_parallel_size == 1
        assert p.gpu_memory_utilization == pytest.approx(0.92)
        assert p.prefix_caching_enabled is True
        assert p.max_context_tokens == 8192
        assert p.structured_output_mode == "json_object"

    def test_profile_structured_mode_none_when_disabled(self):
        provider = VllmProvider(make_config(structured_outputs=False))
        assert provider.runtime_profile().structured_output_mode == "none"

    def test_other_providers_have_no_profile(self):
        assert MockProvider().runtime_profile() is None
        fw = FireworksProvider(
            FireworksConfig(api_key="k"), session=FakeSession(FakeResponse())
        )
        assert fw.runtime_profile() is None


class TestGenerate:
    def test_valid_json_response(self):
        session = FakeSession(
            FakeResponse(
                payload=chat_payload(
                    VALID_SEVERITY_JSON,
                    usage={"prompt_tokens": 120, "completion_tokens": 35},
                )
            )
        )
        provider = VllmProvider(
            make_config(cost_per_prompt_token=1e-7, cost_per_completion_token=3e-7),
            session=session,
        )
        r = provider.generate("req-1", "incident text", SEVERITY)

        assert r.provider == "vllm-gemma"
        assert r.tier == "local"
        assert r.model_id == "gemma-3-12b-it"
        assert r.parsed["severity"] == "P2"
        assert r.prompt_tokens == 120
        assert r.completion_tokens == 35
        assert r.cost_usd == pytest.approx(120e-7 + 105e-7)
        assert r.latency_ms >= 0.0
        assert verify(r, SEVERITY).passed

    def test_request_shape_no_auth_by_default(self):
        session = FakeSession(FakeResponse(payload=chat_payload(VALID_SEVERITY_JSON)))
        provider = VllmProvider(make_config(timeout_seconds=20), session=session)
        provider.generate("req-1", "incident text", SEVERITY)

        call = session.calls[0]
        assert call["url"] == f"{DEFAULT_BASE_URL}/chat/completions"
        assert call["timeout"] == 20
        assert "Authorization" not in call["headers"]
        body = call["json"]
        assert body["model"] == "gemma-3-12b-it"
        assert body["temperature"] == 0
        assert body["response_format"] == {"type": "json_object"}
        assert "ONLY a JSON object" in body["messages"][0]["content"]
        assert '"P1", "P2", "P3", "P4"' in body["messages"][0]["content"]
        assert "minimum 0.0" in body["messages"][0]["content"]

    def test_optional_api_key_adds_auth_header(self):
        session = FakeSession(FakeResponse(payload=chat_payload(VALID_SEVERITY_JSON)))
        provider = VllmProvider(make_config(api_key="local-token"), session=session)
        provider.generate("req-1", "incident text", SEVERITY)
        assert session.calls[0]["headers"]["Authorization"] == "Bearer local-token"

    def test_structured_outputs_disabled_omits_response_format(self):
        session = FakeSession(FakeResponse(payload=chat_payload(VALID_SEVERITY_JSON)))
        provider = VllmProvider(
            make_config(structured_outputs=False), session=session
        )
        provider.generate("req-1", "incident text", SEVERITY)
        assert "response_format" not in session.calls[0]["json"]

    def test_prose_response_fails_layer1(self):
        prose = "The severity here looks like P2 because redundancy was lost."
        session = FakeSession(FakeResponse(payload=chat_payload(prose)))
        provider = VllmProvider(make_config(), session=session)
        r = provider.generate("req-1", "incident text", SEVERITY)
        assert r.parsed is None
        assert verify(r, SEVERITY).failures == ["json_parse"]

    def test_fenced_json_is_not_leniently_parsed(self):
        fenced = f"```json\n{VALID_SEVERITY_JSON}\n```"
        session = FakeSession(FakeResponse(payload=chat_payload(fenced)))
        provider = VllmProvider(make_config(), session=session)
        assert provider.generate("req-1", "x", SEVERITY).parsed is None

    def test_missing_usage_defaults_zero(self):
        session = FakeSession(FakeResponse(payload=chat_payload(VALID_SEVERITY_JSON)))
        provider = VllmProvider(make_config(), session=session)
        r = provider.generate("req-1", "x", SEVERITY)
        assert r.prompt_tokens == 0 and r.completion_tokens == 0
        assert r.cost_usd == 0.0

    def test_http_error_raises(self):
        session = FakeSession(FakeResponse(status_code=503, payload={}, text="busy"))
        provider = VllmProvider(make_config(api_key="tok"), session=session)
        with pytest.raises(VllmError) as exc:
            provider.generate("req-1", "x", SEVERITY)
        assert "503" in str(exc.value)
        assert "tok" not in str(exc.value)

    def test_network_exception_wrapped(self):
        session = FakeSession(exc=requests.ConnectionError("refused"))
        provider = VllmProvider(make_config(), session=session)
        with pytest.raises(VllmError, match="ConnectionError"):
            provider.generate("req-1", "x", SEVERITY)


class TestPipelineIntegration:
    def test_vllm_local_pass_stays_local(self):
        store = TrajectoryStore(":memory:")
        try:
            session = FakeSession(
                FakeResponse(payload=chat_payload(VALID_SEVERITY_JSON))
            )
            pipeline = AssurancePipeline(
                router=Router(),
                local_provider=VllmProvider(make_config(), session=session),
                remote_provider=MockProvider(tier="remote"),
                store=store,
            )
            result = pipeline.handle_request(
                "incident", "telecom.severity_classification"
            )
            assert result.verification.passed
            assert not result.escalated
            rows = store.rows_for_request(result.request_id)
            assert len(rows) == 1
            assert rows[0].provider == "vllm-gemma"
            assert rows[0].tier == "local"
        finally:
            store.close()

    def test_vllm_prose_escalates_to_fireworks(self):
        store = TrajectoryStore(":memory:")
        try:
            vllm_session = FakeSession(
                FakeResponse(payload=chat_payload("not json, sorry"))
            )
            fw_session = FakeSession(
                FakeResponse(payload=chat_payload(VALID_SEVERITY_JSON))
            )
            pipeline = AssurancePipeline(
                router=Router(),
                local_provider=VllmProvider(make_config(), session=vllm_session),
                remote_provider=FireworksProvider(
                    FireworksConfig(api_key="k"), session=fw_session
                ),
                store=store,
            )
            result = pipeline.handle_request(
                "incident", "telecom.severity_classification"
            )
            assert result.escalated
            assert result.verification.passed
            rows = store.rows_for_request(result.request_id)
            assert [r.provider for r in rows] == ["vllm-gemma", "fireworks"]
            assert rows[0].verifier_failures == ["json_parse"]
        finally:
            store.close()


class TestCli:
    def test_default_local_stays_mock(self, capsys):
        from kaaval_assurance.eval.cli import main as cli_main

        rc = cli_main(["--dataset", "data/eval/telecom_gold.jsonl", "--json"])
        assert rc == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["metrics"]["pass_rate"] == 1.0

    def test_vllm_without_model_exits_2(self, monkeypatch, capsys):
        from kaaval_assurance.eval.cli import main as cli_main

        monkeypatch.delenv("VLLM_MODEL", raising=False)
        rc = cli_main(
            ["--dataset", "data/eval/telecom_gold.jsonl", "--local-provider", "vllm"]
        )
        assert rc == 2
        assert "VLLM_MODEL" in capsys.readouterr().err

    def test_vllm_rejects_mock_only_flags(self, monkeypatch, capsys):
        from kaaval_assurance.eval.cli import main as cli_main

        monkeypatch.setenv("VLLM_MODEL", "gemma-3-12b-it")
        rc = cli_main(
            ["--dataset", "data/eval/telecom_gold.jsonl",
             "--local-provider", "vllm", "--failure-mode", "bad_enum"]
        )
        assert rc == 2
        assert "mock local" in capsys.readouterr().err

        rc = cli_main(
            ["--dataset", "data/eval/telecom_gold.jsonl",
             "--local-provider", "vllm", "--closed-loop-demo"]
        )
        assert rc == 2
