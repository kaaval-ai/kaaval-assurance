"""Fireworks AI remote provider: the escalation tier.

Calls the OpenAI-compatible /chat/completions endpoint over HTTP via
`requests`. Configuration comes from environment variables only — no file
coupling — so the same code runs locally, in CI, and on AMD Developer Cloud.

The system prompt is contract-aware and demands a bare JSON object, but the
model may still disobey (glm-5p2 tends to explain on weak prompts). Layer 1
verification remains the source of truth for acceptability; this provider
never pre-judges its own output beyond attempting a JSON parse.
"""

import json
import os
import time
from dataclasses import dataclass
from typing import Mapping, Optional

import requests

from ..contracts import TaskContract
from ..models import ModelResponse
from .base import Provider
from .prompting import build_contract_prompt

DEFAULT_MODEL = "accounts/fireworks/models/glm-5p2"
DEFAULT_BASE_URL = "https://api.fireworks.ai/inference/v1"


class FireworksError(RuntimeError):
    """Fireworks API call failed. Messages never contain the API key."""


@dataclass(frozen=True)
class FireworksConfig:
    api_key: str
    model: str = DEFAULT_MODEL
    base_url: str = DEFAULT_BASE_URL
    timeout_seconds: float = 60.0
    cost_per_prompt_token: float = 0.0
    cost_per_completion_token: float = 0.0

    @classmethod
    def from_env(cls, env: Optional[Mapping[str, str]] = None) -> "FireworksConfig":
        env = os.environ if env is None else env
        api_key = env.get("FIREWORKS_API_KEY", "").strip()
        if not api_key:
            raise ValueError(
                "FIREWORKS_API_KEY is not set; export it before using the "
                "fireworks provider (e.g. `set -a; source .env; set +a`)"
            )
        return cls(
            api_key=api_key,
            model=env.get("FIREWORKS_MODEL", DEFAULT_MODEL),
            base_url=env.get("FIREWORKS_BASE_URL", DEFAULT_BASE_URL).rstrip("/"),
            timeout_seconds=float(env.get("FIREWORKS_TIMEOUT_SECONDS", "60")),
            cost_per_prompt_token=float(
                env.get("FIREWORKS_COST_PER_PROMPT_TOKEN", "0")
            ),
            cost_per_completion_token=float(
                env.get("FIREWORKS_COST_PER_COMPLETION_TOKEN", "0")
            ),
        )


class FireworksProvider(Provider):
    def __init__(
        self,
        config: Optional[FireworksConfig] = None,
        session: Optional[requests.Session] = None,
    ):
        self.config = config or FireworksConfig.from_env()
        self.provider_name = "fireworks"
        self.tier = "remote"
        self.model_id = self.config.model
        self._session = session or requests.Session()

    def generate(
        self, request_id: str, task_input: str, contract: TaskContract
    ) -> ModelResponse:
        url = f"{self.config.base_url.rstrip('/')}/chat/completions"
        payload = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": build_contract_prompt(contract)},
                {"role": "user", "content": task_input},
            ],
            "temperature": 0,
            "max_tokens": 1024,
        }

        started = time.perf_counter()
        try:
            resp = self._session.post(
                url,
                json=payload,
                headers={"Authorization": f"Bearer {self.config.api_key}"},
                timeout=self.config.timeout_seconds,
            )
        except requests.RequestException as e:
            raise FireworksError(
                f"fireworks request failed: {type(e).__name__}: {e}"
            ) from e
        latency_ms = (time.perf_counter() - started) * 1000.0

        if resp.status_code != 200:
            raise FireworksError(
                f"fireworks HTTP {resp.status_code}: {resp.text[:200]}"
            )
        try:
            data = resp.json()
            raw_text = data["choices"][0]["message"]["content"] or ""
        except (ValueError, KeyError, IndexError, TypeError) as e:
            raise FireworksError(
                f"unexpected fireworks response shape: {type(e).__name__}: {e}"
            ) from e

        usage = data.get("usage") or {}
        prompt_tokens = int(usage.get("prompt_tokens") or 0)
        completion_tokens = int(usage.get("completion_tokens") or 0)
        cached = usage.get("cached_tokens")
        if cached is None:
            cached = (usage.get("prompt_tokens_details") or {}).get("cached_tokens")

        try:
            parsed = json.loads(raw_text)
            if not isinstance(parsed, dict):
                parsed = None
        except json.JSONDecodeError:
            parsed = None

        cost_usd = (
            prompt_tokens * self.config.cost_per_prompt_token
            + completion_tokens * self.config.cost_per_completion_token
        )
        return ModelResponse(
            request_id=request_id,
            provider=self.provider_name,
            model_id=self.model_id,
            tier="remote",
            raw_text=raw_text,
            parsed=parsed,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=latency_ms,
            cost_usd=cost_usd,
            cached_tokens=int(cached) if cached is not None else None,
        )
