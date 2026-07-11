"""Deterministic gold scoring for decision-critical contract fields.

Enum, numeric, boolean, and scalar-array fields can be compared reproducibly.
Unconstrained free text is left unscored rather than pretending exact string
equality measures semantic quality.
"""

from typing import Optional

from pydantic import BaseModel, Field

from ..contracts import TaskContract


class GoldScore(BaseModel):
    scored: bool
    correct: Optional[bool] = None
    compared_fields: list[str] = Field(default_factory=list)
    mismatches: list[str] = Field(default_factory=list)


def _normalized_array(value: list) -> Optional[list[str]]:
    if not all(isinstance(item, (str, int, float, bool)) for item in value):
        return None
    return sorted(str(item).strip().casefold() for item in value)


def score_against_gold(
    parsed: Optional[dict], gold: Optional[dict], contract: TaskContract
) -> GoldScore:
    """Compare only fields whose equality has deterministic task meaning."""
    if parsed is None or gold is None:
        return GoldScore(scored=False)

    compared: list[str] = []
    mismatches: list[str] = []
    specs = {field.name: field for field in contract.fields}

    for name, expected in gold.items():
        spec = specs.get(name)
        if spec is None:
            continue

        actual = parsed.get(name)
        comparable = False
        matches = False

        if spec.enum is not None:
            comparable = True
            matches = actual == expected
        elif spec.type in {"integer", "boolean"}:
            comparable = True
            matches = actual == expected
        elif spec.type == "number":
            comparable = True
            matches = (
                isinstance(actual, (int, float))
                and not isinstance(actual, bool)
                and isinstance(expected, (int, float))
                and not isinstance(expected, bool)
                and abs(float(actual) - float(expected)) <= 1e-6
            )
        elif (
            spec.type == "array"
            and isinstance(actual, list)
            and isinstance(expected, list)
        ):
            actual_normalized = _normalized_array(actual)
            expected_normalized = _normalized_array(expected)
            comparable = (
                actual_normalized is not None and expected_normalized is not None
            )
            matches = comparable and actual_normalized == expected_normalized

        if not comparable:
            continue
        compared.append(name)
        if not matches:
            mismatches.append(name)

    if not compared:
        return GoldScore(scored=False)
    return GoldScore(
        scored=True,
        correct=not mismatches,
        compared_fields=compared,
        mismatches=mismatches,
    )
