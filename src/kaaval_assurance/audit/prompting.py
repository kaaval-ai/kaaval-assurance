"""Challenger prompt construction, cache-aware by design.

The system prompt is a stable prefix: output schema, scoring policy, contract
rules, and semantic intent — identical for every audit of the same contract.
Variable content (task input, accepted answer) arrives only in the user
message. This layout is designed to benefit from vLLM automatic prefix
caching and Fireworks prompt cache keys when available; no cache-hit claims
are made without measurement.

The prompt must not presume failure: the challenger is told to return pass
with an empty violations list when no violation is supported by evidence.
"""

import json

from ..contracts import TaskContract
from ..providers.prompting import contract_field_rules

AUDIT_OUTPUT_SCHEMA = (
    '{"result": "pass" | "fail", "violations": [{"check_id": string, '
    '"severity": "minor" | "major" | "critical", "field": string | null, '
    '"description": string, "evidence": string, "repair_hint": string | null}]}'
)


def build_audit_system_prompt(contract: TaskContract) -> str:
    """Stable per-contract prefix: schema, policy, contract rules, intent."""
    lines = [
        "You audit an accepted answer against its task contract. Report only "
        "violations supported by evidence from the task input or the answer.",
        "Respond with ONLY a JSON object matching this schema exactly. "
        "No markdown, no code fences, no prose:",
        AUDIT_OUTPUT_SCHEMA,
        "Scoring policy:",
        '- "minor": marginal issues that do not change operational meaning',
        '- "major": wrong or missing content that changes operational meaning',
        '- "critical": fabricated, unsupported, or operationally dangerous content',
        "- every violation must include an evidence quote from the task input "
        "or the answer",
        "- repair_hint, when present, must be phrased as verification guidance "
        '(for example "Verify the severity label against the stated '
        'operational impact"), never as an asserted failure',
        "Contract rules the answer already passed deterministic checks for:",
    ]
    lines.extend(contract_field_rules(contract))
    lines.append(f"Semantic intent to audit against: {contract.semantic_intent}")
    lines.append(
        "Verify these specifically. If no violation is supported by the "
        "evidence, return pass with an empty violations list."
    )
    return "\n".join(lines)


def build_audit_user_prompt(task_input: str, accepted_answer: dict) -> str:
    """Variable suffix: the specific case under audit."""
    return (
        f"Task input:\n{task_input}\n\n"
        f"Accepted answer JSON:\n{json.dumps(accepted_answer, sort_keys=True)}"
    )
