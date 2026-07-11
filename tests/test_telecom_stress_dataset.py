"""Part C: hard operational stress set — data/eval/telecom_stress.jsonl."""

from kaaval_assurance.eval.dataset import load_dataset

STRESS = "data/eval/telecom_stress.jsonl"

REGIONAL_OUTAGE_PHRASES = [
    "all BGP sessions",
    "lost upstream connectivity",
    "customer impact",
]
NO_REDUNDANCY_PHRASES = ["no redundancy", "subscribers"]

CONTRACTS = {
    "telecom.severity_classification",
    "telecom.component_extraction",
    "telecom.incident_summary",
    "telecom.next_action_recommendation",
}


def _triggers(case, phrases):
    return all(p.lower() in case.task_input.lower() for p in phrases)


def test_exactly_twelve_cases():
    cases = load_dataset(STRESS)
    assert len(cases) == 12


def test_exactly_three_cases_per_contract():
    cases = load_dataset(STRESS)
    by_contract = {}
    for c in cases:
        by_contract.setdefault(c.contract_id, []).append(c)
    assert set(by_contract) == CONTRACTS
    for contract_id, group in by_contract.items():
        assert len(group) == 3, contract_id


def test_every_case_has_gold_answer():
    for c in load_dataset(STRESS):
        assert c.gold_answer, c.case_id


def test_every_case_has_at_least_one_stress_tag():
    for c in load_dataset(STRESS):
        assert c.stress_tags, c.case_id


def test_regional_outage_trigger_case_present_with_all_required_phrases():
    cases = load_dataset(STRESS)
    triggers = [c for c in cases if _triggers(c, REGIONAL_OUTAGE_PHRASES)]
    assert triggers
    assert any(c.gold_answer.get("severity") == "P1" for c in triggers)


def test_no_redundancy_trigger_case_present_with_all_required_phrases():
    cases = load_dataset(STRESS)
    triggers = [c for c in cases if _triggers(c, NO_REDUNDANCY_PHRASES)]
    assert triggers
    assert any(c.gold_answer.get("urgency") == "immediate" for c in triggers)


def test_default_workload_is_telecom():
    for c in load_dataset(STRESS):
        assert c.workload == "telecom"


def test_case_ids_unique_and_distinct_from_gold():
    stress_ids = {c.case_id for c in load_dataset(STRESS)}
    gold_ids = {c.case_id for c in load_dataset("data/eval/telecom_gold.jsonl")}
    assert len(stress_ids) == 12
    assert stress_ids.isdisjoint(gold_ids)


def test_existing_gold_dataset_unchanged():
    cases = load_dataset("data/eval/telecom_gold.jsonl")
    assert len(cases) == 16
