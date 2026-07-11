"""Multi-step agent workflows: several verified decisions chained toward one goal.

The primitive an agentic system actually needs at each step it's about to
act is exactly what AssurancePipeline.handle_request already provides:
verify, escalate on failure, record. This module adds nothing to that
engine — it only calls it repeatedly, feeding each verified step's finding
forward as context for the next, and refusing to let an unverified step
poison downstream steps. If a step never verifies (even after escalation),
the run stops honestly at that step instead of guessing forward.
"""

import uuid
from typing import Optional

from pydantic import BaseModel, Field

from .models import PipelineResult
from .pipeline import AssurancePipeline
from .trajectory import TrajectoryStore
from .models import TrajectoryRow

# One real, concrete agent: a NOC engineer's actual workflow for one
# incident, expressed as four independently-verified decisions in sequence.
NOC_INCIDENT_WORKFLOW = [
    "telecom.component_extraction",
    "telecom.severity_classification",
    "telecom.incident_summary",
    "telecom.next_action_recommendation",
]


class AgentRunResult(BaseModel):
    run_id: str
    initial_input: str
    contract_sequence: list[str]
    completed: bool
    blocked_at: Optional[str] = None
    steps: list[PipelineResult] = Field(default_factory=list)


def run_agent_workflow(
    pipeline: AssurancePipeline,
    initial_input: str,
    contract_sequence: list[str],
    run_id: Optional[str] = None,
) -> AgentRunResult:
    """Run contract_sequence in order; each step's verified finding is
    appended to the context the next step sees. Stops at the first step
    whose final answer (local, or escalated) does not verify — that step's
    attempt is still recorded, but nothing downstream is ever attempted on
    top of an unverified finding.
    """
    run_id = run_id or uuid.uuid4().hex[:8]
    context = initial_input
    findings: list[str] = []
    steps: list[PipelineResult] = []

    for i, contract_id in enumerate(contract_sequence):
        step_request_id = f"agent-{run_id}-step{i + 1}-{contract_id.split('.')[-1]}"
        result = pipeline.handle_request(
            task_input=context,
            contract_id=contract_id,
            request_id=step_request_id,
        )
        steps.append(result)

        if not result.verification.passed:
            return AgentRunResult(
                run_id=run_id,
                initial_input=initial_input,
                contract_sequence=contract_sequence,
                completed=False,
                blocked_at=contract_id,
                steps=steps,
            )

        findings.append(f"[{contract_id}] {result.response.parsed}")
        context = initial_input + "\n\nPrior findings:\n" + "\n".join(findings)

    return AgentRunResult(
        run_id=run_id,
        initial_input=initial_input,
        contract_sequence=contract_sequence,
        completed=True,
        steps=steps,
    )


def rows_for_agent_run(
    store: TrajectoryStore, agent_result: AgentRunResult
) -> list[TrajectoryRow]:
    """Every trajectory row (local + any escalated attempts) across every
    step of one agent run, in step order."""
    rows: list[TrajectoryRow] = []
    for step in agent_result.steps:
        rows.extend(store.rows_for_request(step.request_id))
    return rows
