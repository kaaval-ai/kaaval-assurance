"""Provider factory: explicit, telemetry-visible provider switching.

Names map to tiers:
    local:  mock | ollama | vllm
    remote: mock | fireworks

Fireworks creation requires confirm_spend=True — callers (CLI flag, UI
checkbox) must make credit spend an explicit decision, never a default.
"""

import os
from typing import Mapping, Optional

from .base import Provider
from .fireworks import FireworksConfig, FireworksProvider
from .mock import MockProvider
from .ollama import OllamaProvider, ollama_config_from_env
from .vllm import VllmConfig, VllmProvider

LOCAL_PROVIDERS = ("mock", "ollama", "vllm")
REMOTE_PROVIDERS = ("mock", "fireworks")


class SpendConfirmationRequired(RuntimeError):
    """Raised when a paid provider is requested without explicit confirmation."""


def create_local_provider(
    name: str,
    env: Optional[Mapping[str, str]] = None,
    session=None,
    failure_mode: Optional[str] = None,
    failure_rate: float = 0.0,
    seed: int = 0,
) -> Provider:
    env = os.environ if env is None else env
    if name == "mock":
        return MockProvider(
            tier="local",
            failure_mode=failure_mode,
            failure_rate=failure_rate,
            seed=seed,
        )
    if failure_mode is not None:
        raise ValueError("failure injection is supported by the mock local provider only")
    if name == "ollama":
        return OllamaProvider(ollama_config_from_env(env), session=session)
    if name == "vllm":
        return VllmProvider(VllmConfig.from_env(env), session=session)
    raise ValueError(f"unknown local provider {name!r}; expected one of {LOCAL_PROVIDERS}")


def create_remote_provider(
    name: str,
    env: Optional[Mapping[str, str]] = None,
    session=None,
    confirm_spend: bool = False,
) -> Provider:
    env = os.environ if env is None else env
    if name == "mock":
        return MockProvider(tier="remote", model_id="mock-remote-strong")
    if name == "fireworks":
        if not confirm_spend:
            raise SpendConfirmationRequired(
                "fireworks spends credits; pass explicit confirmation "
                "(CLI flag or UI checkbox) to enable it"
            )
        return FireworksProvider(FireworksConfig.from_env(env), session=session)
    raise ValueError(
        f"unknown remote provider {name!r}; expected one of {REMOTE_PROVIDERS}"
    )
