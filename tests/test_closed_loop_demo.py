import json

import pytest

from kaaval_assurance.eval import load_dataset
from kaaval_assurance.eval.cli import main as cli_main
from kaaval_assurance.eval.closed_loop import run_closed_loop_demo
from kaaval_assurance.providers import MockProvider
from kaaval_assurance.trajectory import TrajectoryStore

GOLD = "data/eval/telecom_gold.jsonl"
AFFECTED = {"severity_classification", "next_action_recommendation"}  # enum-bearing
UNAFFECTED = {"component_extraction", "incident_summary"}


@pytest.fixture()
def demo():
    store = TrajectoryStore(":memory:")
    try:
        yield run_closed_loop_demo(
            load_dataset(GOLD),
            store,
            MockProvider(tier="remote", model_id="mock-remote-strong"),
            failure_mode="bad_enum",
            failure_rate=1.0,
        )
    finally:
        store.close()


def test_phase_a_healthy_baseline(demo):
    m = demo.phase_a.metrics
    assert m.pass_rate == 1.0
    assert m.escalation_rate == 0.0
    assert m.preroute_remote_rate == 0.0
    for cat in m.by_category.values():
        assert cat.ewma_drift == 0.0


def test_phase_b_drift_rises_only_in_affected_categories(demo):
    m = demo.phase_b.metrics
    assert m.pass_rate == 1.0  # escalation rescues every failure
    assert m.escalation_rate == pytest.approx(0.5)
    for name in AFFECTED:
        assert m.by_category[name].ewma_drift == 1.0
        assert m.by_category[name].local_pass_rate == 0.0
    for name in UNAFFECTED:
        assert m.by_category[name].ewma_drift == 0.0
        assert m.by_category[name].local_pass_rate == 1.0


def test_policy_tightens_only_affected_categories(demo):
    for name in AFFECTED:
        assert demo.policy_after_b[name].action == "force_remote"
        assert demo.policy_after_b[name].threshold == 1.0
    for name in UNAFFECTED:
        assert demo.policy_after_b[name].action == "local_first"
        assert demo.policy_after_b[name].threshold == 0.0


def test_phase_c_preroutes_affected_categories_only(demo):
    m = demo.phase_c.metrics
    assert m.pass_rate == 1.0  # quality recovered
    for name in AFFECTED:
        cat = m.by_category[name]
        assert cat.preroute_remote_rate == 1.0
        assert cat.escalation_rate == 0.0  # no failed local attempt needed
    for name in UNAFFECTED:
        cat = m.by_category[name]
        assert cat.preroute_remote_rate == 0.0
        assert cat.local_pass_rate == 1.0


def test_phase_c_cost_per_verified_rises_with_quality_held(demo):
    a, c = demo.phase_a.metrics, demo.phase_c.metrics
    assert a.cost_per_verified_usd == 0.0  # all-local baseline
    assert c.cost_per_verified_usd > 0.0  # remote tier earns the affected traffic
    assert c.pass_rate == 1.0
    # adapted routing verifies first-time: fewer attempts than phase B
    assert c.attempts < demo.phase_b.metrics.attempts


def test_phase_c_routing_reasons_show_drift_influence(demo):
    prerouted = [
        r for r in demo.phase_c.results
        if r.category in AFFECTED
    ]
    assert prerouted
    for r in prerouted:
        assert "forces remote tier" in r.routing_reason
        assert "ewma drift 1.00" in r.routing_reason
    healthy = [r for r in demo.phase_c.results if r.category in UNAFFECTED]
    for r in healthy:
        assert "healthy" in r.routing_reason


def test_demo_is_deterministic():
    def run():
        store = TrajectoryStore(":memory:")
        try:
            d = run_closed_loop_demo(
                load_dataset(GOLD),
                store,
                MockProvider(tier="remote"),
                failure_mode="bad_enum",
                failure_rate=1.0,
                seed=42,
            )
            return (
                d.phase_b.metrics.escalation_rate,
                d.phase_c.metrics.preroute_remote_rate,
                {k: v.threshold for k, v in d.policy_after_b.items()},
            )
        finally:
            store.close()

    assert run() == run()


def test_cli_closed_loop_demo_text(capsys):
    rc = cli_main(["--dataset", GOLD, "--closed-loop-demo",
                   "--failure-mode", "bad_enum", "--failure-rate", "1.0"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "phase A (healthy local tier)" in out
    assert "phase B (degraded local tier, default routing)" in out
    assert "phase C (degraded local tier, adapted routing)" in out
    assert "force_remote" in out
    assert "example phase-C routing reason" in out
    assert "ewma drift" in out


def test_cli_closed_loop_demo_json(capsys):
    rc = cli_main(["--dataset", GOLD, "--closed-loop-demo", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["phase_c"]["metrics"]["pass_rate"] == 1.0
    assert (
        payload["policy_after_b"]["severity_classification"]["action"]
        == "force_remote"
    )
