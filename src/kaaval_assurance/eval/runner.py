"""Eval runner: replay gold cases through the assurance pipeline.

Each case becomes one pipeline request with request_id
"eval-<run_id>-<case_id>", so runs stay traceable and replayable from the
trajectory store, and reusing a persistent DB across runs cannot leak
prior-run rows into this run's metrics. Metrics are computed from the
trajectory rows the run wrote — the same telemetry path production requests
use, not a side channel.
"""

import uuid
from typing import Optional

from pydantic import BaseModel

from ..contracts import get_contract
from ..metrics import DEFAULT_EWMA_ALPHA, MetricsReport, aggregate
from ..models import TrajectoryRow
from ..pipeline import AssurancePipeline
from .dataset import EvalCase


class CaseResult(BaseModel):
    case_id: str
    request_id: str
    contract_id: str
    category: str
    passed: bool
    escalated: bool
    attempts: int
    routing_reason: str = ""


class EvalRunReport(BaseModel):
    run_id: str
    n_cases: int
    results: list[CaseResult]
    metrics: MetricsReport


def run_eval(
    pipeline: AssurancePipeline,
    cases: list[EvalCase],
    ewma_alpha: float = DEFAULT_EWMA_ALPHA,
    run_id: Optional[str] = None,
) -> EvalRunReport:
    run_id = run_id or uuid.uuid4().hex[:8]
    results: list[CaseResult] = []
    run_rows: list[TrajectoryRow] = []

    for case in cases:
        request_id = f"eval-{run_id}-{case.case_id}"
        contract = get_contract(case.contract_id, case.contract_version)
        outcome = pipeline.handle_request(
            task_input=case.task_input,
            contract_id=case.contract_id,
            contract_version=case.contract_version,
            request_id=request_id,
        )
        results.append(
            CaseResult(
                case_id=case.case_id,
                request_id=request_id,
                contract_id=case.contract_id,
                category=contract.category,
                passed=outcome.verification.passed,
                escalated=outcome.escalated,
                attempts=outcome.attempts,
                routing_reason=outcome.routing.reason,
            )
        )
        run_rows.extend(pipeline.store.rows_for_request(request_id))

    metrics = aggregate(run_rows, alpha=ewma_alpha)
    return EvalRunReport(
        run_id=run_id, n_cases=len(cases), results=results, metrics=metrics
    )
