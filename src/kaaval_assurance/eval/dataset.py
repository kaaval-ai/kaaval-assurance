"""Gold eval dataset loader (JSONL).

One case per line. gold_answer is a known-good contract output for the case:
unused by the mock eval loop today, required from Jul 7 as the calibration
set for Layer-3 challenger false-positive testing.
"""

import json
from pathlib import Path
from typing import Optional, Union

from pydantic import BaseModel, ValidationError

from ..contracts import get_contract


class EvalCase(BaseModel):
    case_id: str
    contract_id: str
    contract_version: Optional[str] = None
    task_input: str
    gold_answer: Optional[dict] = None


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
