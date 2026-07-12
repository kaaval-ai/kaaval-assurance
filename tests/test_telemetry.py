"""Telemetry Truth Layer tests. Network-free: mock providers only."""

import json

import pytest

from kaaval_assurance.audit import MockAuditChallenger, calibrate_challenger, run_sampled_audit
from kaaval_assurance.eval import load_dataset
from kaaval_assurance.eval.cli import main as cli_main
from kaaval_assurance.eval.runner import run_eval
from kaaval_assurance.pipeline import AssurancePipeline
from kaaval_assurance.providers import MockProvider
from kaaval_assurance.providers.vllm import VllmConfig, VllmProvider
from kaaval_assurance.router import Router
from kaaval_assurance.routing_policy import apply_policy, policy_from_drift
from kaaval_assurance.telemetry import (
    baseline_from_rows,
    build_telemetry_summary,
    render_summary_markdown,
    render_summary_text,
)
from kaaval_assurance.trajectory import TrajectoryStore

GOLD = "data/eval/telecom_gold.jsonl"


def run_mock_eval(store, local_failure=None, audit_flag_rate=None, sample_rate=1.0):
    pipeline = AssurancePipeline(
        router=Router(),
        local_provider=MockProvider(tier="local", failure_mode=local_failure),
        remote_provider=MockProvider(tier="remote", model_id="mock-remote-strong"),
        store=store,
    )
    cases = load_dataset(GOLD)
    report = run_eval(pipeline, cases)
    if audit_flag_rate is not None:
        challenger = MockAuditChallenger(flag_rate=audit_flag_rate, seed=7)
        calibration = calibrate_challenger(
            MockAuditChallenger(flag_rate=audit_flag_rate, seed=7), cases
        )
        rows = collect_rows(store, report)
        summary, _ = run_sampled_audit(
            store, rows, challenger, calibration, sample_rate=sample_rate
        )
        report.audit = summary
    return report, collect_rows(store, report)


def collect_rows(store, report):
    rows = []
    for r in report.results:
        rows.extend(store.rows_for_request(r.request_id))
    return rows


class TestSummaryDerivation:
    def test_derives_from_rows_not_hardcoded(self):
        store = TrajectoryStore(":memory:")
        try:
            report, rows = run_mock_eval(store, local_failure="bad_enum")
            t = build_telemetry_summary(report, rows)
        finally:
            store.close()

        # bad_enum degrades 2 of 4 categories -> 8 escalations of 16 requests
        assert t.requests == 16
        assert t.attempts == 24
        assert t.verification.local_verified_rate == pytest.approx(0.5)
        assert t.verification.final_verified_rate == 1.0
        assert t.routing.escalation_rate == pytest.approx(0.5)
        # sev-001 and act-001 also trip the deterministic grounding rules
        # alongside their enum failure (see test_grounding_rules.py).
        assert t.verification.failures_by_check == {
            "enum:severity": 4,
            "enum:urgency": 4,
            "grounding:regional_outage_requires_p1": 1,
            "grounding:no_redundancy_requires_immediate": 1,
        }
        assert t.latency_ms_p95 > t.latency_ms_p50

    def test_provider_mix(self):
        store = TrajectoryStore(":memory:")
        try:
            report, rows = run_mock_eval(store, local_failure="bad_enum")
            t = build_telemetry_summary(report, rows)
        finally:
            store.close()
        assert t.provider_mix.local_attempts == 16
        assert t.provider_mix.remote_attempts == 8
        assert t.provider_mix.attempts_by_provider == {"mock": 24}
        assert t.provider_mix.requests_by_first_tier == {"local": 16}

    def test_high_drift_categories_surfaced(self):
        store = TrajectoryStore(":memory:")
        try:
            report, rows = run_mock_eval(store, local_failure="bad_enum")
            t = build_telemetry_summary(report, rows)
        finally:
            store.close()
        assert set(t.routing.high_drift_categories) == {
            "severity_classification",
            "next_action_recommendation",
        }
        assert t.routing.watch_categories == []

    def test_cost_per_verified_answer(self):
        store = TrajectoryStore(":memory:")
        try:
            report, rows = run_mock_eval(store, local_failure="bad_enum")
            t = build_telemetry_summary(report, rows)
        finally:
            store.close()
        assert t.cost.remote_cost_usd == pytest.approx(8 * 0.001)
        assert t.cost.local_cost_usd == 0.0
        assert t.cost.cost_per_verified_answer_usd == pytest.approx(8 * 0.001 / 16)


class TestAuditReflection:
    def test_trusted_audit_reflected(self):
        store = TrajectoryStore(":memory:")
        try:
            report, rows = run_mock_eval(store, audit_flag_rate=0.0)
            t = build_telemetry_summary(report, rows)
        finally:
            store.close()
        assert t.audit.enabled and t.audit.trusted is True
        assert t.audit.sampled == 16
        assert t.audit.calibration_status == "passed"
        claim = next(
            c for c in t.claims if c.claim == "Layer 3 FP calibration passed"
        )
        assert claim.value == "yes; display-only, not a routing input"
        assert claim.source == "measured"
        assert t.audit.calibration_scope == "false_positive_only"
        assert t.audit.routing_integration == "display_only"

    def test_untrusted_audit_reflected(self):
        store = TrajectoryStore(":memory:")
        try:
            report, rows = run_mock_eval(store, audit_flag_rate=0.9)
            t = build_telemetry_summary(report, rows)
        finally:
            store.close()
        assert t.audit.trusted is False
        assert t.audit.calibration_status == "failed"
        assert t.audit.violations_by_severity.get("major", 0) > 0

    def test_no_audit_marked_not_available(self):
        store = TrajectoryStore(":memory:")
        try:
            report, rows = run_mock_eval(store)
            t = build_telemetry_summary(report, rows)
        finally:
            store.close()
        assert t.audit.enabled is False
        claim = next(
            c for c in t.claims if c.claim == "Layer 3 FP calibration passed"
        )
        assert claim.source == "not_available"


class TestBaseline:
    def make_always_remote_rows(self):
        store = TrajectoryStore(":memory:")
        try:
            router = Router()
            drift = {c: 1.0 for c in [
                "severity_classification", "component_extraction",
                "incident_summary", "next_action_recommendation",
            ]}
            apply_policy(router, policy_from_drift(drift))
            pipeline = AssurancePipeline(
                router=router,
                local_provider=MockProvider(tier="local"),
                remote_provider=MockProvider(tier="remote"),
                store=store,
            )
            report = run_eval(pipeline, load_dataset(GOLD))
            return collect_rows(store, report)
        finally:
            store.close()

    def test_savings_null_without_baseline(self):
        store = TrajectoryStore(":memory:")
        try:
            report, rows = run_mock_eval(store)
            t = build_telemetry_summary(report, rows)
        finally:
            store.close()
        assert t.cost.remote_calls_avoided is None
        assert t.cost.remote_tokens_avoided is None
        assert t.cost.estimated_cost_saved_vs_always_remote_usd is None
        claim = next(
            c for c in t.claims if c.claim == "Remote calls avoided vs always-remote"
        )
        assert claim.source == "not_available"

    def test_savings_computed_with_baseline(self):
        baseline = baseline_from_rows(self.make_always_remote_rows())
        assert baseline.remote_calls == 16

        store = TrajectoryStore(":memory:")
        try:
            report, rows = run_mock_eval(store, local_failure="bad_enum")
            t = build_telemetry_summary(report, rows, always_remote_baseline=baseline)
        finally:
            store.close()
        assert t.cost.remote_calls_avoided == 16 - 8
        assert t.cost.remote_calls_avoided_rate == pytest.approx(0.5)
        assert t.cost.remote_tokens_avoided is not None
        assert t.cost.estimated_cost_saved_vs_always_remote_usd == pytest.approx(
            16 * 0.001 - 8 * 0.001
        )


class TestRuntimeSource:
    def test_configured_profile_never_measured(self):
        profile = VllmProvider(
            VllmConfig(model="gemma-3-12b-it", rocm_version="6.3")
        ).runtime_profile()
        store = TrajectoryStore(":memory:")
        try:
            report, rows = run_mock_eval(store)
            t = build_telemetry_summary(report, rows, runtime_profile=profile)
        finally:
            store.close()
        assert t.runtime.status == "configured"
        claim = next(c for c in t.claims if c.claim == "Runtime")
        assert claim.source == "configured"
        assert "gemma-3-12b-it" in claim.value
        assert "ROCm 6.3" in claim.value

    def test_mock_run_is_planned(self):
        store = TrajectoryStore(":memory:")
        try:
            report, rows = run_mock_eval(store)
            t = build_telemetry_summary(report, rows)
        finally:
            store.close()
        assert t.runtime.status == "planned"
        claim = next(c for c in t.claims if c.claim == "Runtime")
        assert claim.source == "planned"


class TestRendering:
    def test_text_and_markdown(self):
        store = TrajectoryStore(":memory:")
        try:
            report, rows = run_mock_eval(store, audit_flag_rate=0.0)
            t = build_telemetry_summary(report, rows)
        finally:
            store.close()
        text = render_summary_text(t)
        assert "Local Layer-1 contract-conformance rate: 100.0% [measured]" in text
        md = render_summary_markdown(t)
        assert "| Claim | Value | Source |" in md
        assert "| Local Layer-1 contract-conformance rate | 100.0% | measured |" in md


class TestCliTelemetry:
    def test_summary_flag_prints_block(self, capsys):
        rc = cli_main(
            ["--dataset", GOLD, "--audit-provider", "mock",
             "--audit-sample-rate", "1.0", "--telemetry-summary"]
        )
        assert rc == 0
        out = capsys.readouterr().out
        assert "=== telemetry truth summary ===" in out
        assert "Local Layer-1 contract-conformance rate: 100.0% [measured]" in out
        assert (
            "Layer 3 FP calibration passed: yes; display-only, not a routing input "
            "[measured]" in out
        )
        assert "[planned]" in out  # mock local tier -> runtime planned

    def test_telemetry_json_parses(self, capsys):
        rc = cli_main(["--dataset", GOLD, "--telemetry-json", "--json"])
        assert rc == 0
        out = capsys.readouterr().out
        # two JSON documents: report then telemetry; split on the first
        # top-level close followed by open brace
        first, _, second = out.partition("}\n{")
        telemetry = json.loads("{" + second)
        assert telemetry["runtime"]["status"] == "planned"
        assert telemetry["verification"]["final_verified_rate"] == 1.0

    def test_markdown_file_written(self, tmp_path, capsys):
        md = tmp_path / "telemetry.md"
        rc = cli_main(["--dataset", GOLD, "--telemetry-markdown", str(md)])
        assert rc == 0
        content = md.read_text()
        assert "# Telemetry truth summary" in content
        assert "| Runtime |" in content

    def test_baseline_db_flag(self, tmp_path, capsys):
        baseline_db = tmp_path / "baseline.db"
        store = TrajectoryStore(baseline_db)
        try:
            router = Router()
            apply_policy(
                router,
                policy_from_drift(
                    {c: 1.0 for c in [
                        "severity_classification", "component_extraction",
                        "incident_summary", "next_action_recommendation",
                    ]}
                ),
            )
            pipeline = AssurancePipeline(
                router=router,
                local_provider=MockProvider(tier="local"),
                remote_provider=MockProvider(tier="remote"),
                store=store,
            )
            run_eval(pipeline, load_dataset(GOLD))
        finally:
            store.close()

        rc = cli_main(
            ["--dataset", GOLD, "--telemetry-summary",
             "--always-remote-baseline-db", str(baseline_db)]
        )
        assert rc == 0
        out = capsys.readouterr().out
        assert "Remote calls avoided vs always-remote: 100.0%" in out

    def test_telemetry_rejected_in_demo(self, capsys):
        rc = cli_main(
            ["--dataset", GOLD, "--closed-loop-demo", "--telemetry-summary"]
        )
        assert rc == 2
        assert "standard eval path" in capsys.readouterr().err
