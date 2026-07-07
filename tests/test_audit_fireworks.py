"""Fireworks audit challenger tests. All HTTP faked — no network, no keys."""

import json

import pytest

from kaaval_assurance.audit import (
    FireworksAuditChallenger,
    FireworksAuditConfig,
)
from kaaval_assurance.contracts import get_contract
from kaaval_assurance.providers.fireworks import DEFAULT_MODEL, FireworksError

SEVERITY = get_contract("telecom.severity_classification")

GOLD_ANSWER = {"severity": "P1", "confidence": 0.95, "rationale": "regional outage"}

CLEAN_OUTPUT = json.dumps({"result": "pass", "violations": []})
FLAGGING_OUTPUT = json.dumps(
    {
        "result": "fail",
        "violations": [
            {
                "check_id": "severity_support",
                "severity": "major",
                "field": "severity",
                "description": "severity not supported by stated impact",
                "evidence": "no customer complaints",
                "repair_hint": "Verify the severity label against impact.",
            }
        ],
    }
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


def chat_payload(content, usage=None, logprobs=None):
    choice = {"message": {"content": content}}
    if logprobs is not None:
        choice["logprobs"] = logprobs
    payload = {"choices": [choice]}
    if usage is not None:
        payload["usage"] = usage
    return payload


def make_config(**overrides):
    defaults = dict(api_key="test-key")
    defaults.update(overrides)
    return FireworksAuditConfig(**defaults)


TASK_INPUT = "CR-99 dropped all BGP sessions at 03:12 test-marker-x7"


def challenge(challenger):
    return challenger.challenge("req-1", TASK_INPUT, GOLD_ANSWER, SEVERITY)


class TestConfig:
    def test_from_env_audit_specific_vars(self):
        env = {
            "FIREWORKS_API_KEY": "k",
            "FIREWORKS_MODEL": "accounts/fireworks/models/base",
            "FIREWORKS_AUDIT_MODEL": "accounts/fireworks/models/auditor",
            "FIREWORKS_AUDIT_TEMPERATURE": "0.2",
            "FIREWORKS_AUDIT_TOP_K": "40",
            "FIREWORKS_AUDIT_MAX_TOKENS": "512",
            "FIREWORKS_AUDIT_LOGPROBS": "true",
            "FIREWORKS_AUDIT_TOP_LOGPROBS": "5",
            "FIREWORKS_AUDIT_PROMPT_CACHE_KEY": "audit-v1",
            "FIREWORKS_AUDIT_THINKING_BUDGET_TOKENS": "256",
        }
        cfg = FireworksAuditConfig.from_env(env)
        assert cfg.model == "accounts/fireworks/models/auditor"
        assert cfg.temperature == pytest.approx(0.2)
        assert cfg.top_k == 40
        assert cfg.max_tokens == 512
        assert cfg.logprobs is True
        assert cfg.top_logprobs == 5
        assert cfg.prompt_cache_key == "audit-v1"
        assert cfg.thinking_budget_tokens == 256

    def test_audit_model_falls_back_to_generation_model(self):
        cfg = FireworksAuditConfig.from_env(
            {"FIREWORKS_API_KEY": "k", "FIREWORKS_MODEL": "accounts/f/models/m"}
        )
        assert cfg.model == "accounts/f/models/m"
        cfg2 = FireworksAuditConfig.from_env({"FIREWORKS_API_KEY": "k"})
        assert cfg2.model == DEFAULT_MODEL

    def test_missing_key_raises(self):
        with pytest.raises(ValueError, match="FIREWORKS_API_KEY"):
            FireworksAuditConfig.from_env({})


class TestChallenge:
    def test_clean_output_passes(self):
        session = FakeSession(
            FakeResponse(
                payload=chat_payload(
                    CLEAN_OUTPUT,
                    usage={"prompt_tokens": 200, "completion_tokens": 10},
                )
            )
        )
        challenger = FireworksAuditChallenger(
            make_config(cost_per_prompt_token=1e-6, cost_per_completion_token=2e-6),
            session=session,
        )
        r = challenge(challenger)
        assert r.result == "pass"
        assert r.parse_ok
        assert r.violations == []
        assert r.prompt_tokens == 200
        assert r.cost_usd == pytest.approx(200e-6 + 20e-6)

    def test_flagging_output_fails_with_violations(self):
        session = FakeSession(FakeResponse(payload=chat_payload(FLAGGING_OUTPUT)))
        r = challenge(FireworksAuditChallenger(make_config(), session=session))
        assert r.result == "fail"
        assert r.violations[0].check_id == "severity_support"
        assert r.violations[0].repair_hint.startswith("Verify")

    def test_payload_shape_and_optional_knobs_absent_by_default(self):
        session = FakeSession(FakeResponse(payload=chat_payload(CLEAN_OUTPUT)))
        challenge(FireworksAuditChallenger(make_config(), session=session))
        body = session.calls[0]["json"]
        assert body["response_format"] == {"type": "json_object"}
        assert body["temperature"] == 0.0
        assert body["max_tokens"] == 1024
        for knob in (
            "top_k",
            "logprobs",
            "top_logprobs",
            "prompt_cache_key",
            "prompt_cache_isolation_key",
            "thinking_budget_tokens",
        ):
            assert knob not in body

    def test_optional_knobs_passed_when_configured(self):
        session = FakeSession(FakeResponse(payload=chat_payload(CLEAN_OUTPUT)))
        challenge(
            FireworksAuditChallenger(
                make_config(
                    top_k=40,
                    logprobs=True,
                    top_logprobs=3,
                    prompt_cache_key="audit-v1",
                    thinking_budget_tokens=128,
                ),
                session=session,
            )
        )
        body = session.calls[0]["json"]
        assert body["top_k"] == 40
        assert body["logprobs"] is True
        assert body["top_logprobs"] == 3
        assert body["prompt_cache_key"] == "audit-v1"
        assert body["thinking_budget_tokens"] == 128

    def test_prompt_split_stable_system_variable_user(self):
        session = FakeSession(FakeResponse(payload=chat_payload(CLEAN_OUTPUT)))
        challenge(FireworksAuditChallenger(make_config(), session=session))
        messages = session.calls[0]["json"]["messages"]
        assert "Verify these specifically" in messages[0]["content"]
        assert "test-marker-x7" not in messages[0]["content"]  # stable prefix
        assert "test-marker-x7" in messages[1]["content"]

    def test_confidence_proxy_from_logprobs(self):
        logprobs = {"content": [{"logprob": -0.1}, {"logprob": -0.3}]}
        session = FakeSession(
            FakeResponse(payload=chat_payload(CLEAN_OUTPUT, logprobs=logprobs))
        )
        r = challenge(FireworksAuditChallenger(make_config(), session=session))
        assert r.confidence_proxy == pytest.approx(0.8187, abs=1e-3)

    def test_confidence_proxy_none_without_logprobs(self):
        session = FakeSession(FakeResponse(payload=chat_payload(CLEAN_OUTPUT)))
        r = challenge(FireworksAuditChallenger(make_config(), session=session))
        assert r.confidence_proxy is None  # never fabricated

    def test_cached_tokens_recorded_when_reported(self):
        session = FakeSession(
            FakeResponse(
                payload=chat_payload(
                    CLEAN_OUTPUT,
                    usage={
                        "prompt_tokens": 200,
                        "completion_tokens": 10,
                        "prompt_tokens_details": {"cached_tokens": 150},
                    },
                )
            )
        )
        r = challenge(FireworksAuditChallenger(make_config(), session=session))
        assert r.cached_tokens == 150

    def test_malformed_challenger_output_is_error_not_violation(self):
        session = FakeSession(
            FakeResponse(payload=chat_payload("the answer looks mostly fine"))
        )
        r = challenge(FireworksAuditChallenger(make_config(), session=session))
        assert r.result == "error"
        assert r.parse_ok is False
        assert r.violations == []

    def test_http_error_raises_without_key_leak(self):
        session = FakeSession(FakeResponse(status_code=500, payload={}, text="boom"))
        challenger = FireworksAuditChallenger(
            make_config(api_key="sk-secret"), session=session
        )
        with pytest.raises(FireworksError) as exc:
            challenge(challenger)
        assert "sk-secret" not in str(exc.value)
