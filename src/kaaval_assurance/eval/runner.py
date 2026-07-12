"""Eval runner: replay reference-answer cases through the assurance pipeline.

Each case becomes one pipeline request with request_id
"eval-<run_id>-<case_id>", so runs stay traceable and replayable from the
trajectory store, and reusing a persistent DB across runs cannot leak
prior-run rows into this run's metrics. Metrics are computed from the
trajectory rows the run wrote — the same telemetry path production requests
use, not a side channel.
"""

import uuid
from typing import Optional

from pydantic import BaseModel, Field

from ..audit.models import AuditRunSummary
from ..contracts import get_contract
from ..metrics import DEFAULT_EWMA_ALPHA, MetricsReport, aggregate
from ..models import TrajectoryRow
from ..pipeline import AssurancePipeline
from .dataset import EvalCase
from .scoring import score_against_gold


class CaseResult(BaseModel):
    case_id: str
    request_id: str
    contract_id: str
    category: str
    status: str = "accepted"
    # Backward-compatible alias: passed means Layer-1 contract conformance,
    # never semantic or task correctness.
    passed: bool
    contract_conformant: bool
    gold_scored: bool = False
    gold_correct: Optional[bool] = None
    gold_compared_fields: list[str] = Field(default_factory=list)
    gold_mismatches: list[str] = Field(default_factory=list)
    escalated: bool
    attempts: int
    routing_reason: str = ""


class EvalRunReport(BaseModel):
    run_id: str
    n_cases: int
    results: list[CaseResult]
    metrics: MetricsReport
    gold_scored_cases: int = 0
    gold_correct_cases: int = 0
    gold_accuracy: Optional[float] = None
    false_accept_count: int = 0
    false_accept_rate: Optional[float] = None
    false_reject_count: int = 0
    false_reject_rate: Optional[float] = None
    # Layer 3 offline sampled audit summary, attached after the run when audit
    # is enabled. Reporting only — it never alters metrics above.
    audit: Optional[AuditRunSummary] = None


def run_eval(
    pipeline: AssurancePipeline,
    cases: list[EvalCase],
    ewma_alpha: float = DEFAULT_EWMA_ALPHA,
    run_id: Optional[str] = None,
) -> EvalRunReport:
    run_id = run_id or uuid.uuid4().hex[:8]
    results: list[CaseResult] = []
    run_rows: list[TrajectoryRow] = []

    # A batch eval run reports Layer-2 metrics against a fixed routing
    # policy for the whole dataset — it must not let the router's online
    # closure (record_signal) adapt mid-replay, or metrics would reflect a
    # moving target instead of one policy. Live per-request adaptation is a
    # pipeline.handle_request() concern; restore the router's own setting
    # once the batch finishes.
    router = pipeline.router
    prior_online_adaptation = router.online_adaptation
    router.online_adaptation = False
    try:
        for case in cases:
            request_id = f"eval-{run_id}-{case.case_id}"
            contract = get_contract(case.contract_id, case.contract_version)
            outcome = pipeline.handle_request(
                task_input=case.task_input,
                contract_id=case.contract_id,
                contract_version=case.contract_version,
                request_id=request_id,
            )
            gold_score = score_against_gold(
                outcome.response.parsed, case.gold_answer, contract
            )
            results.append(
                CaseResult(
                    case_id=case.case_id,
                    request_id=request_id,
                    contract_id=case.contract_id,
                    category=contract.category,
                    status=outcome.status,
                    passed=outcome.verification.passed,
                    contract_conformant=outcome.verification.passed,
                    gold_scored=gold_score.scored,
                    gold_correct=gold_score.correct,
                    gold_compared_fields=gold_score.compared_fields,
                    gold_mismatches=gold_score.mismatches,
                    escalated=outcome.escalated,
                    attempts=outcome.attempts,
                    routing_reason=outcome.routing.reason,
                )
            )
            run_rows.extend(pipeline.store.rows_for_request(request_id))
    finally:
        router.online_adaptation = prior_online_adaptation

    metrics = aggregate(run_rows, alpha=ewma_alpha)
    scored = [result for result in results if result.gold_scored]
    correct = [result for result in scored if result.gold_correct is True]
    false_accepts = [
        result
        for result in scored
        if result.contract_conformant and result.gold_correct is False
    ]
    false_rejects = [
        result
        for result in scored
        if not result.contract_conformant and result.gold_correct is True
    ]
    return EvalRunReport(
        run_id=run_id,
        n_cases=len(cases),
        results=results,
        metrics=metrics,
        gold_scored_cases=len(scored),
        gold_correct_cases=len(correct),
        gold_accuracy=len(correct) / len(scored) if scored else None,
        false_accept_count=len(false_accepts),
        false_accept_rate=len(false_accepts) / len(scored) if scored else None,
        false_reject_count=len(false_rejects),
        false_reject_rate=len(false_rejects) / len(scored) if scored else None,
    )
