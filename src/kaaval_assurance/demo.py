"""Live demo runner: one interactive request through the assurance pipeline.

Runs the real AssurancePipeline with mock providers — the local development
stand-in for Gemma via vLLM on the AMD pod. Same Provider interface, swapped
by environment; nothing here claims a measured AMD runtime, and exported
telemetry keeps its source tags (the mock run reports runtime as planned).
"""

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from .contracts import get_contract
from .eval.runner import CaseResult, EvalRunReport
from .metrics import aggregate
from .models import PipelineResult, TrajectoryRow
from .pipeline import AssurancePipeline
from .providers import MockProvider, Provider
from .router import Router
from .telemetry import TelemetrySummary, build_telemetry_summary
from .trajectory import TrajectoryStore

LIVE_FAILURE_MODES = ("missing_field", "bad_enum", "unparseable")


class LiveDemoResult(BaseModel):
    case_id: str
    contract_id: str
    category: str
    task_input: str
    failure_mode: Optional[str] = None
    result: PipelineResult
    rows: list[TrajectoryRow] = Field(default_factory=list)

    @property
    def local_row(self) -> Optional[TrajectoryRow]:
        return next((r for r in self.rows if r.tier == "local"), None)

    @property
    def remote_row(self) -> Optional[TrajectoryRow]:
        return next((r for r in self.rows if r.tier == "remote"), None)


def run_live_demo(
    task_input: str,
    contract_id: str,
    failure_mode: Optional[str] = None,
    case_id: str = "live",
    local_provider: Optional[Provider] = None,
    remote_provider: Optional[Provider] = None,
) -> LiveDemoResult:
    """One request through the assurance pipeline, in-memory store.

    Defaults to mock tiers. Custom providers (e.g. Ollama local, Fireworks
    remote from the provider factory) may be injected; failure injection is a
    mock-tier concept and cannot combine with a custom local provider.
    """
    if failure_mode is not None and failure_mode not in LIVE_FAILURE_MODES:
        raise ValueError(f"failure_mode must be one of {LIVE_FAILURE_MODES} or None")
    if failure_mode is not None and local_provider is not None:
        raise ValueError(
            "failure injection applies to the default mock local tier only"
        )
    contract = get_contract(contract_id)
    store = TrajectoryStore(":memory:")
    try:
        pipeline = AssurancePipeline(
            router=Router(),
            local_provider=local_provider
            or MockProvider(tier="local", failure_mode=failure_mode),
            remote_provider=remote_provider
            or MockProvider(tier="remote", model_id="mock-remote-strong"),
            store=store,
        )
        request_id = f"live-{uuid.uuid4().hex[:8]}-{case_id}"
        result = pipeline.handle_request(
            task_input=task_input,
            contract_id=contract_id,
            request_id=request_id,
        )
        rows = store.rows_for_request(request_id)
    finally:
        store.close()
    return LiveDemoResult(
        case_id=case_id,
        contract_id=contract_id,
        category=contract.category,
        task_input=task_input,
        failure_mode=failure_mode,
        result=result,
        rows=rows,
    )


def telemetry_for(demo: LiveDemoResult) -> TelemetrySummary:
    """Telemetry truth summary for one live demo run (public API surface)."""
    report = EvalRunReport(
        run_id=demo.result.request_id,
        n_cases=1,
        results=[
            CaseResult(
                case_id=demo.case_id,
                request_id=demo.result.request_id,
                contract_id=demo.contract_id,
                category=demo.category,
                passed=demo.result.verification.passed,
                escalated=demo.result.escalated,
                attempts=demo.result.attempts,
                routing_reason=demo.result.routing.reason,
            )
        ],
        metrics=aggregate(demo.rows),
    )
    return build_telemetry_summary(report, demo.rows)


def _summary_markdown(demo: LiveDemoResult, telemetry: TelemetrySummary) -> str:
    local = demo.local_row
    remote = demo.remote_row
    lines = [
        "# Live assurance demo run",
        "",
        f"Recorded {datetime.now(timezone.utc).isoformat()} — case "
        f"`{demo.case_id}`, contract `{demo.contract_id}`, injected local "
        f"failure: `{demo.failure_mode or 'none'}`.",
        "",
        f"**Task input:** {demo.task_input}",
        "",
    ]
    if local is not None:
        outcome = "passed" if local.verifier_passed else "FAILED"
        failures = ", ".join(local.verifier_failures) or "none"
        lines.append(
            f"**Local attempt** ({local.provider}/{local.model_id}): Layer 1 "
            f"{outcome}; failed checks: {failures}."
        )
    if demo.result.escalated and remote is not None:
        lines.append(
            f"**Escalation:** {demo.result.routing.reason}"
        )
        lines.append(
            f"**Remote attempt** ({remote.provider}/{remote.model_id}): Layer 1 "
            f"{'passed' if remote.verifier_passed else 'FAILED'}."
        )
    else:
        lines.append("**Escalation:** not needed; local answer accepted.")
    lines.append(
        f"**Final answer verified:** {demo.result.verification.passed} "
        f"(tier: {demo.result.response.tier}, attempts: {demo.result.attempts})."
    )
    lines += [
        "",
        "| Claim | Value | Source |",
        "|---|---|---|",
    ]
    lines += [
        f"| {c.claim} | {c.value} | {c.source} |" for c in telemetry.claims
    ]
    lines += [
        "",
        "This run uses the deterministic mock local tier as the development "
        "stand-in for Gemma served via vLLM on the AMD hackathon GPU — same "
        "Provider interface, swapped by environment configuration. Runtime "
        "values stay tagged planned/configured; measured AMD claims require "
        "runtime probe artifacts from the pod.",
    ]
    return "\n".join(lines)


def export_live_demo_artifacts(
    demo: LiveDemoResult, out_dir: Path
) -> list[Path]:
    """Write telemetry JSON, trajectory JSON, manifest, and a markdown summary."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    telemetry = telemetry_for(demo)

    telemetry_filename = "demo-live-telemetry.json"
    telemetry_path = out_dir / telemetry_filename
    telemetry_path.write_text(telemetry.model_dump_json(indent=2) + "\n", "utf-8")

    trajectory_filename = "demo-live-trajectory.json"
    trajectory_path = out_dir / trajectory_filename
    trajectory_path.write_text(
        "[\n"
        + ",\n".join(row.model_dump_json(indent=2) for row in demo.rows)
        + "\n]\n",
        "utf-8",
    )

    import json
    manifest_filename = "demo-live-manifest.json"
    manifest_path = out_dir / manifest_filename
    manifest = {
        "schema_version": 1,
        "run_id": demo.result.request_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "artifacts": {
            "telemetry": telemetry_filename,
            "trajectory": trajectory_filename,
        },
        "metadata": {
            "mode": "live",
            "category": demo.category,
            "failure_mode": demo.failure_mode
        }
    }
    if (out_dir / "runtime-probe.json").exists():
        manifest["artifacts"]["runtime_probe"] = "runtime-probe.json"
        
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", "utf-8")

    summary_path = out_dir / "demo-live-summary.md"
    summary_path.write_text(_summary_markdown(demo, telemetry) + "\n", "utf-8")

    return [telemetry_path, trajectory_path, manifest_path, summary_path]
