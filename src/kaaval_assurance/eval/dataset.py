"""Reference-answer eval dataset loader (JSONL).

Decision-critical fields in gold_answer are scored by the eval runner. The
complete answer also remains the Layer-3 calibration input. Free-text fields
are intentionally not scored by exact string equality.
"""

import json
from pathlib import Path
from typing import Optional, Union

from pydantic import BaseModel, Field, ValidationError

from ..contracts import get_contract


class EvalCase(BaseModel):
    case_id: str
    contract_id: str
    contract_version: Optional[str] = None
    task_input: str
    gold_answer: Optional[dict] = None
    # Which eval set this case belongs to (e.g. "telecom" gold vs. a harder
    # stress set). Defaults preserve every existing dataset unchanged.
    workload: str = "telecom"
    # Reusable stress-case labels (e.g. "distractor_quantity",
    # "negation_or_temporal_change"); empty for ordinary gold cases.
    stress_tags: list[str] = Field(default_factory=list)


def load_dataset(path: Union[str, Path]) -> list[EvalCase]:
    """Load and validate a JSONL eval dataset. Fails fast with line numbers."""
    path = Path(path)
    cases: list[EvalCase] = []
    seen_ids: set[str] = set()

    with path.open(encoding="utf-8") as f:
        for lineno, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as e:
                raise ValueError(f"{path}:{lineno}: invalid JSON: {e}") from e
            try:
                case = EvalCase.model_validate(payload)
            except ValidationError as e:
                raise ValueError(f"{path}:{lineno}: invalid eval case: {e}") from e

            if case.case_id in seen_ids:
                raise ValueError(f"{path}:{lineno}: duplicate case_id {case.case_id!r}")
            seen_ids.add(case.case_id)

            try:
                get_contract(case.contract_id, case.contract_version)
            except KeyError as e:
                raise ValueError(
                    f"{path}:{lineno}: case {case.case_id!r} references "
                    f"unknown contract {case.contract_id!r}"
                ) from e

            cases.append(case)

    if not cases:
        raise ValueError(f"{path}: dataset is empty")
    return cases
