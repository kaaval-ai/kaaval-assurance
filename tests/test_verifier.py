import json

from kaaval_assurance.contracts import get_contract
from kaaval_assurance.models import ModelResponse
from kaaval_assurance.verifier import verify

SEVERITY = get_contract("telecom.severity_classification")
EXTRACTION = get_contract("telecom.component_extraction")


def response_with(payload) -> ModelResponse:
    raw = payload if isinstance(payload, str) else json.dumps(payload)
    try:
        parsed = json.loads(raw)
        if not isinstance(parsed, dict):
            parsed = None
    except json.JSONDecodeError:
        parsed = None
    return ModelResponse(
        request_id="t",
        provider="mock",
        model_id="m",
        tier="local",
        raw_text=raw,
        parsed=parsed,
    )


def test_valid_payload_passes():
    result = verify(
        response_with(
            {"severity": "P1", "confidence": 0.9, "rationale": "full outage"}
        ),
        SEVERITY,
    )
    assert result.passed
    assert result.failures == []
    assert result.checks_run > 1


def test_unparseable_fails_json_parse():
    result = verify(response_with("not json at all {"), SEVERITY)
    assert not result.passed
    assert result.failures == ["json_parse"]


def test_missing_required_field():
    result = verify(response_with({"severity": "P1", "confidence": 0.9}), SEVERITY)
    assert not result.passed
    assert "required:rationale" in result.failures


def test_bad_enum_value():
    result = verify(
        response_with(
            {"severity": "CRITICAL", "confidence": 0.9, "rationale": "x"}
        ),
        SEVERITY,
    )
    assert not result.passed
    assert "enum:severity" in result.failures


def test_out_of_range_confidence():
    result = verify(
        response_with({"severity": "P1", "confidence": 1.5, "rationale": "x"}),
        SEVERITY,
    )
    assert not result.passed
    assert "range:confidence" in result.failures


def test_wrong_type():
    result = verify(
        response_with({"severity": "P1", "confidence": "high", "rationale": "x"}),
        SEVERITY,
    )
    assert not result.passed
    assert "type:confidence" in result.failures


def test_min_items_on_array():
    result = verify(
        response_with({"components": [], "primary_component": "core-router"}),
        EXTRACTION,
    )
    assert not result.passed
    assert "min_items:components" in result.failures


def test_multiple_failures_collected():
    result = verify(response_with({"severity": "WRONG"}), SEVERITY)
    assert not result.passed
    assert "enum:severity" in result.failures
    assert "required:confidence" in result.failures
    assert "required:rationale" in result.failures
