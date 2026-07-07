"""FireworksProvider tests. All HTTP is faked — no network, no API key."""

import json

import pytest
import requests

from kaaval_assurance.contracts import get_contract
from kaaval_assurance.pipeline import AssurancePipeline
from kaaval_assurance.providers import MockProvider
from kaaval_assurance.providers.fireworks import (
    DEFAULT_BASE_URL,
    DEFAULT_MODEL,
    FireworksConfig,
    FireworksError,
    FireworksProvider,
    build_contract_prompt,
)
from kaaval_assurance.router import Router
from kaaval_assurance.trajectory import TrajectoryStore
from kaaval_assurance.verifier import verify

SEVERITY = get_contract("telecom.severity_classification")

VALID_SEVERITY_JSON = json.dumps(
    {"severity": "P1", "confidence": 0.9, "rationale": "regional outage"}
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
    defaults = dict(api_key="test-key")
    defaults.update(overrides)
    return FireworksConfig(**defaults)


class TestConfig:
    def test_from_env_reads_all_vars(self):
        env = {
            "FIREWORKS_API_KEY": "k",
            "FIREWORKS_MODEL": "accounts/fireworks/models/other",
            "FIREWORKS_BASE_URL": "https://example.test/v1/",
            "FIREWORKS_TIMEOUT_SECONDS": "10",
            "FIREWORKS_COST_PER_PROMPT_TOKEN": "0.000001",
            "FIREWORKS_COST_PER_COMPLETION_TOKEN": "0.000002",
        }
        cfg = FireworksConfig.from_env(env)
        assert cfg.model == "accounts/fireworks/models/other"
        assert cfg.base_url == "https://example.test/v1"  # trailing slash stripped
        assert cfg.timeout_seconds == 10.0
        assert cfg.cost_per_prompt_token == pytest.approx(1e-6)
        assert cfg.cost_per_completion_token == pytest.approx(2e-6)

    def test_from_env_defaults(self):
        cfg = FireworksConfig.from_env({"FIREWORKS_API_KEY": "k"})
        assert cfg.model == DEFAULT_MODEL
        assert cfg.base_url == DEFAULT_BASE_URL
        assert cfg.timeout_seconds == 60.0
        assert cfg.cost_per_prompt_token == 0.0

    def test_missing_api_key_raises(self):
        with pytest.raises(ValueError, match="FIREWORKS_API_KEY"):
            FireworksConfig.from_env({})


class TestContractPrompt:
    def test_prompt_is_strict_and_contract_aware(self):
        prompt = build_contract_prompt(SEVERITY)
        assert "ONLY a JSON object" in prompt
        assert "No markdown" in prompt
        assert '"severity"' in prompt
        assert '"P1", "P2", "P3", "P4"' in prompt
        assert "minimum 0.0" in prompt and "maximum 1.0" in prompt


class TestGenerate:
    def test_valid_json_response(self):
        session = FakeSession(
            FakeResponse(
                payload=chat_payload(
                    VALID_SEVERITY_JSON,
                    usage={"prompt_tokens": 100, "completion_tokens": 40},
                )
            )
        )
        provider = FireworksProvider(
            make_config(cost_per_prompt_token=1e-6, cost_per_completion_token=2e-6),
            session=session,
        )
        r = provider.generate("req-1", "incident text", SEVERITY)

        assert r.provider == "fireworks"
        assert r.tier == "remote"
        assert r.model_id == DEFAULT_MODEL
        assert r.raw_text == VALID_SEVERITY_JSON
        assert r.parsed == {"severity": "P1", "confidence": 0.9,
                            "rationale": "regional outage"}
        assert r.prompt_tokens == 100
        assert r.completion_tokens == 40
        assert r.cost_usd == pytest.approx(100e-6 + 80e-6)
        assert r.latency_ms >= 0.0
        assert verify(r, SEVERITY).passed

    def test_request_shape(self):
        session = FakeSession(FakeResponse(payload=chat_payload(VALID_SEVERITY_JSON)))
        provider = FireworksProvider(make_config(timeout_seconds=15), session=session)
        provider.generate("req-1", "incident text", SEVERITY)

        call = session.calls[0]
        assert call["url"] == f"{DEFAULT_BASE_URL}/chat/completions"
        assert call["timeout"] == 15
        assert call["headers"]["Authorization"] == "Bearer test-key"
        body = call["json"]
        assert body["model"] == DEFAULT_MODEL
        assert body["temperature"] == 0
        assert body["messages"][0]["role"] == "system"
        assert "ONLY a JSON object" in body["messages"][0]["content"]
        assert body["messages"][1] == {"role": "user", "content": "incident text"}

    def test_prose_response_parses_to_none_and_fails_layer1(self):
        # glm-5p2 on weak prompts explains instead of emitting JSON.
        prose = "Sure — based on the incident, severity should be P1 because..."
        session = FakeSession(FakeResponse(payload=chat_payload(prose)))
        provider = FireworksProvider(make_config(), session=session)
        r = provider.generate("req-1", "incident text", SEVERITY)

        assert r.raw_text == prose
        assert r.parsed is None
        result = verify(r, SEVERITY)
        assert not result.passed
        assert result.failures == ["json_parse"]

    def test_fenced_json_is_not_leniently_parsed(self):
        fenced = f"```json\n{VALID_SEVERITY_JSON}\n```"
        session = FakeSession(FakeResponse(payload=chat_payload(fenced)))
        provider = FireworksProvider(make_config(), session=session)
        r = provider.generate("req-1", "incident text", SEVERITY)
        assert r.parsed is None  # Layer 1 stays the source of truth

    def test_missing_usage_defaults_zero(self):
        session = FakeSession(FakeResponse(payload=chat_payload(VALID_SEVERITY_JSON)))
        provider = FireworksProvider(make_config(), session=session)
        r = provider.generate("req-1", "incident text", SEVERITY)
        assert r.prompt_tokens == 0
        assert r.completion_tokens == 0
        assert r.cost_usd == 0.0

    def test_http_error_raises_without_leaking_key(self):
        session = FakeSession(FakeResponse(status_code=500, payload={}, text="boom"))
        provider = FireworksProvider(make_config(api_key="sk-secret"), session=session)
        with pytest.raises(FireworksError) as exc:
            provider.generate("req-1", "incident text", SEVERITY)
        assert "500" in str(exc.value)
        assert "sk-secret" not in str(exc.value)

    def test_network_exception_wrapped(self):
        session = FakeSession(exc=requests.ConnectionError("dns failure"))
        provider = FireworksProvider(make_config(), session=session)
        with pytest.raises(FireworksError, match="ConnectionError"):
            provider.generate("req-1", "incident text", SEVERITY)

    def test_malformed_response_shape_raises(self):
        session = FakeSession(FakeResponse(payload={"choices": []}))
        provider = FireworksProvider(make_config(), session=session)
        with pytest.raises(FireworksError, match="unexpected fireworks response"):
            provider.generate("req-1", "incident text", SEVERITY)


class TestPipelineIntegration:
    def test_local_failure_escalates_to_fireworks(self):
        store = TrajectoryStore(":memory:")
        try:
            session = FakeSession(
                FakeResponse(
                    payload=chat_payload(
                        VALID_SEVERITY_JSON,
                        usage={"prompt_tokens": 80, "completion_tokens": 30},
                    )
                )
            )
            pipeline = AssurancePipeline(
                router=Router(),
                local_provider=MockProvider(tier="local", failure_mode="bad_enum"),
                remote_provider=FireworksProvider(make_config(), session=session),
                store=store,
            )
            result = pipeline.handle_request("incident", "telecom.severity_classification")

            assert result.escalated
            assert result.verification.passed
            assert result.response.provider == "fireworks"

            rows = store.rows_for_request(result.request_id)
            assert len(rows) == 2
            assert rows[1].provider == "fireworks"
            assert rows[1].tier == "remote"
            assert rows[1].prompt_tokens == 80
        finally:
            store.close()


class TestCli:
    def test_fireworks_without_key_exits_2(self, monkeypatch, capsys):
        from kaaval_assurance.eval.cli import main as cli_main

        monkeypatch.delenv("FIREWORKS_API_KEY", raising=False)
        rc = cli_main(
            ["--dataset", "data/eval/telecom_gold.jsonl",
             "--remote-provider", "fireworks"]
        )
        assert rc == 2
        assert "FIREWORKS_API_KEY" in capsys.readouterr().err

    def test_default_remote_stays_mock(self, capsys):
        from kaaval_assurance.eval.cli import main as cli_main

        rc = cli_main(["--dataset", "data/eval/telecom_gold.jsonl", "--json"])
        assert rc == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["metrics"]["pass_rate"] == 1.0
