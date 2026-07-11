"""Part B: deterministic content-aware Layer 1 grounding rules."""

import json

from kaaval_assurance.contracts import get_contract
from kaaval_assurance.models import ModelResponse
from kaaval_assurance.verifier import verify

SEVERITY = get_contract("telecom.severity_classification")
NEXT_ACTION = get_contract("telecom.next_action_recommendation")

REGIONAL_OUTAGE_INPUT = (
    "Core router CR-04 dropped all BGP sessions at 02:13; downstream OLT "
    "sites in region south lost upstream connectivity. Customer impact "
    "confirmed."
)
STANDARD_REDUNDANCY_LOSS_INPUT = (
    "Aggregation switch AGG-12 reports one of two uplinks down; traffic "
    "rerouted over the redundant path, utilization at 78%, no customer "
    "complaints."
)
NO_REDUNDANCY_INPUT = (
    "Core router CR-04 line card LC-3 suspected faulty after BGP flap "
    "outage; currently on failover to CR-05 with no redundancy remaining. "
    "40k subscribers on the failover path."
)


def response_with(payload) -> ModelResponse:
    raw = payload if isinstance(payload, str) else json.dumps(payload)
    try:
        parsed = json.loads(raw)
        if not isinstance(parsed, dict):
            parsed = None
    except json.JSONDecodeError:
        parsed = None
    return ModelResponse(
        request_id="t", provider="mock", model_id="m", tier="local",
        raw_text=raw, parsed=parsed,
    )


class TestRegionalOutageGrounding:
    def test_p2_for_regional_outage_fails_grounding(self):
        result = verify(
            response_with(
                {"severity": "P2", "confidence": 0.7, "rationale": "elevated risk"}
            ),
            SEVERITY,
            REGIONAL_OUTAGE_INPUT,
        )
        assert not result.passed
        assert "grounding:regional_outage_requires_p1" in result.failures

    def test_p1_for_regional_outage_passes(self):
        result = verify(
            response_with(
                {"severity": "P1", "confidence": 0.95, "rationale": "full outage"}
            ),
            SEVERITY,
            REGIONAL_OUTAGE_INPUT,
        )
        assert result.passed
        assert "grounding:regional_outage_requires_p1" not in result.failures

    def test_standard_redundancy_loss_does_not_trigger_regional_rule(self):
        result = verify(
            response_with(
                {"severity": "P2", "confidence": 0.8, "rationale": "redundancy lost"}
            ),
            SEVERITY,
            STANDARD_REDUNDANCY_LOSS_INPUT,
        )
        assert result.passed
        assert "grounding:regional_outage_requires_p1" not in result.failures

    def test_rule_never_triggers_on_default_empty_task_input(self):
        result = verify(
            response_with(
                {"severity": "P2", "confidence": 0.7, "rationale": "n/a"}
            ),
            SEVERITY,
        )
        assert result.passed  # backward-compatible default: no grounding evaluated


class TestNoRedundancyGrounding:
    def test_monitor_for_no_redundancy_fails_grounding(self):
        result = verify(
            response_with(
                {
                    "action": "watch the failover path",
                    "urgency": "monitor",
                    "justification": "seems stable",
                }
            ),
            NEXT_ACTION,
            NO_REDUNDANCY_INPUT,
        )
        assert not result.passed
        assert "grounding:no_redundancy_requires_immediate" in result.failures

    def test_immediate_for_no_redundancy_passes(self):
        result = verify(
            response_with(
                {
                    "action": "dispatch field engineering",
                    "urgency": "immediate",
                    "justification": "no redundancy remains",
                }
            ),
            NEXT_ACTION,
            NO_REDUNDANCY_INPUT,
        )
        assert result.passed
        assert "grounding:no_redundancy_requires_immediate" not in result.failures


class TestGroundingChecksRun:
    def test_triggered_rule_counted_in_checks_run(self):
        triggered = verify(
            response_with(
                {"severity": "P1", "confidence": 0.9, "rationale": "x"}
            ),
            SEVERITY,
            REGIONAL_OUTAGE_INPUT,
        )
        not_triggered = verify(
            response_with(
                {"severity": "P1", "confidence": 0.9, "rationale": "x"}
            ),
            SEVERITY,
            STANDARD_REDUNDANCY_LOSS_INPUT,
        )
        assert triggered.checks_run == not_triggered.checks_run + 1

    def test_missing_field_does_not_double_count_grounding(self):
        # required:severity already fails structurally; grounding must not
        # also fire (nothing to ground against).
        result = verify(
            response_with({"confidence": 0.9, "rationale": "x"}),
            SEVERITY,
            REGIONAL_OUTAGE_INPUT,
        )
        assert "required:severity" in result.failures
        assert not any(f.startswith("grounding:") for f in result.failures)
