"""Ollama local provider: OpenAI-compatible /v1 on a developer machine.

Development comparison/fallback tier only — Gemma served via vLLM on the AMD
hackathon GPU remains the Track 3 proof target, and Gemma stays the preferred
model family here too. The request path is identical to the vLLM provider
(same OpenAI-compatible protocol); only the labels, defaults, and env prefix
differ, and telemetry records provider="ollama" with its own hardware target
so local-Mac runs can never masquerade as AMD runs.
"""

import os
from typing import Literal, Mapping, Optional

import requests

from ..contracts import TaskContract
from ..models import ModelResponse
from .vllm import VllmConfig, VllmProvider, _parse_bool
from .vllm import VllmError

DEFAULT_BASE_URL = "http://127.0.0.1:11434/v1"
DEFAULT_HARDWARE_TARGET = "local-mac-ollama"


class OllamaError(VllmError):
    """Ollama endpoint call failed without exposing credentials."""


def ollama_config_from_env(env: Optional[Mapping[str, str]] = None) -> VllmConfig:
    env = os.environ if env is None else env
    model = env.get("OLLAMA_MODEL", "").strip()
    if not model:
        raise ValueError(
            "OLLAMA_MODEL is not set; set it to a served Ollama model "
            "(Gemma preferred, e.g. a gemma tag) before using the ollama "
            "provider"
        )
    return VllmConfig(
        model=model,
        base_url=env.get("OLLAMA_BASE_URL", DEFAULT_BASE_URL).rstrip("/"),
        timeout_seconds=float(env.get("OLLAMA_TIMEOUT_SECONDS", "120")),
        api_key=env.get("OLLAMA_API_KEY", "").strip(),
        # Serving knobs below are vLLM engine concepts; they do not apply to
        # Ollama and are recorded as empty rather than inherited defaults.
        dtype="",
        kv_cache_dtype="",
        enable_prefix_caching=False,
        gpu_memory_utilization=0.0,
        tensor_parallel_size=1,
        structured_outputs=_parse_bool(
            env.get("OLLAMA_STRUCTURED_OUTPUTS", ""), False
        ),
        hardware_target=env.get("OLLAMA_HARDWARE_TARGET", DEFAULT_HARDWARE_TARGET),
        model_family=env.get("OLLAMA_MODEL_FAMILY", "gemma"),
    )


class OllamaProvider(VllmProvider):
    label = "ollama"

    def __init__(
        self,
        config: Optional[VllmConfig] = None,
        session: Optional[requests.Session] = None,
        tier: Literal["local", "remote"] = "local",
    ):
        super().__init__(
            config or ollama_config_from_env(),
            session=session,
            tier=tier,
            provider_name="ollama",
        )

    def generate(
        self, request_id: str, task_input: str, contract: TaskContract
    ) -> ModelResponse:
        try:
            return super().generate(request_id, task_input, contract)
        except VllmError as exc:
            raise OllamaError(str(exc)) from exc
