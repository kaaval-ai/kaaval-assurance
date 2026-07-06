import pytest

from kaaval_assurance.contracts import get_contract, list_contracts


def test_four_contracts_registered():
    contracts = list_contracts()
    assert len(contracts) == 4
    ids = {c.contract_id for c in contracts}
    assert ids == {
        "telecom.severity_classification",
        "telecom.component_extraction",
        "telecom.incident_summary",
        "telecom.next_action_recommendation",
    }


def test_every_contract_has_semantic_intent_and_fields():
    for c in list_contracts():
        assert c.semantic_intent.strip()
        assert c.fields
        assert c.version == "1.0"
        assert c.category


def test_lookup_by_id_and_version():
    c = get_contract("telecom.severity_classification", "1.0")
    assert c.category == "severity_classification"
    latest = get_contract("telecom.severity_classification")
    assert latest.version == "1.0"


def test_unknown_contract_raises():
    with pytest.raises(KeyError):
        get_contract("telecom.does_not_exist")
    with pytest.raises(KeyError):
        get_contract("telecom.severity_classification", "9.9")
