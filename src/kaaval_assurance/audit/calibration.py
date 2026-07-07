"""Challenger false-positive calibration: the hard gate before trust.

Run the challenger against known-good gold answers. Every fail verdict
against a gold answer is a false positive ("critic finds something because
it was told to critique"). If the false-positive rate exceeds the threshold,
calibration fails and audit results must not be trusted as a routing signal.
"""

from ..contracts import get_contract
from ..eval.dataset import EvalCase
from .challenger import AuditChallenger
from .models import AuditCalibrationReport

DEFAULT_CALIBRATION_THRESHOLD = 0.20


def calibrate_challenger(
    challenger: AuditChallenger,
    cases: list[EvalCase],
    threshold: float = DEFAULT_CALIBRATION_THRESHOLD,
) -> AuditCalibrationReport:
    gold_cases = [c for c in cases if c.gold_answer]
    false_positives = 0
    parse_errors = 0
    flagged: list[str] = []

    for case in gold_cases:
        contract = get_contract(case.contract_id, case.contract_version)
        result = challenger.challenge(
            request_id=f"calibration-{case.case_id}",
            task_input=case.task_input,
            accepted_answer=case.gold_answer,
            contract=contract,
        )
        if result.result == "fail":
            false_positives += 1
            flagged.append(case.case_id)
        elif result.result == "error":
            parse_errors += 1

    total = len(gold_cases)
    rate = false_positives / total if total else 0.0
    status = "passed" if rate <= threshold and parse_errors == 0 else "failed"
    return AuditCalibrationReport(
        total_gold=total,
        false_positives=false_positives,
        false_positive_rate=rate,
        threshold=threshold,
        status=status,
        parse_errors=parse_errors,
        flagged_case_ids=flagged,
    )


def skipped_calibration(
    threshold: float = DEFAULT_CALIBRATION_THRESHOLD,
) -> AuditCalibrationReport:
    """Explicit skip marker for local development. Skipped is not passed:
    audit results stay untrusted."""
    return AuditCalibrationReport(
        total_gold=0,
        false_positives=0,
        false_positive_rate=0.0,
        threshold=threshold,
        status="skipped",
    )
