"""Operations schema and aggregation tests for K Top's public data seam."""

from datetime import datetime, timedelta, timezone

from kaaval_assurance.models import TrajectoryRow
from kaaval_assurance.ops import (
    OpsRoutingState,
    OpsSessionInput,
    build_ops_snapshot,
)


NOW = datetime(2026, 7, 13, 18, 0, tzinfo=timezone.utc)


def row(
    request_id: str,
    *,
    passed: bool,
    tier: str = "local",
    escalated: bool = False,
    failures: list[str] | None = None,
    status: str = "completed",
    task_input: str = "SENSITIVE-TASK-CONTENT",
    raw_text: str = "SENSITIVE-MODEL-CONTENT",
) -> TrajectoryRow:
    return TrajectoryRow(
        request_id=request_id,
        ts=NOW,
        category="refund_decision",
        contract_id="support.refund_decision",
        contract_version="1.0",
        tier=tier,
        provider="mock-local" if tier == "local" else "mock-remote",
        model_id="small" if tier == "local" else "strong",
        verifier_passed=passed,
        verifier_failures=failures or [],
        escalated=escalated,
        latency_ms=10.0,
        cost_usd=0.01,
        prompt_tokens=12,
        completion_tokens=4,
        task_input=task_input,
        raw_text=raw_text,
        attempt_status=status,
        error_type="ConnectionError" if status == "provider_error" else None,
        error_message="SENSITIVE-UPSTREAM-ERROR" if status == "provider_error" else None,
    )


def test_snapshot_maps_attempts_to_honest_terminal_outcomes():
    rows = [
        row("accepted", passed=True),
        row("rescued", passed=False, failures=["range:refund_amount_usd"]),
        row("rescued", passed=True, tier="remote", escalated=True),
        row("no-safe", passed=False, failures=["enum:decision"]),
        row(
            "no-safe",
            passed=False,
            tier="remote",
            escalated=True,
            failures=["grounding:human_review"],
        ),
        row("provider-error", passed=False, failures=["transport:TimeoutError"]),
        row(
            "provider-error",
            passed=False,
            tier="remote",
            escalated=True,
            failures=["transport:ConnectionError"],
            status="provider_error",
        ),
    ]
    snapshot = build_ops_snapshot(
        [
            OpsSessionInput(
                session_id="session-1",
                rows=rows,
                routing=[
                    OpsRoutingState(
                        session_id="session-1",
                        category="refund_decision",
                        verifier_failure_ewma=0.51,
                        action="force_remote",
                        reason="test policy",
                    )
                ],
            )
        ],
        runtime_version="0.1.0",
        deployment_mode="local",
        live_runs_enabled=True,
        generated_at=NOW + timedelta(seconds=10),
    )

    outcomes = {item.decision_id: item.final_outcome for item in snapshot.decisions}
    assert outcomes == {
        "accepted": "conformant",
        "rescued": "recovered",
        "no-safe": "no_safe_answer",
        "provider-error": "provider_error",
    }
    assert snapshot.totals.decisions == 4
    assert snapshot.totals.attempts == 7
    assert snapshot.totals.final_contract_conformance_rate == 0.5
    assert snapshot.totals.recovered == 1
    assert snapshot.totals.no_safe_answer == 1
    assert snapshot.totals.provider_errors == 1
    assert snapshot.totals.escalations == 3
    assert snapshot.routing[0].verifier_failure_ewma == 0.51


def test_snapshot_is_content_free_even_when_receipts_contain_sensitive_values():
    sensitive = row("r", passed=True)
    sensitive.model_id = "/Users/private-team/models/gemma-secret"
    snapshot = build_ops_snapshot(
        [OpsSessionInput(session_id="s", rows=[sensitive])],
        runtime_version="0.1.0",
        deployment_mode="local",
        live_runs_enabled=True,
        generated_at=NOW,
    )

    payload = snapshot.model_dump_json()
    assert "SENSITIVE-TASK-CONTENT" not in payload
    assert "SENSITIVE-MODEL-CONTENT" not in payload
    assert "SENSITIVE-UPSTREAM-ERROR" not in payload
    assert "task_input" not in payload
    assert "raw_text" not in payload
    assert "error_message" not in payload
    assert "/Users/private-team" not in payload
    assert snapshot.decisions[0].attempts[0].model_id == (
        "local-model:gemma-secret"
    )
    assert snapshot.decisions[0].content_redaction == "withheld"


def test_path_shaped_model_ids_are_reduced_to_safe_display_identity():
    model_ids = [
        "file:///Users/alice/private/model-a",
        "./private/model-b",
        "../private/model-c",
        r"C:\\private\\model-d",
        "http://[invalid-model-url",
        r"file:C:\\private\\model-e",
    ]
    rows = []
    for index, model_id in enumerate(model_ids):
        item = row(f"request-{index}", passed=True)
        item.model_id = model_id
        rows.append(item)
    snapshot = build_ops_snapshot(
        [OpsSessionInput(session_id="s", rows=rows)],
        runtime_version="0.1.0",
        deployment_mode="local",
        live_runs_enabled=True,
        generated_at=NOW,
    )

    public_ids = {
        attempt.model_id
        for decision in snapshot.decisions
        for attempt in decision.attempts
    }
    assert public_ids == {
        "local-model:model-a",
        "local-model:model-b",
        "local-model:model-c",
        "local-model:model-d",
        "redacted-model-id",
        "local-model:model-e",
    }


def test_empty_snapshot_uses_unavailable_for_rates_and_latency():
    snapshot = build_ops_snapshot(
        [],
        runtime_version="0.1.0",
        deployment_mode="local",
        live_runs_enabled=False,
        generated_at=NOW,
    )

    assert snapshot.totals.decisions == 0
    assert snapshot.totals.final_contract_conformance_rate is None
    assert snapshot.totals.p95_recorded_model_call_latency_sum_ms is None
    assert snapshot.provenance == "live"
    assert snapshot.authority == "unavailable"
    assert snapshot.service.execution_mode == "unavailable"


def test_legacy_naive_receipt_timestamp_is_normalized_to_utc():
    legacy = row("legacy", passed=True)
    legacy.ts = NOW.replace(tzinfo=None)
    snapshot = build_ops_snapshot(
        [OpsSessionInput(session_id="legacy-session", rows=[legacy])],
        runtime_version="0.1.0",
        deployment_mode="local",
        live_runs_enabled=True,
        generated_at=NOW,
    )

    assert snapshot.decisions[0].timestamp.tzinfo == timezone.utc
    assert snapshot.totals.calls_last_minute == 1


def test_truncated_window_marks_window_metrics_and_calls_per_minute_unavailable():
    snapshot = build_ops_snapshot(
        [
            OpsSessionInput(
                session_id="busy",
                rows=[row("recent", passed=True)],
                window_truncated=True,
            )
        ],
        runtime_version="0.1.0",
        deployment_mode="local",
        live_runs_enabled=True,
        generated_at=NOW,
    )

    assert snapshot.totals.decision_window_truncated is True
    assert snapshot.totals.calls_last_minute is None
    assert snapshot.totals.decisions == 1
