"""MockProvider: deterministic responses with controllable failure injection.

Runs with zero cloud access — the entire Jul 5 end-to-end path and the later
mock-mode demo depend on this. Failure modes exist so tests and the shift
simulation can exercise the verifier and escalation path deterministically.
"""

import json
import random
from typing import Optional

from ..contracts import FieldSpec, TaskContract
from ..models import ModelResponse
from .base import Provider

# Supported injectable failures.
FAILURE_MODES = (
    "missing_field",
    "bad_enum",
    "out_of_range",
    "unparseable",
    # Mock-only test/demo seam — never a real Gemma failure mode. Returns a
    # structurally and enum-valid but operationally under-severe P2 for
    # severity-classification contracts, so tests can exercise the Layer 1
    # deterministic grounding-rule engine (content-aware, not shape-based)
    # and the escalation/recovery path it triggers. No-op on contracts
    # without a "severity" field.
    "undersevere",
)


def _sample_value(spec: FieldSpec):
    if spec.enum:
        return spec.enum[0]
    if spec.type == "string":
        return f"mock {spec.name}"
    if spec.type == "number":
        lo = spec.min_value if spec.min_value is not None else 0.0
        hi = spec.max_value if spec.max_value is not None else lo + 1.0
        return (lo + hi) / 2
    if spec.type == "integer":
        return int(spec.min_value) if spec.min_value is not None else 1
    if spec.type == "boolean":
        return True
    if spec.type == "array":
        n = spec.min_items if spec.min_items else 1
        return [f"mock-{spec.name}-{i}" for i in range(n)]
    return {}


class MockProvider(Provider):
    def __init__(
        self,
        tier: str = "local",
        model_id: str = "mock-gemma-3-12b-it",
        failure_mode: Optional[str] = None,
        failure_rate: float = 0.0,
        seed: int = 0,
        provider_name: str = "mock",
    ):
        if failure_mode is not None and failure_mode not in FAILURE_MODES:
            raise ValueError(f"failure_mode must be one of {FAILURE_MODES}")
        self.provider_name = provider_name
        self.tier = tier
        self.model_id = model_id
        self.failure_mode = failure_mode
        self.failure_rate = failure_rate
        self._rng = random.Random(seed)

    def _should_fail(self) -> bool:
        if self.failure_mode is None:
            return False
        if self.failure_rate <= 0.0:
            return True  # failure_mode set, no rate: fail every time (tests)
        return self._rng.random() < self.failure_rate

    def _build_payload(self, contract: TaskContract, fail: bool) -> str:
        payload = {spec.name: _sample_value(spec) for spec in contract.fields}
        if not fail:
            return json.dumps(payload)
        if self.failure_mode == "unparseable":
            return "I think the answer is probably fine {not json"
        if self.failure_mode == "missing_field":
            required = [s.name for s in contract.fields if s.required]
            if required:
                payload.pop(required[0])
        elif self.failure_mode == "bad_enum":
            for spec in contract.fields:
                if spec.enum:
                    payload[spec.name] = "NOT_IN_ENUM"
                    break
        elif self.failure_mode == "out_of_range":
            for spec in contract.fields:
                if spec.max_value is not None:
                    payload[spec.name] = spec.max_value + 1000
                    break
        elif self.failure_mode == "undersevere":
            for spec in contract.fields:
                if spec.name == "severity" and spec.enum and "P2" in spec.enum:
                    payload[spec.name] = "P2"
                    break
        return json.dumps(payload)

    def generate(
        self, request_id: str, task_input: str, contract: TaskContract
    ) -> ModelResponse:
        raw_text = self._build_payload(contract, fail=self._should_fail())
        try:
            parsed = json.loads(raw_text)
            if not isinstance(parsed, dict):
                parsed = None
        except json.JSONDecodeError:
            parsed = None
        return ModelResponse(
            request_id=request_id,
            provider=self.provider_name,
            model_id=self.model_id,
            tier=self.tier,  # type: ignore[arg-type]
            raw_text=raw_text,
            parsed=parsed,
            prompt_tokens=len(task_input.split()),
            completion_tokens=len(raw_text.split()),
            latency_ms=5.0 if self.tier == "local" else 50.0,
            cost_usd=0.0 if self.tier == "local" else 0.001,
        )
