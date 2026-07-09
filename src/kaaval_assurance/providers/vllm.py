"""vLLM provider: the local Gemma open-weight tier.

Targets an OpenAI-compatible vLLM endpoint (ROCm backend on AMD Developer
Cloud is the planned deployment; any /v1 vLLM server works). Configuration is
environment-only. The runtime knobs (dtype, FP8 KV cache, prefix caching,
tensor parallelism, GPU memory utilization) mirror vLLM engine args and are
recorded in a RuntimeProfile so telemetry can state which serving settings
produced each result — recorded configuration, never measured claims.

When structured outputs are enabled the request asks vLLM for a JSON object
via response_format, but Layer 1 verification remains the source of truth:
prose or fenced output still parses to None and fails the contract check.
"""

import json
import os
import time
from dataclasses import dataclass
from typing import Mapping, Optional
from urllib.parse import urlparse

import requests

from ..contracts import TaskContract
from ..models import ModelResponse, RuntimeProfile
from .base import Provider
from .prompting import build_contract_prompt

DEFAULT_BASE_URL = "http://localhost:8000/v1"

_TRUE_VALUES = {"1", "true", "yes", "on"}


def _parse_bool(value: str, default: bool) -> bool:
    if value == "":
        return default
    return value.strip().lower() in _TRUE_VALUES


class VllmError(RuntimeError):
    """OpenAI-compatible endpoint call failed. Messages never contain credentials."""


def base_url_host(base_url: str) -> Optional[str]:
    """Host (and port) only — safe for telemetry; never the full URL."""
    parsed = urlparse(base_url)
    if not parsed.hostname:
        return None
    return (
        f"{parsed.hostname}:{parsed.port}" if parsed.port else parsed.hostname
    )


@dataclass(frozen=True)
class VllmConfig:
    model: str
    base_url: str = DEFAULT_BASE_URL
    timeout_seconds: float = 60.0
    api_key: str = ""  # optional; local vLLM usually runs without auth
    dtype: str = "bfloat16"
    kv_cache_dtype: str = "fp8"
    enable_prefix_caching: bool = True
    gpu_memory_utilization: float = 0.92
    tensor_parallel_size: int = 1
    structured_outputs: bool = True
    max_context_tokens: Optional[int] = None
    hardware_target: str = "amd-hackathon-gpu"
    rocm_version: Optional[str] = None
    vllm_version: Optional[str] = None
    cost_per_prompt_token: float = 0.0
    cost_per_completion_token: float = 0.0
    model_family: str = "gemma"  # configurable; recorded, never inferred

    @classmethod
    def from_env(cls, env: Optional[Mapping[str, str]] = None) -> "VllmConfig":
        env = os.environ if env is None else env
        model = env.get("VLLM_MODEL", "").strip()
        if not model:
            raise ValueError(
                "VLLM_MODEL is not set; set it to the served Gemma model name "
                "before using the vllm provider"
            )
        max_context = env.get("VLLM_MAX_CONTEXT_TOKENS", "").strip()
        return cls(
            model=model,
            base_url=env.get("VLLM_BASE_URL", DEFAULT_BASE_URL).rstrip("/"),
            timeout_seconds=float(env.get("VLLM_TIMEOUT_SECONDS", "60")),
            api_key=env.get("VLLM_API_KEY", "").strip(),
            dtype=env.get("VLLM_DTYPE", "bfloat16"),
            kv_cache_dtype=env.get("VLLM_KV_CACHE_DTYPE", "fp8"),
            enable_prefix_caching=_parse_bool(
                env.get("VLLM_ENABLE_PREFIX_CACHING", ""), True
            ),
            gpu_memory_utilization=float(
                env.get("VLLM_GPU_MEMORY_UTILIZATION", "0.92")
            ),
            tensor_parallel_size=int(env.get("VLLM_TENSOR_PARALLEL_SIZE", "1")),
            structured_outputs=_parse_bool(env.get("VLLM_STRUCTURED_OUTPUTS", ""), True),
            max_context_tokens=int(max_context) if max_context else None,
            hardware_target=env.get("VLLM_HARDWARE_TARGET", "amd-hackathon-gpu"),
            rocm_version=env.get("VLLM_ROCM_VERSION") or None,
            vllm_version=env.get("VLLM_VERSION") or None,
            cost_per_prompt_token=float(env.get("VLLM_COST_PER_PROMPT_TOKEN", "0")),
            cost_per_completion_token=float(
                env.get("VLLM_COST_PER_COMPLETION_TOKEN", "0")
            ),
            model_family=env.get("VLLM_MODEL_FAMILY", "gemma"),
        )


class VllmProvider(Provider):
    # Subclasses serving other OpenAI-compatible runtimes (e.g. Ollama)
    # override these labels; the request/verify path is identical.
    label = "vllm"
    endpoint_type = "openai_compatible"

    def __init__(
        self,
        config: Optional[VllmConfig] = None,
        session: Optional[requests.Session] = None,
    ):
        self.config = config or VllmConfig.from_env()
        self.provider_name = "vllm-gemma"
        self.tier = "local"
        self.model_id = self.config.model
        self._session = session or requests.Session()

    def runtime_profile(self) -> RuntimeProfile:
        cfg = self.config
        return RuntimeProfile(
            provider=self.provider_name,
            model_id=cfg.model,
            served_model_name=cfg.model,
            tier=self.tier,
            endpoint_type=self.endpoint_type,
            base_url_host=base_url_host(cfg.base_url),
            hardware_target=cfg.hardware_target,
            rocm_version=cfg.rocm_version,
            vllm_version=cfg.vllm_version,
            dtype=cfg.dtype,
            kv_cache_dtype=cfg.kv_cache_dtype,
            tensor_parallel_size=cfg.tensor_parallel_size,
            gpu_memory_utilization=cfg.gpu_memory_utilization,
            prefix_caching_enabled=cfg.enable_prefix_caching,
            max_context_tokens=cfg.max_context_tokens,
            structured_output_mode=(
                "json_object" if cfg.structured_outputs else "none"
            ),
            model_family=cfg.model_family,
            temperature=0.0,
            max_tokens=1024,
        )

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
        if self.config.structured_outputs:
            payload["response_format"] = {"type": "json_object"}
        headers = {}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"

        started = time.perf_counter()
        try:
            resp = self._session.post(
                url,
                json=payload,
                headers=headers,
                timeout=self.config.timeout_seconds,
            )
        except requests.RequestException as e:
            raise VllmError(
                f"{self.label} request failed: {type(e).__name__}: {e}"
            ) from e
        latency_ms = (time.perf_counter() - started) * 1000.0

        if resp.status_code != 200:
            raise VllmError(
                f"{self.label} HTTP {resp.status_code}: {resp.text[:200]}"
            )
        try:
            data = resp.json()
            raw_text = data["choices"][0]["message"]["content"] or ""
        except (ValueError, KeyError, IndexError, TypeError) as e:
            raise VllmError(
                f"unexpected {self.label} response shape: {type(e).__name__}: {e}"
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
            tier="local",
            raw_text=raw_text,
            parsed=parsed,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=latency_ms,
            cost_usd=cost_usd,
            cached_tokens=int(cached) if cached is not None else None,
        )
