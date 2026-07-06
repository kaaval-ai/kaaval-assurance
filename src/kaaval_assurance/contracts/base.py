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


class TaskContract(BaseModel):
    contract_id: str
    version: str
    category: str
    description: str
    # Layer 3 seam: what the answer must get right semantically, beyond shape.
    # The adversarial challenger attacks accepted answers against this text.
    semantic_intent: str
    fields: list[FieldSpec] = Field(min_length=1)

    @property
    def key(self) -> tuple[str, str]:
        return (self.contract_id, self.version)
