"""Multi-step agent workflow: several verified decisions chained together.

Proves the "agentic" claim is literal, not aspirational: one initial input
drives a sequence of independently-verified steps, each step's finding
feeds the next, escalation within a step is transparent to the chain, and
a step that never verifies (even after escalation) honestly halts the run
instead of feeding a bad finding downstream.
"""

import pytest
from fastapi.testclient import TestClient

from apps.api.artifacts import ArtifactStore
from apps.api.server import create_app
from kaaval_assurance.agent import (
    NOC_INCIDENT_WORKFLOW,
    run_agent_workflow,
    rows_for_agent_run,
)
from kaaval_assurance.agent_cli import main as agent_cli_main
from kaaval_assurance.pipeline import AssurancePipeline
from kaaval_assurance.providers import MockProvider
from kaaval_assurance.router import Router
from kaaval_assurance.trajectory import TrajectoryStore

INCIDENT = (
    "Core router CR-04 dropped all BGP sessions at 02:13; downstream OLT "
    "sites in region south lost upstream connectivity. Customer impact "
    "confirmed across 40k subscribers."
)


@pytest.fixture()
def store():
    s = TrajectoryStore(":memory:")
    yield s
    s.close()


class TestHappyPathChain:
    def test_all_four_steps_complete_and_verify(self, store):
        pipeline = AssurancePipeline(
            router=Router(),
            local_provider=MockProvider(tier="local"),
            remote_provider=MockProvider(tier="remote", model_id="mock-remote-strong"),
            store=store,
        )
        result = run_agent_workflow(pipeline, INCIDENT, NOC_INCIDENT_WORKFLOW)

        assert result.completed
        assert result.blocked_at is None
        assert len(result.steps) == 4
        assert [s.attempts for s in result.steps] == [1, 1, 1, 1]
        for step in result.steps:
            assert step.verification.passed

    def test_context_accumulates_across_steps(self, store):
        pipeline = AssurancePipeline(
            router=Router(),
            local_provider=MockProvider(tier="local"),
            remote_provider=MockProvider(tier="remote", model_id="mock-remote-strong"),
            store=store,
        )
        run_agent_workflow(pipeline, INCIDENT, NOC_INCIDENT_WORKFLOW)

        rows = store.all_rows()
        by_category = {r.category: r for r in rows}
        # severity_classification's stored input is step 2 - it must carry
        # step 1's finding forward, not just the raw incident text alone.
        severity_row = by_category["severity_classification"]
        assert "component_extraction" in severity_row.task_input
        assert INCIDENT in severity_row.task_input
        # the final step has accumulated all three prior findings
        action_row = by_category["next_action_recommendation"]
        assert "component_extraction" in action_row.task_input
        assert "severity_classification" in action_row.task_input
        assert "incident_summary" in action_row.task_input

    def test_step_request_ids_distinct_and_readable(self, store):
        pipeline = AssurancePipeline(
            router=Router(),
            local_provider=MockProvider(tier="local"),
            remote_provider=MockProvider(tier="remote", model_id="mock-remote-strong"),
            store=store,
        )
        result = run_agent_workflow(
            pipeline, INCIDENT, NOC_INCIDENT_WORKFLOW, run_id="demo1"
        )
        ids = [s.request_id for s in result.steps]
        assert len(set(ids)) == 4
        assert ids[0] == "agent-demo1-step1-component_extraction"
        assert ids[3] == "agent-demo1-step4-next_action_recommendation"

    def test_rows_for_agent_run_covers_every_step(self, store):
        pipeline = AssurancePipeline(
            router=Router(),
            local_provider=MockProvider(tier="local"),
            remote_provider=MockProvider(tier="remote", model_id="mock-remote-strong"),
            store=store,
        )
        result = run_agent_workflow(pipeline, INCIDENT, NOC_INCIDENT_WORKFLOW)
        rows = rows_for_agent_run(store, result)
        assert len(rows) == 4  # one local attempt per step, none escalated
        assert [r.category for r in rows] == [
            "component_extraction",
            "severity_classification",
            "incident_summary",
            "next_action_recommendation",
        ]


class TestEscalationWithinAStep:
    def test_escalated_step_still_advances_the_chain(self, store):
        pipeline = AssurancePipeline(
            router=Router(),
            local_provider=MockProvider(tier="local", failure_mode="missing_field"),
            remote_provider=MockProvider(tier="remote", model_id="mock-remote-strong"),
            store=store,
        )
        result = run_agent_workflow(pipeline, INCIDENT, NOC_INCIDENT_WORKFLOW)

        assert result.completed
        assert len(result.steps) == 4
        # every step failed locally (missing_field) and was rescued remotely
        assert all(s.escalated for s in result.steps)
        assert all(s.verification.passed for s in result.steps)

        rows = rows_for_agent_run(store, result)
        assert len(rows) == 8  # local FAILED + remote rescue, per step


class TestHonestHardStop:
    def test_step_that_never_verifies_halts_the_run(self, store):
        pipeline = AssurancePipeline(
            router=Router(),
            local_provider=MockProvider(tier="local", failure_mode="missing_field"),
            remote_provider=MockProvider(
                tier="remote", model_id="mock-remote-strong", failure_mode="missing_field"
            ),
            store=store,
        )
        result = run_agent_workflow(pipeline, INCIDENT, NOC_INCIDENT_WORKFLOW)

        assert not result.completed
        assert result.blocked_at == "telecom.component_extraction"
        assert len(result.steps) == 1  # steps 2-4 never attempted
        assert not result.steps[0].verification.passed

    def test_downstream_steps_never_touch_the_store(self, store):
        pipeline = AssurancePipeline(
            router=Router(),
            local_provider=MockProvider(tier="local", failure_mode="missing_field"),
            remote_provider=MockProvider(
                tier="remote", model_id="mock-remote-strong", failure_mode="missing_field"
            ),
            store=store,
        )
        run_agent_workflow(pipeline, INCIDENT, NOC_INCIDENT_WORKFLOW)
        rows = store.all_rows()
        categories = {r.category for r in rows}
        assert categories == {"component_extraction"}
        assert "severity_classification" not in categories


class TestRunnableAgentSurface:
    def test_cli_runs_complete_mock_workflow(self, capsys):
        rc = agent_cli_main(["--input", INCIDENT])
        output = capsys.readouterr().out
        assert rc == 0
        assert '"status": "completed"' in output
        assert output.count('"contract_conformant": true') == 4

    def test_api_runs_complete_mock_workflow(self, tmp_path, monkeypatch):
        monkeypatch.setenv("KAAVAL_LIVE_RUNS_ENABLED", "1")
        store = ArtifactStore(
            artifacts_dir=tmp_path / "artifacts",
            sample_dir=tmp_path / "sample",
        )
        client = TestClient(create_app(store))

        response = client.post(
            "/api/agent-runs",
            json={
                "task_input": INCIDENT,
                "local_provider": "mock",
                "remote_provider": "mock",
            },
        )

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "completed"
        assert len(body["steps"]) == 4
        assert all(step["status"] == "accepted" for step in body["steps"])
        assert all(step["accepted_answer"] for step in body["steps"])

    def test_api_agent_paid_remote_is_operator_gated(
        self, tmp_path, monkeypatch
    ):
        monkeypatch.setenv("KAAVAL_LIVE_RUNS_ENABLED", "1")
        monkeypatch.delenv("KAAVAL_ALLOW_PAID_REMOTE", raising=False)
        store = ArtifactStore(
            artifacts_dir=tmp_path / "artifacts",
            sample_dir=tmp_path / "sample",
        )
        client = TestClient(create_app(store))

        response = client.post(
            "/api/agent-runs",
            json={
                "task_input": INCIDENT,
                "local_provider": "mock",
                "remote_provider": "fireworks",
                "confirm_spend": True,
            },
        )

        assert response.status_code == 403
        assert "disabled" in response.json()["detail"]
