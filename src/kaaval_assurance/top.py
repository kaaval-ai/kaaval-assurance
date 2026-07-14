"""K Top: a read-only terminal view of Kaaval assured decisions.

This quick MVP deliberately consumes the public operations snapshot. It does
not import the verifier, router, providers, or trajectory store, and it never
requests or renders prompt/response content.
"""

from __future__ import annotations

import json
import ipaddress
import os
import queue
import shutil
import sys
import threading
import time
import unicodedata
from datetime import datetime, timezone
from typing import Protocol
from urllib.parse import urlsplit, urlunsplit

import requests
from pydantic import ValidationError

from .ops import (
    OpsAttempt,
    OpsDecision,
    OpsRoutingState,
    OpsService,
    OpsSnapshot,
    OpsTotals,
)


class SnapshotSource(Protocol):
    label: str

    def fetch(self) -> OpsSnapshot: ...


class SourceError(RuntimeError):
    """Safe, user-facing source error with no upstream response content."""


def _terminal_text(value: str) -> str:
    """Remove terminal controls and invisible formatting from untrusted text."""

    cleaned = []
    for character in value:
        if character in "\r\n\t":
            cleaned.append(" ")
        elif unicodedata.category(character) in {"Cc", "Cf", "Cs"}:
            continue
        else:
            cleaned.append(character)
    return "".join(cleaned)


def _safe_endpoint(endpoint: str) -> tuple[str, str]:
    value = endpoint.strip()
    if _terminal_text(value) != value:
        raise SourceError("endpoint contains terminal control characters")
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise SourceError("endpoint must be an http:// or https:// URL")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise SourceError(
            "endpoint must not contain credentials, query parameters, or a fragment"
        )
    try:
        parsed_port = parsed.port
    except ValueError:
        raise SourceError("endpoint contains an invalid port") from None
    port = f":{parsed_port}" if parsed_port is not None else ""
    host = parsed.hostname or ""
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    safe_netloc = f"{host}{port}"
    base_path = parsed.path.rstrip("/")
    if base_path.endswith("/api/ops/snapshot"):
        path = base_path
    else:
        path = f"{base_path}/api/ops/snapshot"
    url = urlunsplit((parsed.scheme, safe_netloc, path, "", ""))
    label = urlunsplit((parsed.scheme, safe_netloc, base_path or "/", "", ""))
    return url, label


class HttpSnapshotSource:
    def __init__(self, endpoint: str, timeout_seconds: float = 5.0):
        self.url, self.label = _safe_endpoint(endpoint)
        self.timeout_seconds = timeout_seconds
        self.session = requests.Session()
        api_key = os.environ.get("KAAVAL_API_KEY")
        parsed = urlsplit(self.url)
        host = parsed.hostname or ""
        try:
            loopback = ipaddress.ip_address(host).is_loopback
        except ValueError:
            loopback = host.lower() == "localhost"
        if api_key and parsed.scheme != "https" and not loopback:
            raise SourceError(
                "refusing to send KAAVAL_API_KEY to a non-loopback HTTP endpoint"
            )
        self.headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}

    def fetch(self) -> OpsSnapshot:
        try:
            response = self.session.get(
                self.url,
                headers=self.headers,
                timeout=self.timeout_seconds,
            )
        except requests.RequestException as exc:
            raise SourceError(
                f"cannot reach {self.label} ({type(exc).__name__})"
            ) from None
        if response.status_code != 200:
            raise SourceError(
                f"{self.label} returned HTTP {response.status_code}"
            )
        try:
            payload = response.json()
            return OpsSnapshot.model_validate(payload)
        except (ValueError, ValidationError):
            raise SourceError(
                f"{self.label} returned an incompatible operations snapshot"
            ) from None


def _attempt(
    ordinal: int,
    timestamp: datetime,
    provider: str,
    model_id: str,
    tier: str,
    *,
    passed: bool,
    failures: list[str] | None = None,
    escalated: bool = False,
    latency_ms: float = 0.0,
    status: str = "completed",
    error_type: str | None = None,
) -> OpsAttempt:
    return OpsAttempt(
        ordinal=ordinal,
        timestamp=timestamp,
        provider=provider,
        model_id=model_id,
        tier=tier,
        attempt_status=status,
        contract_conformant=passed,
        failed_check_ids=failures or [],
        escalated=escalated,
        latency_ms=latency_ms,
        prompt_tokens=80,
        completion_tokens=24,
        recorded_cost_usd=0.0,
        error_type=error_type,
    )


def demo_snapshot() -> OpsSnapshot:
    """Deterministic, content-free SAMPLE fixture for immediate first value."""

    ts = datetime(2026, 7, 13, 16, 5, tzinfo=timezone.utc)
    decisions = [
        OpsDecision(
            decision_id="demo-conformant-001",
            session_id="demo-session",
            timestamp=ts,
            category="severity_classification",
            contract_id="telecom.severity_classification",
            contract_version="1.0",
            final_outcome="conformant",
            provenance="sample",
            authority="display_only",
            attempts=[
                _attempt(
                    1,
                    ts,
                    "vllm-gemma",
                    "gemma-3-1b-it",
                    "local",
                    passed=True,
                    latency_ms=83.0,
                )
            ],
            recorded_model_call_latency_sum_ms=83.0,
            recorded_cost_usd=0.0,
        ),
        OpsDecision(
            decision_id="demo-recovered-002",
            session_id="demo-session",
            timestamp=ts,
            category="refund_decision",
            contract_id="support.refund_decision",
            contract_version="1.0",
            final_outcome="recovered",
            provenance="sample",
            authority="display_only",
            attempts=[
                _attempt(
                    1,
                    ts,
                    "ollama",
                    "llama3.2:1b",
                    "local",
                    passed=False,
                    failures=["range:refund_amount_usd"],
                    latency_ms=91.0,
                ),
                _attempt(
                    2,
                    ts,
                    "fireworks",
                    "accounts/fireworks/models/kimi-k2p6",
                    "remote",
                    passed=True,
                    escalated=True,
                    latency_ms=207.0,
                ),
            ],
            recorded_model_call_latency_sum_ms=298.0,
            recorded_cost_usd=0.0,
        ),
        OpsDecision(
            decision_id="demo-no-safe-003",
            session_id="demo-session",
            timestamp=ts,
            category="refund_decision",
            contract_id="support.refund_decision",
            contract_version="1.0",
            final_outcome="no_safe_answer",
            provenance="sample",
            authority="display_only",
            attempts=[
                _attempt(
                    1,
                    ts,
                    "ollama",
                    "llama3.2:1b",
                    "local",
                    passed=False,
                    failures=["range:refund_amount_usd"],
                    latency_ms=88.0,
                ),
                _attempt(
                    2,
                    ts,
                    "fireworks",
                    "accounts/fireworks/models/kimi-k2p6",
                    "remote",
                    passed=False,
                    failures=[
                        "grounding:consequential_damages_requires_human"
                    ],
                    escalated=True,
                    latency_ms=302.0,
                ),
            ],
            recorded_model_call_latency_sum_ms=390.0,
            recorded_cost_usd=0.0,
        ),
        OpsDecision(
            decision_id="demo-provider-error-004",
            session_id="demo-session",
            timestamp=ts,
            category="severity_classification",
            contract_id="telecom.severity_classification",
            contract_version="1.0",
            final_outcome="provider_error",
            provenance="sample",
            authority="display_only",
            attempts=[
                _attempt(
                    1,
                    ts,
                    "vllm-gemma",
                    "gemma-3-1b-it",
                    "local",
                    passed=False,
                    failures=["transport:TimeoutError"],
                    latency_ms=1000.0,
                    status="provider_error",
                    error_type="TimeoutError",
                ),
                _attempt(
                    2,
                    ts,
                    "fireworks",
                    "accounts/fireworks/models/kimi-k2p6",
                    "remote",
                    passed=False,
                    failures=["transport:ConnectionError"],
                    escalated=True,
                    latency_ms=500.0,
                    status="provider_error",
                    error_type="ConnectionError",
                ),
            ],
            recorded_model_call_latency_sum_ms=1500.0,
            recorded_cost_usd=0.0,
        ),
    ]
    return OpsSnapshot(
        generated_at=ts,
        provenance="sample",
        authority="display_only",
        service=OpsService(
            runtime_version="0.1.0-demo",
            deployment_mode="local-demo",
            live_runs_enabled=False,
            execution_mode="unavailable",
        ),
        totals=OpsTotals(
            sessions=1,
            decisions=4,
            attempts=7,
            calls_last_minute=4,
            final_contract_conformance_rate=0.5,
            recovered=1,
            no_safe_answer=1,
            provider_errors=1,
            escalations=3,
            p95_recorded_model_call_latency_sum_ms=1333.5,
            recorded_cost_usd=0.0,
        ),
        routing=[
            OpsRoutingState(
                session_id="demo-session",
                category="refund_decision",
                verifier_failure_ewma=0.51,
                action="force_remote",
                reason="recent local contract failures crossed the 0.50 policy band",
            ),
            OpsRoutingState(
                session_id="demo-session",
                category="severity_classification",
                verifier_failure_ewma=0.30,
                action="tightened",
                reason="recent local contract failures are under tightened watch",
            ),
        ],
        decisions=decisions,
    )


class DemoSnapshotSource:
    label = "demo://local"

    def fetch(self) -> OpsSnapshot:
        return demo_snapshot()


OUTCOME_LABELS = {
    "conformant": "CONFORMANT",
    "recovered": "RECOVERED",
    "no_safe_answer": "NO SAFE",
    "provider_error": "PROVIDER ERROR",
    "unknown": "UNKNOWN",
}


def filter_decisions(snapshot: OpsSnapshot, query: str) -> list[OpsDecision]:
    needle = query.strip().lower()
    if not needle:
        return list(snapshot.decisions)
    matches = []
    for decision in snapshot.decisions:
        values = [
            decision.decision_id,
            decision.session_id,
            decision.category,
            decision.contract_id,
            decision.contract_version,
            decision.final_outcome,
            OUTCOME_LABELS[decision.final_outcome],
        ]
        for attempt in decision.attempts:
            values.extend(
                [
                    attempt.provider,
                    attempt.model_id,
                    attempt.tier,
                    attempt.attempt_status,
                    *(attempt.failed_check_ids),
                ]
            )
        if needle in " ".join(values).lower():
            matches.append(decision)
    return matches


def move_selection(current: int, delta: int, count: int) -> int:
    if count <= 0:
        return 0
    return max(0, min(count - 1, current + delta))


def selection_for_decision(
    snapshot: OpsSnapshot,
    query: str,
    decision_id: str | None,
    fallback: int = 0,
) -> int:
    visible = filter_decisions(snapshot, query)
    if decision_id is not None:
        for index, decision in enumerate(visible):
            if decision.decision_id == decision_id:
                return index
    return move_selection(fallback, 0, len(visible))


def _viewport_start(selected: int, count: int, capacity: int) -> int:
    if count <= capacity or capacity <= 0:
        return 0
    return min(max(0, selected - capacity + 1), count - capacity)


def _fit(value: str, width: int) -> str:
    value = _terminal_text(value)
    if width <= 0:
        return ""
    if len(value) <= width:
        return value
    if width == 1:
        return value[:1]
    return value[: width - 1] + "…"


def _short_id(value: str, width: int = 12) -> str:
    if len(value) <= width:
        return value
    return value[: max(1, width - 1)] + "…"


def _path(decision: OpsDecision) -> str:
    return ">".join("L" if attempt.tier == "local" else "R" for attempt in decision.attempts)


def _rate(value: float | None) -> str:
    return "unavailable" if value is None else f"{value:.1%}"


def _count(value: int | None) -> str:
    return "unavailable" if value is None else str(value)


def _ms(value: float | None) -> str:
    return "unavailable" if value is None else f"{value:.0f}ms"


def _detail_lines(decision: OpsDecision, width: int) -> list[str]:
    lines = [
        "",
        _fit("─ SELECTED DECISION / REDACTED RECEIPT " + "─" * width, width),
        _fit(
            f"Outcome {OUTCOME_LABELS[decision.final_outcome]}  "
            f"Authority {decision.authority.upper()}  "
            f"Provenance {decision.provenance.upper()}  "
            "Recorded model-call latency sum "
            f"{_ms(decision.recorded_model_call_latency_sum_ms)}",
            width,
        ),
        _fit(
            f"Decision {decision.decision_id}  Contract "
            f"{decision.contract_id}@{decision.contract_version}  "
            f"Contract hash unavailable",
            width,
        ),
    ]
    for attempt in decision.attempts:
        status = (
            "PROVIDER ERROR"
            if attempt.attempt_status == "provider_error"
            else "CONFORMANT"
            if attempt.contract_conformant
            else "REJECTED"
        )
        lines.append(
            _fit(
                f"#{attempt.ordinal} {attempt.tier}/{attempt.provider} "
                f"model={attempt.model_id}  {status}  {_ms(attempt.latency_ms)}",
                width,
            )
        )
        if attempt.failed_check_ids:
            lines.append(
                _fit("   failed " + ", ".join(attempt.failed_check_ids), width)
            )
        if attempt.audit_sampled:
            lines.append(
                _fit(
                    f"   audit {attempt.audit_result or 'unavailable'} "
                    "[DISPLAY ONLY]",
                    width,
                )
            )
    lines.append(
        _fit(
            "Receipt: raw content WITHHELD | provider/model + contract version "
            "+ checks recorded | replay unavailable",
            width,
        )
    )
    return lines


def render_lines(
    snapshot: OpsSnapshot,
    *,
    width: int = 120,
    height: int = 36,
    selected: int = 0,
    query: str = "",
    detail: bool = False,
    connection: str | None = None,
    endpoint: str = "",
    paused: bool = False,
) -> list[str]:
    width = max(40, width)
    height = max(12, height)
    state = connection or ("DEMO" if snapshot.provenance == "sample" else "LIVE")
    runtime_badges = (
        f"STATE {state} | DATA {snapshot.provenance.upper()} | MODE "
        f"{snapshot.service.execution_mode.upper()}"
    )
    authority_badges = (
        f"AUTHORITY {snapshot.authority.upper().replace('_', ' ')} | "
        "CONTENT WITHHELD"
    )
    lines = [
        _fit("K TOP  Kaaval decision assurance", width),
        _fit(runtime_badges, width),
        _fit(authority_badges, width),
        _fit(
            f"endpoint {endpoint or 'unavailable'}  runtime "
            f"{snapshot.service.runtime_version}  deployment "
            f"{snapshot.service.deployment_mode}"
            + ("  VIEW PAUSED" if paused else ""),
            width,
        ),
    ]
    if width < 104:
        lines.extend(
            [
                _fit(
                    f"Window decisions {snapshot.totals.decisions}  "
                    f"Calls/min {_count(snapshot.totals.calls_last_minute)}  "
                    f"Final contract-conformance "
                    f"{_rate(snapshot.totals.final_contract_conformance_rate)}  "
                    f"Recovered {snapshot.totals.recovered}",
                    width,
                ),
                _fit(
                    f"No safe {snapshot.totals.no_safe_answer}  "
                    f"Provider errors {snapshot.totals.provider_errors}  "
                    f"Attempts {snapshot.totals.attempts}  "
                    f"Escalations {snapshot.totals.escalations}",
                    width,
                ),
                _fit(
                    "p95 model-call latency sum "
                    f"{_ms(snapshot.totals.p95_recorded_model_call_latency_sum_ms)}  "
                    f"Recorded cost ${snapshot.totals.recorded_cost_usd:.4f}",
                    width,
                ),
            ]
        )
    else:
        lines.extend(
            [
                _fit(
                    f"Window decisions {snapshot.totals.decisions}  "
                    f"Calls/min {_count(snapshot.totals.calls_last_minute)}  "
                    f"Final contract-conformance "
                    f"{_rate(snapshot.totals.final_contract_conformance_rate)}  "
                    f"Recovered {snapshot.totals.recovered}  "
                    f"No safe {snapshot.totals.no_safe_answer}  "
                    f"Provider errors {snapshot.totals.provider_errors}",
                    width,
                ),
                _fit(
                    f"Attempts {snapshot.totals.attempts}  "
                    f"Escalations {snapshot.totals.escalations}  "
                    "p95 model-call latency sum "
                    f"{_ms(snapshot.totals.p95_recorded_model_call_latency_sum_ms)}  "
                    f"Recorded cost ${snapshot.totals.recorded_cost_usd:.4f}",
                    width,
                ),
            ]
        )
    if snapshot.totals.decision_window_truncated:
        lines.append(
            _fit(
                "WINDOW TRUNCATED: rates, latency, calls/min, and cost are "
                "limited to bounded recent receipts",
                width,
            )
        )
    if snapshot.routing:
        trend = max(snapshot.routing, key=lambda item: item.verifier_failure_ewma)
        if width < 104:
            lines.extend(
                [
                    _fit(
                        "Verifier failure trend: recent local contract failures; "
                        "not model accuracy",
                        width,
                    ),
                    _fit(
                        f"  {trend.category} {trend.verifier_failure_ewma:.2f} "
                        f"{trend.action.upper()}",
                        width,
                    ),
                ]
            )
        else:
            lines.append(
                _fit(
                    "Verifier failure trend (recent local contract failures, not "
                    f"model accuracy): {trend.category} "
                    f"{trend.verifier_failure_ewma:.2f} {trend.action.upper()}",
                    width,
                )
            )
    else:
        lines.append("Verifier failure trend: unavailable")

    visible = filter_decisions(snapshot, query)
    if query:
        lines.append(_fit(f"Filter /{query}/  {len(visible)} match(es)", width))
    if detail:
        if visible:
            selected = move_selection(selected, 0, len(visible))
            lines.extend(_detail_lines(visible[selected], width))
        else:
            lines.extend(["", "No decisions match the current filter."])
        footer = "Esc back  / filter  p pause  ? help  q quit"
        if len(lines) >= height:
            lines = lines[: height - 1]
        lines.append(_fit(footer, width))
        return lines

    lines.append("")
    if width >= 104:
        lines.append(
            _fit(
                "  TIME      DECISION       CONTRACT@VERSION                 "
                "MODEL                  PATH  OUTCOME       CALL LAT SUM",
                width,
            )
        )
        table_capacity = max(1, height - len(lines) - 1)
        start = _viewport_start(selected, len(visible), table_capacity)
        window = visible[start : start + table_capacity]
        for offset, decision in enumerate(window):
            index = start + offset
            final_model = decision.attempts[-1].model_id if decision.attempts else "unavailable"
            row = (
                f"{'>' if index == selected else ' '} "
                f"{decision.timestamp.astimezone().strftime('%H:%M:%S')}  "
                f"{_short_id(decision.decision_id, 13):13}  "
                f"{_fit(decision.contract_id + '@' + decision.contract_version, 30):30}  "
                f"{_fit(final_model, 22):22}  "
                f"{_path(decision):4}  "
                f"{OUTCOME_LABELS[decision.final_outcome]:15}  "
                f"{_ms(decision.recorded_model_call_latency_sum_ms):>11}"
            )
            lines.append(_fit(row, width))
    else:
        lines.append(
            _fit(
                "  TIME      DECISION       CONTRACT              PATH  OUTCOME",
                width,
            )
        )
        table_capacity = max(1, height - len(lines) - 1)
        start = _viewport_start(selected, len(visible), table_capacity)
        window = visible[start : start + table_capacity]
        for offset, decision in enumerate(window):
            index = start + offset
            row = (
                f"{'>' if index == selected else ' '} "
                f"{decision.timestamp.astimezone().strftime('%H:%M:%S')}  "
                f"{_short_id(decision.decision_id, 13):13}  "
                f"{_fit(decision.contract_id, 21):21}  "
                f"{_path(decision):4}  "
                f"{OUTCOME_LABELS[decision.final_outcome]}"
            )
            lines.append(_fit(row, width))

    if not visible:
        lines.extend(["", "No decisions match the current filter."])

    if visible:
        shown_end = min(len(visible), start + table_capacity)
        viewport = f"  rows {start + 1}-{shown_end}/{len(visible)}"
    else:
        viewport = ""
    footer = (
        "j/k move  Enter inspect  / filter  p pause  ? help  q quit" + viewport
    )
    if len(lines) >= height:
        lines = lines[: height - 1]
    lines.append(_fit(footer, width))
    return lines


def _help_lines(width: int, height: int) -> list[str]:
    values = [
        "K TOP HELP",
        "",
        "j/k or arrows  move selected assured decision",
        "Enter          inspect the redacted receipt",
        "Esc            return to overview",
        "/              filter contract, model, outcome, or failed check ID",
        "p              pause/resume viewport (collection continues)",
        "r              refresh now",
        "?              toggle this help",
        "q              quit",
        "",
        "K Top is read-only. It cannot change enforcement, retry a paid call,",
        "approve a decision, expose raw content, or execute a business action.",
    ]
    return [_fit(value, width) for value in values[: max(1, height - 1)]]


def _run_curses(
    source: SnapshotSource,
    initial: OpsSnapshot,
    refresh_seconds: float,
    initial_query: str,
) -> int:
    try:
        import curses
    except ImportError:
        for line in render_lines(
            initial,
            width=shutil.get_terminal_size((120, 36)).columns,
            endpoint=source.label,
        ):
            print(line)
        return 0

    results: queue.Queue[tuple[OpsSnapshot | None, bool]] = queue.Queue(maxsize=1)
    refresh_requested = threading.Event()
    stop_requested = threading.Event()

    def fetch_worker() -> None:
        while not stop_requested.is_set():
            if not refresh_requested.wait(0.1):
                continue
            if stop_requested.is_set():
                break
            refresh_requested.clear()
            try:
                item = (source.fetch(), True)
            except Exception:
                # The interactive surface stays responsive and retains its
                # last good frame. Upstream exception text is never rendered.
                item = (None, False)
            try:
                while True:
                    results.get_nowait()
            except queue.Empty:
                pass
            try:
                results.put_nowait(item)
            except queue.Full:
                pass

    worker = threading.Thread(target=fetch_worker, daemon=True)
    worker.start()

    def app(screen) -> None:
        screen.keypad(True)
        screen.nodelay(True)
        current = initial
        pending = initial
        selected = 0
        query = initial_query
        detail = False
        help_open = False
        paused = False
        connection = "DEMO" if initial.provenance == "sample" else "LIVE"
        last_refresh_request = time.monotonic()

        while True:
            now = time.monotonic()
            if now - last_refresh_request >= refresh_seconds:
                refresh_requested.set()
                last_refresh_request = now

            try:
                while True:
                    fetched, ok = results.get_nowait()
                    if fetched is not None:
                        current_visible = filter_decisions(current, query)
                        selected_id = (
                            current_visible[selected].decision_id
                            if current_visible
                            and 0 <= selected < len(current_visible)
                            else None
                        )
                        pending = fetched
                        connection = (
                            "DEMO" if pending.provenance == "sample" else "LIVE"
                        )
                        if not paused:
                            current = pending
                            selected = selection_for_decision(
                                current, query, selected_id, selected
                            )
                    elif not ok:
                        connection = "STALE"
            except queue.Empty:
                pass

            height, width = screen.getmaxyx()
            visible = filter_decisions(current, query)
            selected = move_selection(selected, 0, len(visible))
            lines = (
                _help_lines(width, height)
                if help_open
                else render_lines(
                    current,
                    width=width,
                    height=height,
                    selected=selected,
                    query=query,
                    detail=detail,
                    connection=connection,
                    endpoint=source.label,
                    paused=paused,
                )
            )
            screen.erase()
            for row, line in enumerate(lines[: max(0, height - 1)]):
                try:
                    screen.addnstr(row, 0, line, max(0, width - 1))
                except curses.error:
                    pass
            screen.refresh()

            key = screen.getch()
            if key == -1:
                time.sleep(0.05)
                continue
            if key in (ord("q"), ord("Q")):
                return
            if key in (ord("?"),):
                help_open = not help_open
                continue
            if help_open:
                continue
            if key in (ord("j"), curses.KEY_DOWN):
                selected = move_selection(selected, 1, len(visible))
            elif key in (ord("k"), curses.KEY_UP):
                selected = move_selection(selected, -1, len(visible))
            elif key in (10, 13, curses.KEY_ENTER):
                detail = bool(visible)
            elif key == 27:
                detail = False
            elif key in (ord("p"), ord("P")):
                paused = not paused
                if not paused:
                    current_visible = filter_decisions(current, query)
                    selected_id = (
                        current_visible[selected].decision_id
                        if current_visible and 0 <= selected < len(current_visible)
                        else None
                    )
                    current = pending
                    selected = selection_for_decision(
                        current, query, selected_id, selected
                    )
            elif key in (ord("r"), ord("R")):
                refresh_requested.set()
                last_refresh_request = time.monotonic()
            elif key == ord("/"):
                screen.nodelay(False)
                curses.echo()
                try:
                    prompt = "Filter (empty clears): "
                    screen.move(max(0, height - 1), 0)
                    screen.clrtoeol()
                    screen.addnstr(max(0, height - 1), 0, prompt, max(0, width - 1))
                    raw = screen.getstr(
                        max(0, height - 1),
                        min(len(prompt), max(0, width - 1)),
                        max(1, width - len(prompt) - 1),
                    )
                    query = raw.decode("utf-8", errors="replace")
                    selected = 0
                    detail = False
                finally:
                    curses.noecho()
                    screen.nodelay(True)

    try:
        try:
            curses.wrapper(app)
        except KeyboardInterrupt:
            return 0
    finally:
        stop_requested.set()
        refresh_requested.set()
    return 0


def run_top(args) -> int:
    source: SnapshotSource
    if args.demo:
        source = DemoSnapshotSource()
    else:
        endpoint = args.endpoint or os.environ.get(
            "KAAVAL_ENDPOINT", "http://127.0.0.1:8000"
        )
        try:
            source = HttpSnapshotSource(endpoint, timeout_seconds=args.timeout)
        except SourceError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2

    try:
        snapshot = source.fetch()
    except SourceError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(snapshot.model_dump_json(indent=2))
        return 0

    if args.once or not (sys.stdin.isatty() and sys.stdout.isatty()):
        width = args.width or shutil.get_terminal_size((120, 36)).columns
        for line in render_lines(
            snapshot,
            width=width,
            height=args.height,
            query=args.filter,
            endpoint=source.label,
        ):
            print(line)
        return 0

    return _run_curses(source, snapshot, args.refresh, args.filter)
