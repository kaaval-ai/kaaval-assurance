"""Layer 3 audit backbone tests: schema, calibration gate, sampled runner.

Network-free throughout: mock challenger only; Fireworks challenger is
covered with faked HTTP in test_audit_fireworks.py.
"""

import json

import pytest
from pydantic import ValidationError

from kaaval_assurance.audit import (
    AuditViolation,
    ChallengerOutput,
    MockAuditChallenger,
    aggregate_verdict,
    calibrate_challenger,
    run_sampled_audit,
    skipped_calibration,
)
from kaaval_assurance.audit.prompting import (
    build_audit_system_prompt,
    build_audit_user_prompt,
)
from kaaval_assurance.contracts import get_contract
from kaaval_assurance.eval import load_dataset
from kaaval_assurance.eval.cli import main as cli_main
from kaaval_assurance.eval.runner import run_eval
from kaaval_assurance.pipeline import AssurancePipeline
from kaaval_assurance.providers import MockProvider
from kaaval_assurance.router import Router
from kaaval_assurance.trajectory import TrajectoryStore

GOLD = "data/eval/telecom_gold.jsonl"
SEVERITY = get_contract("telecom.severity_classification")


def make_pipeline(store, local_failure=None):
    return AssurancePipeline(
        router=Router(),
        local_provider=MockProvider(tier="local", failure_mode=local_failure),
        remote_provider=MockProvider(tier="remote", model_id="mock-remote-strong"),
        store=store,
    )


class TestAuditSchema:
    def test_violation_requires_valid_severity(self):
        with pytest.raises(ValidationError):
            AuditViolation(
                check_id="x", severity="fatal", description="d", evidence="e"
            )

    def test_challenger_output_validates(self):
        out = ChallengerOutput.model_validate(
            {
                "result": "fail",
                "violations": [
                    {
                        "check_id": "severity_mismatch",
                        "severity": "major",
                        "field": "severity",
                        "description": "label inconsistent with impact",
                        "evidence": "Customer impact confirmed",
                        "repair_hint": "Verify the severity label specifically.",
                    }
                ],
            }
        )
        assert out.violations[0].field == "severity"

    def test_malformed_output_rejected(self):
        with pytest.raises(ValidationError):
            ChallengerOutput.model_validate({"result": "maybe", "violations": []})

    def test_aggregation_is_deterministic_over_structured_output(self):
        minor_only = ChallengerOutput(
            result="pass",
            violations=[
                AuditViolation(
                    check_id="c", severity="minor", description="d", evidence="e"
                )
            ],
        )
        assert aggregate_verdict(minor_only) == "pass"
        major = ChallengerOutput(
            result="pass",
            violations=[
                AuditViolation(
                    check_id="c", severity="major", description="d", evidence="e"
                )
            ],
        )
        assert aggregate_verdict(major) == "fail"
        assert aggregate_verdict(ChallengerOutput(result="fail")) == "fail"


class TestAuditPrompt:
    def test_prompt_does_not_presume_failure(self):
        system = build_audit_system_prompt(SEVERITY)
        assert (
            "If no violation is supported by the evidence, return pass with an "
            "empty violations list." in system
        )
        assert "Verify these specifically." in system
        assert "must find" not in system.lower()

    def test_prompt_contains_contract_rules_and_intent(self):
        system = build_audit_system_prompt(SEVERITY)
        assert '"P1", "P2", "P3", "P4"' in system
        assert "minimum 0.0" in system and "maximum 1.0" in system
        assert SEVERITY.semantic_intent in system
        assert "ONLY a JSON object" in system

    def test_stable_prefix_variable_suffix(self):
        # System prompt identical across cases of the same contract
        # (cache-friendly); case specifics live in the user prompt only.
        assert build_audit_system_prompt(SEVERITY) == build_audit_system_prompt(
            SEVERITY
        )
        user = build_audit_user_prompt("input text", {"severity": "P1"})
        assert "input text" in user
        assert '"severity": "P1"' in user

    def test_repair_hint_policy_worded_as_verification(self):
        system = build_audit_system_prompt(SEVERITY)
        assert "never as an asserted failure" in system


class TestCalibration:
    def test_clean_challenger_passes_gold_calibration(self):
        report = calibrate_challenger(
            MockAuditChallenger(flag_rate=0.0), load_dataset(GOLD)
        )
        assert report.total_gold == 16
        assert report.false_positives == 0
        assert report.false_positive_rate == 0.0
        assert report.status == "passed"

    def test_overflagging_challenger_fails_calibration(self):
        report = calibrate_challenger(
            MockAuditChallenger(flag_rate=0.9, seed=1), load_dataset(GOLD)
        )
        assert report.false_positive_rate > 0.20
        assert report.status == "failed"
        assert report.flagged_case_ids

    def test_threshold_configurable(self):
        report = calibrate_challenger(
            MockAuditChallenger(flag_rate=0.9, seed=1),
            load_dataset(GOLD),
            threshold=1.0,
        )
        assert report.status == "passed"

    def test_skipped_calibration_is_not_passed(self):
        assert skipped_calibration().status == "skipped"


class TestSampledAudit:
    def run_audit(self, flag_rate=0.0, sample_rate=1.0, local_failure=None):
        store = TrajectoryStore(":memory:")
        try:
            pipeline = make_pipeline(store, local_failure=local_failure)
            cases = load_dataset(GOLD)
            report = run_eval(pipeline, cases)
            challenger = MockAuditChallenger(flag_rate=flag_rate, seed=7)
            calibration = calibrate_challenger(
                MockAuditChallenger(flag_rate=flag_rate, seed=7), cases
            )
            rows = []
            for r in report.results:
                rows.extend(store.rows_for_request(r.request_id))
            summary, results = run_sampled_audit(
                store, rows, challenger, calibration,
                sample_rate=sample_rate, seed=3,
            )
            all_rows = store.all_rows()
            return summary, results, all_rows
        finally:
            store.close()

    def test_full_sample_audits_all_accepted(self):
        summary, results, rows = self.run_audit(sample_rate=1.0)
        assert summary.accepted_answers == 16
        assert summary.sampled == 16
        assert summary.passed == 16
        assert summary.failed == 0
        assert summary.trusted is True

    def test_only_layer1_passing_final_attempts_audited(self):
        # bad_enum degrades 2 categories: failed local attempts must never be
        # audited; the escalated remote finals are the accepted answers.
        summary, results, rows = self.run_audit(
            sample_rate=1.0, local_failure="bad_enum"
        )
        assert summary.accepted_answers == 16  # all requests end accepted
        audited_rows = [r for r in rows if r.audit_sampled]
        assert audited_rows
        for row in audited_rows:
            assert row.verifier_passed

    def test_sampling_deterministic_and_partial(self):
        s1, _, _ = self.run_audit(sample_rate=0.5)
        s2, _, _ = self.run_audit(sample_rate=0.5)
        assert s1.sampled == s2.sampled
        assert 0 < s1.sampled < 16

    def test_audit_fields_persist_to_store(self):
        summary, results, rows = self.run_audit(sample_rate=1.0, flag_rate=1.0)
        audited = [r for r in rows if r.audit_sampled]
        assert len(audited) == 16
        for row in audited:
            assert row.audit_result == "fail"
            assert row.audit_violations
            v = row.audit_violations[0]
            assert v["severity"] == "major"
            assert v["repair_hint"].startswith("Verify")

    def test_failed_calibration_marks_signal_untrusted(self):
        summary, _, _ = self.run_audit(flag_rate=0.9, sample_rate=1.0)
        assert summary.calibration.status == "failed"
        assert summary.trusted is False  # hard gate: no Layer-2 trust

    def test_metrics_untouched_by_audit(self):
        store = TrajectoryStore(":memory:")
        try:
            pipeline = make_pipeline(store)
            cases = load_dataset(GOLD)
            report = run_eval(pipeline, cases)
            before = report.metrics.model_dump()
            challenger = MockAuditChallenger(flag_rate=1.0)
            calibration = calibrate_challenger(MockAuditChallenger(1.0), cases)
            rows = []
            for r in report.results:
                rows.extend(store.rows_for_request(r.request_id))
            run_sampled_audit(store, rows, challenger, calibration, sample_rate=1.0)
            # audit failures never alter request success/failure semantics
            assert report.metrics.model_dump() == before
        finally:
            store.close()

    def test_cost_accounting_fields(self):
        summary, _, _ = self.run_audit(sample_rate=1.0)
        assert summary.total_cost_usd == 0.0  # mock challenger is free
        assert summary.cost_per_sampled_usd == 0.0
        assert summary.cost_per_verified_accepted_usd == 0.0
        assert summary.audit_tokens == 0


class TestCliAudit:
    def test_mock_audit_path_text(self, capsys):
        rc = cli_main(
            ["--dataset", GOLD, "--audit-provider", "mock",
             "--audit-sample-rate", "1.0"]
        )
        assert rc == 0
        out = capsys.readouterr().out
        assert "layer-3 audit (mock-audit" in out
        assert "calibration passed" in out
        assert "sampled 16/16 accepted" in out
        assert "Layer 3 sampled 100% of accepted answers" in out

    def test_mock_audit_json_includes_summary(self, capsys):
        rc = cli_main(
            ["--dataset", GOLD, "--audit-provider", "mock",
             "--audit-sample-rate", "1.0", "--json"]
        )
        assert rc == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["audit"]["trusted"] is True
        assert payload["audit"]["sampled"] == 16
        assert payload["audit"]["calibration"]["status"] == "passed"

    def test_skip_calibration_marks_untrusted(self, capsys):
        rc = cli_main(
            ["--dataset", GOLD, "--audit-provider", "mock",
             "--skip-audit-calibration", "--json"]
        )
        assert rc == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["audit"]["calibration"]["status"] == "skipped"
        assert payload["audit"]["trusted"] is False

    def test_fireworks_audit_without_key_exits_2(self, monkeypatch, capsys):
        monkeypatch.delenv("FIREWORKS_API_KEY", raising=False)
        rc = cli_main(["--dataset", GOLD, "--audit-provider", "fireworks"])
        assert rc == 2
        assert "FIREWORKS_API_KEY" in capsys.readouterr().err

    def test_audit_rejected_in_closed_loop_demo(self, capsys):
        rc = cli_main(
            ["--dataset", GOLD, "--closed-loop-demo", "--audit-provider", "mock"]
        )
        assert rc == 2
        assert "standard eval path" in capsys.readouterr().err

    def test_default_has_no_audit(self, capsys):
        rc = cli_main(["--dataset", GOLD, "--json"])
        assert rc == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["audit"] is None
