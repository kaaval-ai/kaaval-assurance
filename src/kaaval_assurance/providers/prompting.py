"""Contract-aware prompt construction shared by HTTP chat providers.

Both the local vLLM Gemma tier and the Fireworks escalation tier use the
same strict JSON-only instruction built from the task contract, so responses
from either tier face identical Layer-1 expectations.
"""

from ..contracts import FieldSpec, TaskContract


def _field_rule(spec: FieldSpec) -> str:
    rule = f'- "{spec.name}" ({spec.type}, {"required" if spec.required else "optional"})'
    parts = []
    if spec.enum:
        parts.append("allowed values: " + ", ".join(f'"{v}"' for v in spec.enum))
    if spec.min_value is not None:
        parts.append(f"minimum {spec.min_value}")
    if spec.max_value is not None:
        parts.append(f"maximum {spec.max_value}")
    if spec.min_items is not None:
        parts.append(f"at least {spec.min_items} items")
    if parts:
        rule += ": " + "; ".join(parts)
    return rule


def contract_field_rules(contract: TaskContract) -> list[str]:
    """One rule line per contract field; shared by generation and audit prompts."""
    return [_field_rule(spec) for spec in contract.fields]


def build_contract_prompt(contract: TaskContract) -> str:
    """Strict, contract-aware system instruction for JSON-only output."""
    lines = [
        f"Task: {contract.description}",
        "Respond with ONLY a JSON object. No markdown, no code fences, no "
        "explanation, no prose before or after the JSON.",
        "The JSON object must contain exactly these fields:",
    ]
    lines.extend(_field_rule(spec) for spec in contract.fields)
    lines.append("Enum fields must use one of the allowed values exactly.")
    lines.append("Numeric fields must respect the stated ranges.")
    return "\n".join(lines)
