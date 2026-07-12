from kaaval_assurance.contracts import get_contract
from kaaval_assurance.contracts.base import FieldSpec, TaskContract
from kaaval_assurance.eval.scoring import score_against_gold


def test_enum_and_number_fields_are_scored() -> None:
    contract = get_contract("telecom.severity_classification")
    score = score_against_gold(
        {"severity": "P2", "confidence": 0.5, "rationale": "free text"},
        {"severity": "P3", "confidence": 0.8, "rationale": "different"},
        contract,
    )

    assert score.scored
    assert score.correct is False
    assert score.compared_fields == ["severity", "confidence"]
    assert score.mismatches == ["severity", "confidence"]


def test_scalar_arrays_are_order_insensitive() -> None:
    contract = get_contract("telecom.component_extraction")
    score = score_against_gold(
        {"components": ["B", "a"], "primary_component": "free text"},
        {"components": ["A", "b"], "primary_component": "different"},
        contract,
    )

    assert score.correct is True
    assert score.compared_fields == ["components"]


def test_unconstrained_free_text_is_explicitly_unscored() -> None:
    contract = TaskContract(
        contract_id="test.free_text",
        version="1.0",
        category="test",
        description="test",
        semantic_intent="test",
        fields=[FieldSpec(name="answer", type="string")],
    )

    score = score_against_gold(
        {"answer": "one valid phrasing"},
        {"answer": "another valid phrasing"},
        contract,
    )

    assert score.scored is False
    assert score.correct is None
