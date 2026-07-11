import json

import pytest

from kaaval_assurance.eval import load_dataset, run_eval
from kaaval_assurance.eval.cli import main as cli_main
from kaaval_assurance.pipeline import AssurancePipeline
from kaaval_assurance.providers import MockProvider
from kaaval_assurance.router import Router
from kaaval_assurance.trajectory import TrajectoryStore

GOLD = "data/eval/telecom_gold.jsonl"


@pytest.fixture()
def store():
    s = TrajectoryStore(":memory:")
    yield s
    s.close()


def make_pipeline(store, local_failure=None):
    return AssurancePipeline(
        router=Router(),
        local_provider=MockProvider(tier="local", failure_mode=local_failure),
        remote_provider=MockProvider(tier="remote", model_id="mock-remote-strong"),
        store=store,
    )


def test_healthy_run_all_pass(store):
    cases = load_dataset(GOLD)
    report = run_eval(make_pipeline(store), cases)

    assert report.n_cases == 16
    assert all(r.passed for r in report.results)
    assert store.count() == 16  # one local attempt per case, all written

    m = report.metrics
    assert m.requests == 16
    assert m.pass_rate == 1.0
    assert m.escalation_rate == 0.0
    assert m.failure_counts == {}
    assert set(m.by_category) == {
        "severity_classification",
        "component_extraction",
        "incident_summary",
        "next_action_recommendation",
    }
    for cat in m.by_category.values():
        assert cat.ewma_drift == 0.0
        assert cat.local_pass_rate == 1.0


def test_eval_request_ids_replayable(store):
    cases = load_dataset(GOLD)
    report = run_eval(make_pipeline(store), cases)
    rows = store.rows_for_request(f"eval-{report.run_id}-sev-001")
    assert len(rows) == 1
    assert rows[0].task_input.startswith("Core router CR-04")


def test_persistent_db_reuse_does_not_contaminate_metrics(tmp_path):
    db = tmp_path / "persistent.db"

    # Run 1: degraded local tier -> escalations, failures, drift.
    store1 = TrajectoryStore(db)
    try:
        report1 = run_eval(
            make_pipeline(store1, local_failure="bad_enum"), load_dataset(GOLD)
        )
    finally:
        store1.close()
    assert report1.metrics.escalation_rate > 0.0
    assert report1.metrics.failure_counts != {}

    # Run 2: healthy, same DB file. Prior-run rows must not leak in.
    store2 = TrajectoryStore(db)
    try:
        report2 = run_eval(make_pipeline(store2), load_dataset(GOLD))
        assert store2.count() == 24 + 16  # both runs persisted in the DB
    finally:
        store2.close()

    assert report2.run_id != report1.run_id
    m = report2.metrics
    assert m.requests == 16
    assert m.attempts == 16  # would be >16 if run-1 rows leaked in
    assert m.escalation_rate == 0.0
    assert m.failure_counts == {}
    for cat in m.by_category.values():
        assert cat.ewma_drift == 0.0


def test_degraded_local_tier_shows_drift_and_escalation(store):
    # bad_enum only corrupts contracts that have enum fields:
    # severity_classification (severity) and next_action_recommendation (urgency).
    cases = load_dataset(GOLD)
    report = run_eval(make_pipeline(store, local_failure="bad_enum"), cases)

    m = report.metrics
    assert m.pass_rate == 1.0  # remote rescues every failure
    assert m.escalation_rate == pytest.approx(8 / 16)
    assert m.attempts == 24  # 16 local + 8 remote
    # sev-001 and act-001 also trip the new deterministic grounding rules
    # (regional-outage / no-redundancy phrases both present) alongside their
    # enum failure, since bad_enum's replacement value satisfies neither the
    # field enum nor the rule's allowed_values.
    assert m.failure_counts == {
        "enum:severity": 4,
        "enum:urgency": 4,
        "grounding:regional_outage_requires_p1": 1,
        "grounding:no_redundancy_requires_immediate": 1,
    }

    assert m.by_category["severity_classification"].ewma_drift > 0.9
    assert m.by_category["next_action_recommendation"].ewma_drift > 0.9
    assert m.by_category["incident_summary"].ewma_drift == 0.0
    assert m.by_category["component_extraction"].ewma_drift == 0.0

    # remote attempts cost money; cost per verified answer reflects rescue cost
    assert m.total_cost_usd == pytest.approx(8 * 0.001)
    assert m.cost_per_verified_usd == pytest.approx(8 * 0.001 / 16)


def test_cli_json_output(capsys):
    rc = cli_main(["--dataset", GOLD, "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["n_cases"] == 16
    assert payload["metrics"]["pass_rate"] == 1.0


def test_cli_text_output_with_injected_failures(capsys):
    rc = cli_main(["--dataset", GOLD, "--failure-mode", "bad_enum"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "pass rate 100.0%" in out
    assert "escalation rate 50.0%" in out
    assert "enum:severity=4" in out
    assert "severity_classification" in out


def test_cli_missing_dataset_errors(capsys):
    rc = cli_main(["--dataset", "does/not/exist.jsonl"])
    assert rc == 2
    assert "error:" in capsys.readouterr().err


def test_cli_persists_trajectory_db(tmp_path):
    db = tmp_path / "run.db"
    rc = cli_main(["--dataset", GOLD, "--db", str(db)])
    assert rc == 0
    store = TrajectoryStore(db)
    try:
        assert store.count() == 16
    finally:
        store.close()


def test_force_remote_eval_replays_fully_remote(capsys, tmp_path):
    db = tmp_path / "run.db"
    rc = cli_main([
        "--dataset", GOLD,
        "--db", str(db),
        "--force-remote",
        "--remote-provider", "mock",
        "--json"
    ])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["n_cases"] == 16
    assert payload["metrics"]["attempts"] == 16
    assert payload["metrics"]["escalation_rate"] == 0.0
    assert payload["metrics"]["pass_rate"] == 1.0
    
    store = TrajectoryStore(db)
    try:
        rows = store.all_rows()
        assert len(rows) == 16
        assert all(r.tier == "remote" for r in rows)
    finally:
        store.close()
        
    for res in payload["results"]:
        assert "explicit always-remote baseline" in res["routing_reason"]


def test_force_remote_closed_loop_incompatible(capsys):
    rc = cli_main(["--force-remote", "--closed-loop-demo"])
    assert rc == 2
    assert "incompatible" in capsys.readouterr().err

