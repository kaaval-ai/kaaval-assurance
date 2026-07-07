"""Audit challengers: model-backed detection behind a narrow interface.

MockAuditChallenger is deterministic and network-free for tests and demos.
FireworksAuditChallenger sends the cache-aware audit prompt to a Fireworks
chat endpoint with audit-specific knobs (model, temperature, logprobs,
prompt cache keys) configured from environment only.
"""

import json
import math
import os
import random
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Mapping, Optional

import requests
from pydantic import ValidationError

from ..contracts import TaskContract
from ..providers.fireworks import (
    DEFAULT_BASE_URL,
    DEFAULT_MODEL,
    FireworksError,
)
from .models import (
    AuditResult,
    AuditViolation,
    ChallengerOutput,
    aggregate_verdict,
)
from .prompting import build_audit_system_prompt, build_audit_user_prompt


class AuditChallenger(ABC):
    challenger_name: str
    model_id: str

    @abstractmethod
    def challenge(
        self,
        request_id: str,
        task_input: str,
        accepted_answer: dict,
        contract: TaskContract,
    ) -> AuditResult:
        """Audit one accepted answer. Offline only — never in the live path."""
        raise NotImplementedError


class MockAuditChallenger(AuditChallenger):
    """Deterministic challenger: flags a seeded fraction of answers.

    flag_rate 0.0 = clean challenger (every gold answer passes calibration);
    higher rates simulate an over-eager critic for calibration-gate tests.
    """

    def __init__(self, flag_rate: float = 0.0, seed: int = 0):
        self.challenger_name = "mock-audit"
        self.model_id = "mock-challenger"
        self.flag_rate = flag_rate
        self._rng = random.Random(seed)

    def challenge(
        self,
        request_id: str,
        task_input: str,
        accepted_answer: dict,
        contract: TaskContract,
    ) -> AuditResult:
        violations: list[AuditViolation] = []
        if self.flag_rate > 0.0 and self._rng.random() < self.flag_rate:
            field = contract.fields[0].name
            violations.append(
                AuditViolation(
                    check_id="mock_overflag",
                    severity="major",
                    field=field,
                    description=f"mock challenge against '{field}'",
                    evidence=str(accepted_answer.get(field, ""))[:80],
                    repair_hint=(
                        f"Verify '{field}' against the task input specifically."
                    ),
                )
            )
        output = ChallengerOutput(
            result="fail" if violations else "pass", violations=violations
        )
        return AuditResult(
            request_id=request_id,
            category=contract.category,
            contract_id=contract.contract_id,
            audit_provider=self.challenger_name,
            audit_model_id=self.model_id,
            result=aggregate_verdict(output),
            violations=output.violations,
        )


@dataclass(frozen=True)
class FireworksAuditConfig:
    api_key: str
    model: str = DEFAULT_MODEL
    base_url: str = DEFAULT_BASE_URL
    timeout_seconds: float = 60.0
    temperature: float = 0.0
    top_k: Optional[int] = None
    max_tokens: int = 1024
    logprobs: Optional[bool] = None
    top_logprobs: Optional[int] = None
    prompt_cache_key: Optional[str] = None
    prompt_cache_isolation_key: Optional[str] = None
    thinking_budget_tokens: Optional[int] = None
    cost_per_prompt_token: float = 0.0
    cost_per_completion_token: float = 0.0

    @classmethod
    def from_env(cls, env: Optional[Mapping[str, str]] = None) -> "FireworksAuditConfig":
        env = os.environ if env is None else env
        api_key = env.get("FIREWORKS_API_KEY", "").strip()
        if not api_key:
            raise ValueError(
                "FIREWORKS_API_KEY is not set; export it before using the "
                "fireworks audit challenger"
            )
        top_k = env.get("FIREWORKS_AUDIT_TOP_K", "").strip()
        top_logprobs = env.get("FIREWORKS_AUDIT_TOP_LOGPROBS", "").strip()
        logprobs = env.get("FIREWORKS_AUDIT_LOGPROBS", "").strip()
        thinking = env.get("FIREWORKS_AUDIT_THINKING_BUDGET_TOKENS", "").strip()
        return cls(
            api_key=api_key,
            model=env.get("FIREWORKS_AUDIT_MODEL")
            or env.get("FIREWORKS_MODEL")
            or DEFAULT_MODEL,
            base_url=env.get("FIREWORKS_BASE_URL", DEFAULT_BASE_URL).rstrip("/"),
            timeout_seconds=float(env.get("FIREWORKS_TIMEOUT_SECONDS", "60")),
            temperature=float(env.get("FIREWORKS_AUDIT_TEMPERATURE", "0")),
            top_k=int(top_k) if top_k else None,
            max_tokens=int(env.get("FIREWORKS_AUDIT_MAX_TOKENS", "1024")),
            logprobs=logprobs.lower() in ("1", "true", "yes", "on")
            if logprobs
            else None,
            top_logprobs=int(top_logprobs) if top_logprobs else None,
            prompt_cache_key=env.get("FIREWORKS_AUDIT_PROMPT_CACHE_KEY") or None,
            prompt_cache_isolation_key=env.get(
                "FIREWORKS_AUDIT_PROMPT_CACHE_ISOLATION_KEY"
            )
            or None,
            thinking_budget_tokens=int(thinking) if thinking else None,
            cost_per_prompt_token=float(
                env.get("FIREWORKS_COST_PER_PROMPT_TOKEN", "0")
            ),
            cost_per_completion_token=float(
                env.get("FIREWORKS_COST_PER_COMPLETION_TOKEN", "0")
            ),
        )


def _confidence_proxy(choice: dict) -> Optional[float]:
    """Mean token probability from returned logprobs. Model-output confidence
    telemetry only — not a truth score. None when logprobs are unavailable."""
    content = (choice.get("logprobs") or {}).get("content") or []
    logprob_values = [
        t["logprob"] for t in content if isinstance(t, dict) and "logprob" in t
    ]
    if not logprob_values:
        return None
    mean = sum(logprob_values) / len(logprob_values)
    return max(0.0, min(1.0, math.exp(mean)))


class FireworksAuditChallenger(AuditChallenger):
    def __init__(
        self,
        config: Optional[FireworksAuditConfig] = None,
        session: Optional[requests.Session] = None,
    ):
        self.config = config or FireworksAuditConfig.from_env()
        self.challenger_name = "fireworks-audit"
        self.model_id = self.config.model
        self._session = session or requests.Session()

    def _build_payload(self, contract: TaskContract, user_prompt: str) -> dict:
        cfg = self.config
        payload = {
            "model": cfg.model,
            "messages": [
                {"role": "system", "content": build_audit_system_prompt(contract)},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": cfg.temperature,
            "max_tokens": cfg.max_tokens,
            "response_format": {"type": "json_object"},
        }
        if cfg.top_k is not None:
            payload["top_k"] = cfg.top_k
        if cfg.logprobs is not None:
            payload["logprobs"] = cfg.logprobs
        if cfg.top_logprobs is not None:
            payload["top_logprobs"] = cfg.top_logprobs
        if cfg.prompt_cache_key is not None:
            payload["prompt_cache_key"] = cfg.prompt_cache_key
        if cfg.prompt_cache_isolation_key is not None:
            payload["prompt_cache_isolation_key"] = cfg.prompt_cache_isolation_key
        if cfg.thinking_budget_tokens is not None:
            payload["thinking_budget_tokens"] = cfg.thinking_budget_tokens
        return payload

    def challenge(
        self,
        request_id: str,
        task_input: str,
        accepted_answer: dict,
        contract: TaskContract,
    ) -> AuditResult:
        cfg = self.config
        url = f"{cfg.base_url.rstrip('/')}/chat/completions"
        payload = self._build_payload(
            contract, build_audit_user_prompt(task_input, accepted_answer)
        )
        headers = {"Authorization": f"Bearer {cfg.api_key}"}

        started = time.perf_counter()
        try:
            resp = self._session.post(
                url, json=payload, headers=headers, timeout=cfg.timeout_seconds
            )
        except requests.RequestException as e:
            raise FireworksError(
                f"fireworks audit request failed: {type(e).__name__}: {e}"
            ) from e
        latency_ms = (time.perf_counter() - started) * 1000.0

        if resp.status_code != 200:
            raise FireworksError(
                f"fireworks audit HTTP {resp.status_code}: {resp.text[:200]}"
            )
        try:
            data = resp.json()
            choice = data["choices"][0]
            raw_text = choice["message"]["content"] or ""
        except (ValueError, KeyError, IndexError, TypeError) as e:
            raise FireworksError(
                f"unexpected fireworks audit response shape: {type(e).__name__}: {e}"
            ) from e

        usage = data.get("usage") or {}
        prompt_tokens = int(usage.get("prompt_tokens") or 0)
        completion_tokens = int(usage.get("completion_tokens") or 0)
        cached = usage.get("cached_tokens")
        if cached is None:
            cached = (usage.get("prompt_tokens_details") or {}).get("cached_tokens")

        base = dict(
            request_id=request_id,
            category=contract.category,
            contract_id=contract.contract_id,
            audit_provider=self.challenger_name,
            audit_model_id=self.model_id,
            latency_ms=latency_ms,
            cost_usd=prompt_tokens * cfg.cost_per_prompt_token
            + completion_tokens * cfg.cost_per_completion_token,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cached_tokens=int(cached) if cached is not None else None,
            confidence_proxy=_confidence_proxy(choice),
        )
        try:
            output = ChallengerOutput.model_validate(json.loads(raw_text))
        except (json.JSONDecodeError, ValidationError):
            # Model-generated detection failed our strict schema: record as an
            # error, never as a violation and never as a silent pass signal.
            return AuditResult(result="error", parse_ok=False, **base)
        return AuditResult(
            result=aggregate_verdict(output),
            violations=output.violations,
            **base,
        )
