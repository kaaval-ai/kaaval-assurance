"""K Top CLI, rendering, filtering, and transport behavior."""

import json

import pytest

from kaaval_assurance.cli import main
from kaaval_assurance.top import (
    HttpSnapshotSource,
    SourceError,
    _safe_endpoint,
    demo_snapshot,
    filter_decisions,
    move_selection,
    render_lines,
    selection_for_decision,
)


def test_demo_contains_each_terminal_teaching_state():
    snapshot = demo_snapshot()
    assert snapshot.provenance == "sample"
    assert snapshot.authority == "display_only"
    assert all(item.authority == "display_only" for item in snapshot.decisions)
    assert {decision.final_outcome for decision in snapshot.decisions} == {
        "conformant",
        "recovered",
        "no_safe_answer",
        "provider_error",
    }


@pytest.mark.parametrize("width", [80, 120, 160])
def test_renderer_is_truthful_and_content_free_at_supported_widths(width):
    output = "\n".join(
        render_lines(
            demo_snapshot(),
            width=width,
            height=36,
            endpoint="demo://local",
        )
    )
    assert "K TOP" in output
    assert "SAMPLE" in output
    assert "DISPLAY ONLY" in output
    assert "Final contract-conformance" in output
    assert "not model accuracy" in output
    assert "CONTENT WITHHELD" in output
    assert "raw_text" not in output
    assert "correct" not in output.lower()
    assert "trusted" not in output.lower()
    assert all(len(line) <= max(40, width) for line in output.splitlines())


def test_filter_matches_contract_model_outcome_and_failure_id():
    snapshot = demo_snapshot()
    assert len(filter_decisions(snapshot, "support.refund")) == 2
    assert len(filter_decisions(snapshot, "llama3.2")) == 2
    assert len(filter_decisions(snapshot, "provider error")) == 1
    assert len(filter_decisions(snapshot, "consequential_damages")) == 1
    assert filter_decisions(snapshot, "does-not-exist") == []


def test_selection_is_bounded():
    assert move_selection(0, -1, 4) == 0
    assert move_selection(0, 2, 4) == 2
    assert move_selection(3, 1, 4) == 3
    assert move_selection(10, 0, 0) == 0


def test_selection_tracks_decision_identity_when_new_rows_prepend():
    snapshot = demo_snapshot()
    selected_id = snapshot.decisions[2].decision_id
    prepended = snapshot.decisions[0].model_copy(
        update={"decision_id": "newer-decision"}
    )
    updated = snapshot.model_copy(
        update={"decisions": [prepended, *snapshot.decisions]}
    )
    assert selection_for_decision(updated, "", selected_id, fallback=2) == 3


def test_viewport_keeps_selected_row_visible():
    snapshot = demo_snapshot()
    base = snapshot.decisions[0]
    decisions = [
        base.model_copy(update={"decision_id": f"decision-{index:03d}"})
        for index in range(50)
    ]
    large = snapshot.model_copy(update={"decisions": decisions})
    output = "\n".join(
        render_lines(
            large,
            width=80,
            height=24,
            selected=49,
            endpoint="demo://local",
        )
    )
    assert "decision-049" in output
    assert "decision-000" not in output
    assert "rows 39-50/50" in output


def test_inspector_keeps_full_two_attempt_failure_path_at_80_by_24():
    lines = render_lines(
        demo_snapshot(),
        width=80,
        height=24,
        selected=2,
        detail=True,
        endpoint="demo://local",
    )
    output = "\n".join(lines)
    assert "#1 local/ollama" in output
    assert "range:refund_amount_usd" in output
    assert "#2 remote/fireworks" in output
    assert "grounding:consequential_damages_requires_human" in output
    assert "raw content WITHHELD" in output
    assert len(lines) <= 24


def test_once_command_renders_and_returns(capsys):
    assert main(["top", "--demo", "--once", "--width", "120"]) == 0
    output = capsys.readouterr().out
    assert "RECOVERED" in output
    assert "NO SAFE" in output
    assert "PROVIDER ERROR" in output


def test_json_command_is_machine_readable(capsys):
    assert main(["top", "--demo", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["schema_version"] == "0.1"
    assert payload["provenance"] == "sample"
    assert payload["totals"]["decisions"] == 4


def test_endpoint_rejects_visible_credentials_and_query_strings():
    with pytest.raises(SourceError, match="credentials"):
        _safe_endpoint("https://user:secret@example.com")
    with pytest.raises(SourceError, match="query"):
        _safe_endpoint("https://example.com?api_key=secret")
    with pytest.raises(SourceError, match="invalid port"):
        _safe_endpoint("http://localhost:not-a-port")


def test_api_key_is_not_sent_to_remote_plain_http(monkeypatch):
    monkeypatch.setenv("KAAVAL_API_KEY", "secret")
    with pytest.raises(SourceError, match="non-loopback HTTP"):
        HttpSnapshotSource("http://example.com")
    local = HttpSnapshotSource("http://127.0.0.1:8000")
    assert local.headers["Authorization"] == "Bearer secret"


def test_renderer_strips_terminal_control_sequences():
    snapshot = demo_snapshot()
    poisoned_attempt = snapshot.decisions[0].attempts[0].model_copy(
        update={"model_id": "model\x1b]0;PWNED\x07"}
    )
    poisoned_decision = snapshot.decisions[0].model_copy(
        update={
            "contract_id": "contract\x1b[31m-red",
            "attempts": [poisoned_attempt],
        }
    )
    poisoned = snapshot.model_copy(update={"decisions": [poisoned_decision]})
    output = "\n".join(
        render_lines(poisoned, width=120, height=24, endpoint="demo://local")
    )
    assert "\x1b" not in output
    assert "\x07" not in output


def test_http_source_accepts_additive_fields(monkeypatch):
    payload = demo_snapshot().model_dump(mode="json")
    payload["future_additive_field"] = "ignored"

    class Response:
        status_code = 200

        def json(self):
            return payload

    source = HttpSnapshotSource("http://127.0.0.1:8000")
    monkeypatch.setattr(source.session, "get", lambda *args, **kwargs: Response())
    assert source.fetch().totals.decisions == 4


def test_http_source_rejects_incompatible_payload_without_echoing_it(monkeypatch):
    class Response:
        status_code = 200

        def json(self):
            return {"schema_version": "99.0", "secret": "DO-NOT-ECHO"}

    source = HttpSnapshotSource("http://127.0.0.1:8000")
    monkeypatch.setattr(source.session, "get", lambda *args, **kwargs: Response())
    with pytest.raises(SourceError) as exc:
        source.fetch()
    assert "DO-NOT-ECHO" not in str(exc.value)
