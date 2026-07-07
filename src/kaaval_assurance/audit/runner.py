"""Sampled offline audit over accepted answers from an eval run.

Runs after the live path has completed — it never gates a response. Only
Layer-1-passing final attempts are eligible; a seeded RNG samples them at
the configured rate; results persist into the trajectory audit columns.

Audit results feed Layer-2 EWMA only when calibration passed (trusted=True),
and that feed is a separate, later step — this runner reports and persists,
nothing else.
"""

import json
import random
from collections import Counter
from typing import Optional

from ..contracts import get_contract
from ..models import TrajectoryRow
from ..trajectory import TrajectoryStore
from .challenger import AuditChallenger
from .models import AuditCalibrationReport, AuditResult, AuditRunSummary

DEFAULT_SAMPLE_RATE = 0.10


def _final_accepted(rows: list[TrajectoryRow]) -> list[TrajectoryRow]:
    """Final attempt per request, kept only when it passed Layer 1."""
    by_request: dict[str, TrajectoryRow] = {}
    for row in rows:
        by_request[row.request_id] = row  # rows arrive id-ordered; last wins
    return [r for r in by_request.values() if r.verifier_passed]


def run_sampled_audit(
    store: TrajectoryStore,
    rows: list[TrajectoryRow],
    challenger: AuditChallenger,
    calibration: AuditCalibrationReport,
    sample_rate: float = DEFAULT_SAMPLE_RATE,
    seed: int = 0,
) -> tuple[AuditRunSummary, list[AuditResult]]:
    accepted = _final_accepted(rows)
    rng = random.Random(seed)
    sampled_rows = [r for r in accepted if rng.random() < sample_rate]

    results: list[AuditResult] = []
    severity_counts: Counter = Counter()
    for row in sampled_rows:
        try:
            answer = json.loads(row.raw_text)
        except json.JSONDecodeError:
            continue  # cannot happen for Layer-1-passing rows; defensive skip
        contract = get_contract(row.contract_id, row.contract_version)
        result = challenger.challenge(
            request_id=row.request_id,
            task_input=row.task_input,
            accepted_answer=answer,
            contract=contract,
        )
        results.append(result)
        for violation in result.violations:
            severity_counts[violation.severity] += 1
        if row.db_id is not None:
            store.update_audit(
                row.db_id,
                audit_result=result.result,
                audit_violations=[v.model_dump() for v in result.violations],
            )

    total_cost = sum(r.cost_usd for r in results)
    passed = sum(1 for r in results if r.result == "pass")
    failed = sum(1 for r in results if r.result == "fail")
    errors = sum(1 for r in results if r.result == "error")

    summary = AuditRunSummary(
        audit_provider=challenger.challenger_name,
        audit_model_id=challenger.model_id,
        trusted=calibration.status == "passed",
        calibration=calibration,
        sample_rate=sample_rate,
        seed=seed,
        accepted_answers=len(accepted),
        sampled=len(results),
        passed=passed,
        failed=failed,
        errors=errors,
        violations_by_severity=dict(severity_counts),
        total_cost_usd=total_cost,
        cost_per_sampled_usd=total_cost / len(results) if results else None,
        cost_per_verified_accepted_usd=(
            total_cost / len(accepted) if accepted else None
        ),
        audit_tokens=sum(r.prompt_tokens + r.completion_tokens for r in results),
    )
    return summary, results
