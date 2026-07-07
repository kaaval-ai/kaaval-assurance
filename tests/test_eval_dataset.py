import pytest

from kaaval_assurance.eval import load_dataset

GOLD = "data/eval/telecom_gold.jsonl"


def test_gold_dataset_loads():
    cases = load_dataset(GOLD)
    assert len(cases) == 16
    ids = [c.case_id for c in cases]
    assert len(set(ids)) == 16


def test_gold_dataset_covers_all_four_contracts():
    cases = load_dataset(GOLD)
    by_contract = {}
    for c in cases:
        by_contract.setdefault(c.contract_id, []).append(c)
    assert set(by_contract) == {
        "telecom.severity_classification",
        "telecom.component_extraction",
        "telecom.incident_summary",
        "telecom.next_action_recommendation",
    }
    for contract_id, group in by_contract.items():
        assert len(group) == 4, contract_id


def test_gold_answers_present_for_layer3_calibration_seam():
    for c in load_dataset(GOLD):
        assert c.gold_answer, c.case_id
        assert c.task_input.strip()


def test_invalid_json_reports_line_number(tmp_path):
    p = tmp_path / "bad.jsonl"
    p.write_text('{"case_id": "a", "contract_id": "telecom.incident_summary", '
                 '"task_input": "x"}\n{not json\n')
    with pytest.raises(ValueError, match=r"bad\.jsonl:2.*invalid JSON"):
        load_dataset(p)


def test_missing_field_reports_line_number(tmp_path):
    p = tmp_path / "bad.jsonl"
    p.write_text('{"case_id": "a", "contract_id": "telecom.incident_summary"}\n')
    with pytest.raises(ValueError, match=r"bad\.jsonl:1.*invalid eval case"):
        load_dataset(p)


def test_duplicate_case_id_rejected(tmp_path):
    line = ('{"case_id": "dup", "contract_id": "telecom.incident_summary", '
            '"task_input": "x"}\n')
    p = tmp_path / "dup.jsonl"
    p.write_text(line + line)
    with pytest.raises(ValueError, match="duplicate case_id"):
        load_dataset(p)


def test_unknown_contract_rejected(tmp_path):
    p = tmp_path / "unknown.jsonl"
    p.write_text('{"case_id": "a", "contract_id": "telecom.nope", "task_input": "x"}\n')
    with pytest.raises(ValueError, match="unknown contract"):
        load_dataset(p)


def test_empty_dataset_rejected(tmp_path):
    p = tmp_path / "empty.jsonl"
    p.write_text("\n\n")
    with pytest.raises(ValueError, match="empty"):
        load_dataset(p)


def test_blank_lines_skipped(tmp_path):
    p = tmp_path / "gaps.jsonl"
    p.write_text('\n{"case_id": "a", "contract_id": "telecom.incident_summary", '
                 '"task_input": "x"}\n\n')
    assert len(load_dataset(p)) == 1
