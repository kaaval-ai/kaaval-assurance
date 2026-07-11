"""Task contract model: the unit of agreement between caller and model.

A contract declares the expected output shape for a task category. Layer 1
verifies responses against it deterministically; Layer 3 (later) attacks
accepted answers against its semantic_intent.
"""

from typing import Literal, Optional

from pydantic import BaseModel, Field

FieldType = Literal["string", "number", "integer", "boolean", "array", "object"]


class FieldSpec(BaseModel):
    """One expected field in the contract output schema."""

    name: str
    type: FieldType
    required: bool = True
    enum: Optional[list[str]] = None  # allowed values (string fields)
    min_value: Optional[float] = None  # numeric range (number/integer)
    max_value: Optional[float] = None
    min_items: Optional[int] = None  # array length floor


class GroundingRule(BaseModel):
    """A deterministic content-aware Layer 1 check.

    When every phrase in required_input_phrases is present (case-insensitive)
    in the task input, the rule is triggered: output_field must then hold one
    of allowed_values, or verification fails with `grounding:<id>`. Pure
    string matching — no LLM calls, no fuzzy matching, no hidden heuristics.
    """

    id: str
    required_input_phrases: list[str]
    output_field: str
    allowed_values: list[str]
    description: str


class TaskContract(BaseModel):
    contract_id: str
    version: str
    category: str
    description: str
    # Layer 3 seam: what the answer must get right semantically, beyond shape.
    # The adversarial challenger attacks accepted answers against this text.
    semantic_intent: str
    fields: list[FieldSpec] = Field(min_length=1)
    # Layer 1 content-aware seam: explicit deterministic rules, not hidden
    # semantic intelligence. Empty by default; telecom is the reference pack.
    grounding_rules: list[GroundingRule] = Field(default_factory=list)

    @property
    def key(self) -> tuple[str, str]:
        return (self.contract_id, self.version)
