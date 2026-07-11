"""Live demo helper tests. No streamlit, no network, no secrets."""

import json

import pytest

from kaaval_assurance.demo import (
    LIVE_FAILURE_MODES,
    export_live_demo_artifacts,
    run_live_demo,
)

INCIDENT = (
    "Core router CR-04 dropped all BGP sessions at 02:13; downstream OLT "
    "sites in region south lost upstream connectivity."
)
SEVERITY = "telecom.severity_classification"

VALID_SOURCES = {"measured", "configured", "not_available", "planned"}


class TestRunLiveDemo:
    def test_happy_path_local_pass(self):
        demo = run_live_demo(INCIDENT, SEVERITY, failure_mode=None, case_id="t1")
        assert demo.result.verification.passed
        assert not demo.result.escalated
        assert demo.result.attempts == 1
        assert len(demo.rows) == 1
        assert demo.local_row.verifier_passed
        assert demo.remote_row is None
        assert demo.rows[0].task_input == INCIDENT  # replayable

    def test_failed_local_escalates_to_remote(self):
        demo = run_live_demo(INCIDENT, SEVERITY, failure_mode="bad_enum", case_id="t2")
        assert demo.result.escalated
        assert demo.result.attempts == 2
        assert demo.result.verification.passed  # remote rescues
        assert len(demo.rows) == 2
        assert not demo.local_row.verifier_passed
        assert "enum:severity" in demo.local_row.verifier_failures
        assert demo.remote_row.verifier_passed
        assert demo.remote_row.escalated
        assert "layer-1 verification failed" in demo.result.routing.reason

    def test_unparseable_local_output(self):
        demo = run_live_demo(INCIDENT, SEVERITY, failure_mode="unparseable")
        assert demo.local_row.verifier_failures == ["json_parse"]
        assert demo.result.escalated

    def test_missing_field_local_output(self):
        demo = run_live_demo(INCIDENT, SEVERITY, failure_mode="missing_field")
        assert any(
            f.startswith("required:") for f in demo.local_row.verifier_failures
        )

    def test_invalid_failure_mode_rejected(self):
        with pytest.raises(ValueError, match="failure_mode"):
            run_live_demo(INCIDENT, SEVERITY, failure_mode="explode")
        assert "out_of_range" in LIVE_FAILURE_MODES  # policy-cap violations are demoable


class TestExportArtifacts:
    def export(self, tmp_path, failure_mode="bad_enum"):
        demo = run_live_demo(INCIDENT, SEVERITY, failure_mode=failure_mode, case_id="x1")
        paths = export_live_demo_artifacts(demo, tmp_path)
        return demo, {p.name: p for p in paths}

    def test_writes_all_three_artifacts(self, tmp_path):
        _, files = self.export(tmp_path)
        assert set(files) == {
            "demo-live-telemetry.json",
            "demo-live-trajectory.json",
            "demo-live-summary.md",
            "demo-live-manifest.json",
        }
        for path in files.values():
            assert path.exists() and path.stat().st_size > 0

    def test_telemetry_has_source_tags_and_no_measured_runtime(self, tmp_path):
        _, files = self.export(tmp_path)
        telemetry = json.loads(files["demo-live-telemetry.json"].read_text())
        assert telemetry["claims"]
        for claim in telemetry["claims"]:
            assert claim["source"] in VALID_SOURCES
        assert telemetry["runtime"]["status"] in ("planned", "configured")
        runtime_claim = next(
            c for c in telemetry["claims"] if c["claim"] == "Runtime"
        )
        assert runtime_claim["source"] != "measured"

    def test_trajectory_artifact_replayable(self, tmp_path):
        demo, files = self.export(tmp_path)
        rows = json.loads(files["demo-live-trajectory.json"].read_text())
        assert len(rows) == 2
        assert rows[0]["tier"] == "local" and rows[0]["verifier_failures"]
        assert rows[1]["tier"] == "remote" and rows[1]["escalated"]
        assert rows[0]["task_input"] == INCIDENT

    def test_summary_markdown_content(self, tmp_path):
        _, files = self.export(tmp_path)
        md = files["demo-live-summary.md"].read_text()
        assert "Escalation:" in md
        assert "| Claim | Value | Source |" in md
        assert "mock local tier" in md
        assert "measured AMD claims require" in md

    def test_no_secrets_in_exports(self, tmp_path):
        _, files = self.export(tmp_path)
        for path in files.values():
            content = path.read_text()
            for marker in ("api_key", "API_KEY", "Bearer ", "sk-", "fw-"):
                assert marker not in content, f"{marker!r} in {path.name}"

    def test_happy_path_export_reports_no_escalation(self, tmp_path):
        _, files = self.export(tmp_path, failure_mode=None)
        md = files["demo-live-summary.md"].read_text()
        assert "not needed" in md
        rows = json.loads(files["demo-live-trajectory.json"].read_text())
        assert len(rows) == 1

    def test_e2e_dashboard_bundle_consistency(self, tmp_path):
        from apps.api.artifacts import ArtifactStore
        demo, _ = self.export(tmp_path, failure_mode=None)
        store = ArtifactStore(artifacts_dir=tmp_path, sample_dir=tmp_path / "sample")
        dash = store.dashboard()
        assert dash["bundle_consistent"] is True
        assert dash["bundle_id"] == demo.result.request_id

    def test_summary_markdown_provider_aware(self, tmp_path):
        from kaaval_assurance.providers import MockProvider

        # Test Ollama
        demo = run_live_demo(INCIDENT, SEVERITY, failure_mode=None, case_id="x2", local_provider=MockProvider(tier="local", provider_name="ollama"))
        export_live_demo_artifacts(demo, tmp_path / "ollama")
        md = (tmp_path / "ollama" / "demo-live-summary.md").read_text()
        assert "Ollama" in md
        assert "not an AMD proof" in md

        # Test vLLM-Gemma
        demo = run_live_demo(INCIDENT, SEVERITY, failure_mode=None, case_id="x3", local_provider=MockProvider(tier="local", provider_name="vllm-gemma"))
        export_live_demo_artifacts(demo, tmp_path / "vllm")
        md = (tmp_path / "vllm" / "demo-live-summary.md").read_text()
        assert "vLLM execution" in md
        assert "AMD status requires matching" in md

        # Test unknown/other
        demo = run_live_demo(INCIDENT, SEVERITY, failure_mode=None, case_id="x4", local_provider=MockProvider(tier="local", provider_name="unknown-provider"))
        export_live_demo_artifacts(demo, tmp_path / "unknown")
        md = (tmp_path / "unknown" / "demo-live-summary.md").read_text()
        assert "unknown-provider" in md
        assert "AMD claims require vLLM execution" in md


class TestMockGroundingScript:
    def test_script_executes_successfully(self):
        import subprocess
        from pathlib import Path

        root = Path(__file__).resolve().parents[1]
        script = root / "scripts" / "mock_grounding_ewma_demo.sh"
        
        # Test it uses the correct venv when we explicitly point KAAVAL_PYTHON to sys.executable
        # or when we just let it run (it should find .venv or fallback successfully)
        import sys
        env = {"KAAVAL_PYTHON": sys.executable}

        result = subprocess.run(
            [str(script)],
            cwd=str(root),
            env=env,
            capture_output=True,
            text=True
        )

        assert result.returncode == 0, f"Script failed with output: {result.stderr}"
        assert "mock-only demo" in result.stdout or "online EWMA drift" in result.stdout
