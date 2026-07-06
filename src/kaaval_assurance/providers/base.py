"""Provider interface: anything that can turn (input, contract) into a response.

Implementations planned:
- MockProvider (Jul 5): deterministic, zero cloud access.
- vLLM/ROCm Gemma on AMD Instinct MI300X (Jul 8): local tier.
- Fireworks (Jul 7): remote escalation + Layer 3 challenger tier.
"""

from abc import ABC, abstractmethod

from ..contracts import TaskContract
from ..models import ModelResponse


class Provider(ABC):
    """One model tier the router can send a request to."""

    provider_name: str
    model_id: str
    tier: str  # "local" | "remote"

    @abstractmethod
    def generate(
        self, request_id: str, task_input: str, contract: TaskContract
    ) -> ModelResponse:
        """Produce one response for the task input under the given contract."""
        raise NotImplementedError
