"""End-to-end mock path: the Jul 5 deliverable proof.

Zero cloud access: MockProvider both tiers, in-memory SQLite.
"""

import pytest

from kaaval_assurance.pipeline import AssurancePipeline
from kaaval_assurance.providers import MockProvider
from kaaval_assurance.router import Router
from kaaval_assurance.trajectory import TrajectoryStore

INCIDENT = (
    "Core router CR-04 dropped all BGP sessions at 02:13; downstream OLT sites "
    "in region south lost upstream connectivity. Customer impact confirmed."
)


@pytest.fixture()
def store():
    s = TrajectoryStore(":memory:")
    yield s
    s.close()


def make_pipeline(store, local_failure=None):
    return AssurancePipeline(
        router=Router(),
        local_provider=MockProvider(tier="local", failure_mode=local_failure),
        remote_provider=MockProvider(tier="remote", model_id="mock-remote-strong"),
        store=store,
    )


def test_happy_path_local_pass(store):
    pipeline = make_pipeline(store)
    result = pipeline.handle_request(INCIDENT, "telecom.severity_classification")

    assert result.verification.passed
    assert not result.escalated
    assert result.attempts == 1
    assert result.response.tier == "local"
    assert "local" in result.routing.reason

    rows = store.rows_for_request(result.request_id)
    assert len(rows) == 1
    assert rows[0].verifier_passed
    assert rows[0].category == "severity_classification"
    assert rows[0].task_input == INCIDENT  # replayable
    assert rows[0].raw_text == result.response.raw_text
    assert rows[0].audit_sampled is False and rows[0].audit_violations is None


def test_local_failure_escalates_to_remote(store):
    pipeline = make_pipeline(store, local_failure="missing_field")
    result = pipeline.handle_request(INCIDENT, "telecom.severity_classification")

    assert result.escalated
    assert result.attempts == 2
    assert result.verification.passed  # remote attempt passes
    assert result.response.tier == "remote"
    assert "layer-1 verification failed" in result.routing.reason

    rows = store.rows_for_request(result.request_id)
    assert len(rows) == 2
    local_row, remote_row = rows
    assert local_row.tier == "local" and not local_row.verifier_passed
    assert local_row.verifier_failures  # failed check IDs recorded
    assert remote_row.tier == "remote" and remote_row.verifier_passed
    assert remote_row.escalated


def test_unparseable_local_output_escalates(store):
    pipeline = make_pipeline(store, local_failure="unparseable")
    result = pipeline.handle_request(INCIDENT, "telecom.next_action_recommendation")

    assert result.escalated
    rows = store.rows_for_request(result.request_id)
    assert rows[0].verifier_failures == ["json_parse"]


def test_all_four_contracts_run_end_to_end(store):
    pipeline = make_pipeline(store)
    for contract_id in [
        "telecom.severity_classification",
        "telecom.component_extraction",
        "telecom.incident_summary",
        "telecom.next_action_recommendation",
    ]:
        result = pipeline.handle_request(INCIDENT, contract_id)
        assert result.verification.passed, contract_id
    assert store.count() == 4


def test_category_query_supports_trend_seam(store):
    pipeline = make_pipeline(store, local_failure="bad_enum")
    for _ in range(3):
        pipeline.handle_request(INCIDENT, "telecom.severity_classification")

    rows = store.rows_for_category("severity_classification")
    # Online Layer-2 EWMA closure (Router.record_signal, alpha 0.3) is live
    # on a default Router: request 1 fails local (drift 0.00 -> 0.30,
    # escalates), request 2 fails local again (drift 0.30 -> 0.51,
    # escalates), request 3 is pre-routed straight to remote (drift >= 0.50)
    # with no local attempt at all. 2 local + 2 remote + 1 remote-only = 5.
    assert len(rows) == 5
    local_fails = [r for r in rows if r.tier == "local" and not r.verifier_passed]
    assert len(local_fails) == 2  # the 3rd request never attempts local
