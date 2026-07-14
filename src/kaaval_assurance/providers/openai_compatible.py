"""Generic OpenAI-compatible remote provider: any /v1/chat/completions endpoint.

The provider-neutral escalation tier. Fireworks remains a first-class,
tuned integration; this provider covers everything else that speaks the
OpenAI chat-completions protocol — OpenAI itself, Together, Groq,
OpenRouter, a remote vLLM box, a colleague's Ollama over a tunnel —
without a new provider class per vendor.

Deliberate posture:

- ``KAAVAL_REMOTE_BASE_URL`` has NO default. A remote tier is somebody's
  bill and somebody's data path; it must be named explicitly, never
  inherited from a default.
- Creation through the factory requires ``confirm_spend=True`` exactly
  like Fireworks. Whether a given endpoint bills per token is not
  something Kaaval can know, so it treats every non-mock remote as paid.
- Pricing is configured, never inferred: cost fields come from
  ``KAAVAL_REMOTE_COST_PER_*_TOKEN`` env values and are recorded with the
  ``configured`` source tag downstream, not presented as an invoice.

The request/verify path is byte-identical to the vLLM/Ollama providers —
one OpenAI-compatible client, different labels and defaults.
"""

import os
from typing import Literal, Mapping, Optional

import requests

from ..contracts import TaskContract
from ..models import ModelResponse
from .vllm import VllmConfig, VllmError, VllmProvider, _parse_bool

DEFAULT_HARDWARE_TARGET = "openai-compatible-remote"


class OpenAICompatibleError(VllmError):
    """Remote OpenAI-compatible endpoint call failed without exposing credentials."""


def openai_compatible_config_from_env(
    env: Optional[Mapping[str, str]] = None,
) -> VllmConfig:
    env = os.environ if env is None else env
    model = env.get("KAAVAL_REMOTE_MODEL", "").strip()
    if not model:
        raise ValueError(
            "KAAVAL_REMOTE_MODEL is not set; set it to the exact model id "
            "served by your OpenAI-compatible endpoint"
        )
    base_url = env.get("KAAVAL_REMOTE_BASE_URL", "").strip()
    if not base_url:
        raise ValueError(
            "KAAVAL_REMOTE_BASE_URL is not set; a remote tier must be named "
            "explicitly (e.g. https://api.openai.com/v1) — there is no "
            "default remote endpoint"
        )
    return VllmConfig(
        model=model,
        base_url=base_url.rstrip("/"),
        timeout_seconds=float(env.get("KAAVAL_REMOTE_TIMEOUT_SECONDS", "120")),
        api_key=env.get("KAAVAL_REMOTE_API_KEY", "").strip(),
        # vLLM engine-serving knobs do not apply to an arbitrary remote
        # endpoint; record them empty rather than inheriting defaults.
        dtype="",
        kv_cache_dtype="",
        enable_prefix_caching=False,
        gpu_memory_utilization=0.0,
        tensor_parallel_size=1,
        structured_outputs=_parse_bool(
            env.get("KAAVAL_REMOTE_STRUCTURED_OUTPUTS", ""), True
        ),
        hardware_target=env.get(
            "KAAVAL_REMOTE_HARDWARE_TARGET", DEFAULT_HARDWARE_TARGET
        ),
        cost_per_prompt_token=float(
            env.get("KAAVAL_REMOTE_COST_PER_PROMPT_TOKEN", "0")
        ),
        cost_per_completion_token=float(
            env.get("KAAVAL_REMOTE_COST_PER_COMPLETION_TOKEN", "0")
        ),
        # Never inferred from the model id: recorded only if declared.
        model_family=env.get("KAAVAL_REMOTE_MODEL_FAMILY", ""),
    )


class OpenAICompatibleProvider(VllmProvider):
    label = "openai_compatible"

    def __init__(
        self,
        config: Optional[VllmConfig] = None,
        session: Optional[requests.Session] = None,
        tier: Literal["local", "remote"] = "remote",
    ):
        super().__init__(
            config or openai_compatible_config_from_env(),
            session=session,
            tier=tier,
            provider_name="openai_compatible",
        )

    def generate(
        self, request_id: str, task_input: str, contract: TaskContract
    ) -> ModelResponse:
        try:
            return super().generate(request_id, task_input, contract)
        except VllmError as exc:
            raise OpenAICompatibleError(str(exc)) from exc
