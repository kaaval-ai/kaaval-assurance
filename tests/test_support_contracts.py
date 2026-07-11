"""Generic customer-support domain: contracts, hard gold set, failure paths.

The support domain exists so the demo reads on scenarios any reviewer has
lived (ticket triage, refunds under a policy cap) rather than telecom jargon.
"""

import json

import pytest

from kaaval_assurance.contracts import get_contract, list_contracts
from kaaval_assurance.eval import load_dataset
from kaaval_assurance.models import ModelResponse
from kaaval_assurance.pipeline import AssurancePipeline
from kaaval_assurance.providers import MockProvider
from kaaval_assurance.router import Router
from kaaval_assurance.trajectory import TrajectoryStore
from kaaval_assurance.verifier import verify

HARD = "data/eval/support_hard.jsonl"


def response_for(payload: dict, contract_id: str) -> ModelResponse:
    raw = json.dumps(payload)
    return ModelResponse(
        request_id="gold-check",
        provider="test",
        model_id="test",
        tier="local",
        raw_text=raw,
        parsed=payload,
        prompt_tokens=1,
        completion_tokens=1,
        latency_ms=1.0,
        cost_usd=0.0,
    )


class TestSupportContracts:
    def test_registered_alongside_telecom(self):
        ids = {c.contract_id for c in list_contracts()}
        assert "support.ticket_triage" in ids
        assert "support.refund_decision" in ids
        assert "telecom.severity_classification" in ids  # nothing displaced

    def test_refund_policy_cap_is_a_contract_range(self):
        contract = get_contract("support.refund_decision")
        amount = next(f for f in contract.fields if f.name == "refund_amount_usd")
        assert amount.min_value == 0.0
        assert amount.max_value == 500.0

    def test_over_cap_refund_is_rejected_deterministically(self):
        contract = get_contract("support.refund_decision")
        over_cap = {
            "decision": "approve",
            "refund_amount_usd": 2500.0,
            "justification": "customer demanded compensation",
        }
        result = verify(response_for(over_cap, contract.contract_id), contract)
        assert not result.passed
        assert "range:refund_amount_usd" in result.failures


class TestSupportHardDataset:
    def test_loads_and_covers_both_categories(self):
        cases = load_dataset(HARD)
        assert len(cases) == 10
        categories = {get_contract(c.contract_id).category for c in cases}
        assert categories == {"ticket_triage", "refund_decision"}

    def test_every_gold_answer_passes_layer_1(self):
        for case in load_dataset(HARD):
            contract = get_contract(case.contract_id)
            assert case.gold_answer is not None, case.case_id
            result = verify(response_for(case.gold_answer, case.contract_id), contract)
            assert result.passed, f"{case.case_id}: {result.failures}"


class TestSupportFailurePaths:
    @pytest.fixture()
    def store(self):
        s = TrajectoryStore(":memory:")
        yield s
        s.close()

    def test_bad_enum_injection_escalates_and_recovers(self, store):
        pipeline = AssurancePipeline(
            router=Router(),
            local_provider=MockProvider(tier="local", failure_mode="bad_enum"),
            remote_provider=MockProvider(tier="remote", model_id="mock-remote-strong"),
            store=store,
        )
        result = pipeline.handle_request(
            "I was charged twice, refund the duplicate $129.99.",
            "support.refund_decision",
        )
        assert result.escalated
        assert result.verification.passed
        rows = store.rows_for_request(result.request_id)
        assert rows[0].verifier_failures == ["enum:decision"]
        assert rows[1].tier == "remote" and rows[1].verifier_passed

    def test_out_of_range_injection_fails_on_the_policy_cap(self, store):
        pipeline = AssurancePipeline(
            router=Router(),
            local_provider=MockProvider(tier="local", failure_mode="out_of_range"),
            remote_provider=MockProvider(tier="remote", model_id="mock-remote-strong"),
            store=store,
        )
        result = pipeline.handle_request(
            "Refund request for order #88231.", "support.refund_decision"
        )
        assert result.escalated
        rows = store.rows_for_request(result.request_id)
        assert rows[0].verifier_failures == ["range:refund_amount_usd"]
