"""Layer 1: deterministic contract verification.

Pure code, no model calls. Every check has a stable ID so trajectory rows,
Layer 2 trends, and repair hints can reference exactly what failed.

Check ID format:
    json_parse            response body was not a JSON object
    required:<field>      required field missing
    type:<field>          wrong JSON type
    enum:<field>          value outside allowed set
    range:<field>         numeric value outside [min_value, max_value]
    min_items:<field>     array shorter than minimum
"""

from .contracts import FieldSpec, TaskContract
from .models import ModelResponse, VerificationResult

_TYPE_CHECKS = {
    "string": lambda v: isinstance(v, str),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
    "array": lambda v: isinstance(v, list),
    "object": lambda v: isinstance(v, dict),
}


def _check_field(spec: FieldSpec, payload: dict) -> tuple[int, list[str]]:
    checks_run = 0
    failures: list[str] = []

    checks_run += 1
    if spec.name not in payload:
        if spec.required:
            failures.append(f"required:{spec.name}")
        return checks_run, failures

    value = payload[spec.name]

    checks_run += 1
    if not _TYPE_CHECKS[spec.type](value):
        failures.append(f"type:{spec.name}")
        return checks_run, failures  # downstream checks meaningless on wrong type

    if spec.enum is not None:
        checks_run += 1
        if value not in spec.enum:
            failures.append(f"enum:{spec.name}")

    if spec.min_value is not None or spec.max_value is not None:
        checks_run += 1
        if spec.min_value is not None and value < spec.min_value:
            failures.append(f"range:{spec.name}")
        elif spec.max_value is not None and value > spec.max_value:
            failures.append(f"range:{spec.name}")

    if spec.min_items is not None:
        checks_run += 1
        if len(value) < spec.min_items:
            failures.append(f"min_items:{spec.name}")

    return checks_run, failures


def verify(response: ModelResponse, contract: TaskContract) -> VerificationResult:
    """Run every deterministic contract check against one response."""
    checks_run = 1  # json_parse
    if response.parsed is None:
        return VerificationResult(
            passed=False, checks_run=checks_run, failures=["json_parse"]
        )

    failures: list[str] = []
    for spec in contract.fields:
        ran, failed = _check_field(spec, response.parsed)
        checks_run += ran
        failures.extend(failed)

    return VerificationResult(
        passed=not failures, checks_run=checks_run, failures=failures
    )
