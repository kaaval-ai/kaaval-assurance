"""Tier-0 SDK semantics: shadow never blocks, enforce fails closed on answers,
infra failures pass through unchanged, every call leaves a receipt.
"""

import json

import pytest

from kaaval_assurance.sdk import Decision, Kaaval, NoSafeAnswer
from kaaval_assurance.trajectory import TrajectoryStore

REFUND = "support.refund_decision"

GOOD_ANSWER = json.dumps(
    {
        "decision": "approve",
        "refund_amount_usd": 120.0,
        "justification": "duplicate charge confirmed",
    }
)
OVER_CAP_ANSWER = json.dumps(
    {
        "decision": "approve",
        "refund_amount_usd": 1500.0,
        "justification": "customer is upset",
    }
)
TASK = "Customer: charged twice for order #88231, refund the duplicate $120."


class TestShadowMode:
    def test_conformant_answer_passes_through_untouched(self):
        with Kaaval(mode="shadow") as kaaval:

            @kaaval.assure(contract=REFUND)
            def decide(task_input: str) -> str:
                return GOOD_ANSWER

            assert decide(TASK) == GOOD_ANSWER
            d = kaaval.last_decision()
            assert d is not None and d.conformant and d.checks_run > 0

    def test_violating_answer_STILL_passes_through(self):
        # Shadow's whole contract: observe, never block.
        with Kaaval(mode="shadow") as kaaval:

            @kaaval.assure(contract=REFUND)
            def decide(task_input: str) -> str:
                return OVER_CAP_ANSWER

            assert decide(TASK) == OVER_CAP_ANSWER
            d = kaaval.last_decision()
            assert d is not None and not d.conformant
            assert "range:refund_amount_usd" in d.failures

    def test_violation_is_receipted(self):
        store = TrajectoryStore(":memory:")
        try:
            kaaval = Kaaval(mode="shadow", receipts=store)

            @kaaval.assure(contract=REFUND)
            def decide(task_input: str) -> str:
                return OVER_CAP_ANSWER

            decide(TASK)
            rows = store.all_rows()
            assert len(rows) == 1
            row = rows[0]
            assert not row.verifier_passed
            assert "range:refund_amount_usd" in row.verifier_failures
            assert row.task_input == TASK
            assert row.raw_text == OVER_CAP_ANSWER  # verbatim, replayable
            assert row.contract_id == REFUND
        finally:
            store.close()


class TestEnforceMode:
    def test_conformant_answer_returned(self):
        with Kaaval(mode="enforce") as kaaval:

            @kaaval.assure(contract=REFUND)
            def decide(task_input: str) -> str:
                return GOOD_ANSWER

            assert decide(TASK) == GOOD_ANSWER

    def test_violation_raises_typed_failure(self):
        with Kaaval(mode="enforce") as kaaval:

            @kaaval.assure(contract=REFUND)
            def decide(task_input: str) -> str:
                return OVER_CAP_ANSWER

            with pytest.raises(NoSafeAnswer) as exc_info:
                decide(TASK)
            err = exc_info.value
            assert err.contract_id == REFUND
            assert "range:refund_amount_usd" in err.failures
            assert err.receipt_id.startswith("sdk-")

    def test_grounding_rules_fire_with_task_input(self):
        angry = (
            "Customer: your outage cost my agency a client worth $12,000. "
            "I expect compensation of at least $2,500 or we churn."
        )
        capped_but_ungrounded = json.dumps(
            {
                "decision": "approve",
                "refund_amount_usd": 400.0,
                "justification": "goodwill",
            }
        )
        with Kaaval(mode="enforce") as kaaval:

            @kaaval.assure(contract=REFUND)
            def decide(task_input: str) -> str:
                return capped_but_ungrounded

            with pytest.raises(NoSafeAnswer) as exc_info:
                decide(angry)
            assert (
                "grounding:consequential_damages_requires_human"
                in exc_info.value.failures
            )


class TestInfraFailures:
    def test_wrapped_exception_reraised_unchanged_and_receipted(self):
        store = TrajectoryStore(":memory:")
        try:
            kaaval = Kaaval(mode="enforce", receipts=store)

            @kaaval.assure(contract=REFUND)
            def decide(task_input: str) -> str:
                raise ConnectionError("provider down")

            with pytest.raises(ConnectionError):
                decide(TASK)

            rows = store.all_rows()
            assert len(rows) == 1
            assert rows[0].attempt_status == "provider_error"
            assert rows[0].error_type == "ConnectionError"
            assert rows[0].verifier_failures == ["transport:ConnectionError"]
            d = kaaval.last_decision()
            assert d is not None and d.attempt_status == "provider_error"
        finally:
            store.close()


class TestApiSurface:
    def test_unknown_contract_fails_at_decoration_time(self):
        kaaval = Kaaval()
        with pytest.raises(KeyError):

            @kaaval.assure(contract="does.not_exist")
            def decide(task_input: str) -> str:
                return "{}"

    def test_invalid_mode_rejected(self):
        with pytest.raises(ValueError):
            Kaaval(mode="audit")  # type: ignore[arg-type]

    def test_dict_return_values_supported(self):
        with Kaaval(mode="enforce") as kaaval:

            @kaaval.assure(contract=REFUND)
            def decide(task_input: str) -> dict:
                return json.loads(GOOD_ANSWER)

            result = decide(TASK)
            assert result["decision"] == "approve"

    def test_decision_dataclass_shape(self):
        with Kaaval(mode="shadow") as kaaval:

            @kaaval.assure(contract=REFUND)
            def decide(task_input: str) -> str:
                return GOOD_ANSWER

            decide(TASK)
            d = kaaval.last_decision()
            assert isinstance(d, Decision)
            assert d.mode == "shadow"
            assert d.contract_id == REFUND
            assert d.latency_ms >= 0
