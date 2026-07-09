"""Kaaval Assurance demo console — Track 3 demo and telemetry replay surface.

Two tabs:
- Live demo run: drives the real AssurancePipeline with mock providers —
  pick a contract, a gold sample input, and an injected local failure, then
  watch Layer-1 verification and escalation happen, and export the run as
  artifacts.
- Artifact replay: renders recorded artifacts, preferring artifacts/ (real
  runs) over demo_artifacts/sample/ (synthetic sample data).

Run locally:
    pip install -e ".[demo]"
    streamlit run apps/demo_console/app.py
"""

import json
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from kaaval_assurance.contracts import list_contracts  # noqa: E402
from kaaval_assurance.demo import (  # noqa: E402
    LIVE_FAILURE_MODES,
    export_live_demo_artifacts,
    run_live_demo,
)
from kaaval_assurance.eval import load_dataset  # noqa: E402

ARTIFACTS = ROOT / "artifacts"
SAMPLE = ROOT / "demo_artifacts" / "sample"
GOLD = ROOT / "data" / "eval" / "telecom_gold.jsonl"

FLOW = """
task input
  └─> provider-neutral router  (per-category thresholds from Layer-2 drift)
        └─> local Gemma tier — vLLM on AMD hackathon GPU  (or MockProvider)
              └─> Layer 1: deterministic contract verification
                    ├─ pass ──> accepted answer
                    └─ fail ──> escalate: Fireworks remote tier (or mock)
        every attempt ──> trajectory store (replayable rows)
                             ├─> Layer 2: metrics + per-category EWMA drift
                             └─> Layer 3: sampled offline adversarial audit
                                   (calibration-gated; sensor, not a judge)
"""

SOURCE_BADGES = {
    "measured": "🟢 measured",
    "configured": "🔵 configured",
    "not_available": "⚪ not_available",
    "planned": "🟡 planned",
}

AMD_FRAMING = (
    "The mock local tier is the development stand-in for **Gemma served via "
    "vLLM on the AMD hackathon GPU** — same `Provider` interface, swapped by "
    "environment configuration. Measured AMD claims require runtime probe "
    "artifacts from the pod; everything below stays honestly tagged."
)


def load_artifact(name: str):
    """Prefer real artifacts/, fall back to shipped sample data."""
    for base, source in ((ARTIFACTS, "artifacts"), (SAMPLE, "sample")):
        path = base / name
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8")), source
            except (OSError, json.JSONDecodeError):
                continue
    return None, None


def badge(source: str) -> str:
    return SOURCE_BADGES.get(source, source)


def pct(value) -> str:
    return "n/a" if value is None else f"{value:.1%}"


def usd(value) -> str:
    return "n/a" if value is None else f"${value:.4f}"


def render_attempt_row(row, title: str) -> None:
    outcome = "passed" if row.verifier_passed else "FAILED"
    failures = ", ".join(row.verifier_failures) or "none"
    with st.expander(
        f"{title} — {row.provider}/{row.model_id} — Layer 1 {outcome} "
        f"(failed checks: {failures})",
        expanded=not row.verifier_passed,
    ):
        st.markdown("**Raw model output:**")
        st.code(row.raw_text, language="json")
        st.markdown(
            f"latency {row.latency_ms:.1f}ms · cost ${row.cost_usd:.4f} · "
            f"tokens {row.prompt_tokens}+{row.completion_tokens}"
        )


def render_live() -> None:
    st.markdown(AMD_FRAMING)

    contracts = list_contracts()
    contract = st.selectbox(
        "Task contract",
        contracts,
        format_func=lambda c: f"{c.contract_id} — {c.description}",
    )
    cases = [
        c for c in load_dataset(GOLD) if c.contract_id == contract.contract_id
    ]
    case = st.selectbox(
        "Sample input (from the gold eval set, synthetic)",
        cases,
        format_func=lambda c: f"{c.case_id}: {c.task_input[:90]}",
    )
    mode = st.radio(
        "Inject local-tier failure",
        ["none", *LIVE_FAILURE_MODES],
        horizontal=True,
        help="Simulates local-model degradation so Layer 1 and escalation "
        "are visible on demand.",
    )

    if st.button("Run assurance pipeline", type="primary"):
        st.session_state["live_demo"] = run_live_demo(
            task_input=case.task_input,
            contract_id=contract.contract_id,
            failure_mode=None if mode == "none" else mode,
            case_id=case.case_id,
        )

    demo = st.session_state.get("live_demo")
    if demo is None:
        st.caption("Pick a contract, an input, and a failure mode, then run.")
        return

    st.subheader("What happened")
    if demo.local_row is not None:
        render_attempt_row(demo.local_row, "Local attempt")
    if demo.result.escalated:
        st.warning(f"Escalation: {demo.result.routing.reason}")
        if demo.remote_row is not None:
            render_attempt_row(demo.remote_row, "Remote attempt (escalated)")
    else:
        st.success(f"No escalation needed — {demo.result.routing.reason}")

    st.subheader("Final accepted answer")
    verified = "verified" if demo.result.verification.passed else "NOT verified"
    st.markdown(
        f"Layer 1 **{verified}** after {demo.result.attempts} attempt(s), "
        f"served by the **{demo.result.response.tier}** tier "
        f"({demo.result.verification.checks_run} deterministic checks run)."
    )
    if demo.result.response.parsed is not None:
        st.json(demo.result.response.parsed)
    else:
        st.code(demo.result.response.raw_text, language=None)

    st.subheader("Trajectory rows written")
    st.caption(
        "One replayable row per attempt — full input and raw output stored "
        "verbatim, audit fields reserved for the Layer-3 sampler."
    )
    st.json([json.loads(r.model_dump_json()) for r in demo.rows])

    if st.button("Save demo artifacts"):
        paths = export_live_demo_artifacts(demo, ARTIFACTS)
        st.success(
            "written: "
            + ", ".join(str(p.relative_to(ROOT)) for p in paths)
        )
        st.caption(
            "Exported telemetry keeps its source tags — this mock run reports "
            "the runtime as planned, never measured."
        )


def render_replay() -> None:
    telemetry, telemetry_source = load_artifact("telemetry-truth.json")
    probe, probe_source = load_artifact("runtime-probe.json")
    trajectory, trajectory_source = load_artifact("trajectory-sample.json")

    if telemetry_source == "artifacts" or probe_source == "artifacts":
        st.success(
            "Showing recorded artifacts from a real run (artifacts/). Sections "
            "still tagged planned/configured have not been measured yet."
        )
    else:
        st.warning(
            "Sample data (synthetic, mock providers, zero cloud access) until "
            "the AMD pod run. Measured AMD artifacts from the runtime probe "
            "and eval CLI replace these automatically once written to "
            "artifacts/."
        )

    st.header("Request flow")
    st.code(FLOW, language=None)

    left, right = st.columns(2)

    with left:
        st.header("Runtime profile")
        if telemetry is not None:
            runtime = telemetry.get("runtime", {})
            st.markdown(f"**Status:** {badge(runtime.get('status', 'planned'))}")
            st.caption(runtime.get("note", ""))
            profile = runtime.get("profile")
            if profile:
                rows = [
                    ("model_id", profile.get("model_id")),
                    ("model_family", profile.get("model_family")),
                    ("hardware_target", profile.get("hardware_target")),
                    ("rocm_version", profile.get("rocm_version") or "recorded at deployment"),
                    ("vllm_version", profile.get("vllm_version") or "recorded at deployment"),
                    ("dtype", profile.get("dtype")),
                    ("kv_cache_dtype", profile.get("kv_cache_dtype")),
                    ("tensor_parallel_size", profile.get("tensor_parallel_size")),
                    ("gpu_memory_utilization", profile.get("gpu_memory_utilization")),
                    ("prefix_caching_enabled", profile.get("prefix_caching_enabled")),
                    ("structured_output_mode", profile.get("structured_output_mode")),
                ]
                st.table(
                    {"setting": [r[0] for r in rows], "value": [str(r[1]) for r in rows]}
                )
                st.caption(
                    "Recorded serving settings — configuration, not measured "
                    "performance."
                )
            else:
                st.markdown(
                    f"{badge('planned')} — Gemma via vLLM on the AMD hackathon "
                    "GPU is the planned local tier; this run used the mock tier."
                )
        if probe is not None:
            st.markdown(f"**Runtime probe** ({probe_source}) — {badge('measured')}")
            system = probe.get("system", {})
            st.markdown(
                f"- under `/workspace`: `{system.get('under_workspace')}`\n"
                f"- python: `{system.get('python_version')}`"
            )
            for name, cmd in (probe.get("commands") or {}).items():
                tag = badge(cmd.get("source", "not_available"))
                detail = (cmd.get("output") or cmd.get("error") or "").splitlines()
                st.markdown(f"- `{name}`: {detail[0] if detail else ''} {tag}")
            endpoint = probe.get("endpoint")
            if endpoint:
                reach = "reachable" if endpoint.get("reachable") else "unreachable"
                st.markdown(
                    f"- vLLM endpoint: {reach}; served: "
                    f"`{', '.join(endpoint.get('served_models', [])) or 'none'}`"
                )
        else:
            st.caption(
                "No runtime probe artifact yet — run "
                "`python -m kaaval_assurance.runtime_probe --output "
                "artifacts/runtime-probe.json` on the AMD pod."
            )

    with right:
        st.header("Telemetry truth")
        if telemetry is None:
            st.info("No telemetry artifact found.")
        else:
            verification = telemetry.get("verification", {})
            routing = telemetry.get("routing", {})
            cost = telemetry.get("cost", {})
            audit = telemetry.get("audit", {})

            m1, m2, m3 = st.columns(3)
            m1.metric(
                "Final verified rate", pct(verification.get("final_verified_rate"))
            )
            m2.metric("Local pass rate", pct(verification.get("local_verified_rate")))
            m3.metric("Escalation rate", pct(routing.get("escalation_rate")))
            m4, m5, m6 = st.columns(3)
            m4.metric(
                "Cost / verified answer",
                usd(cost.get("cost_per_verified_answer_usd")),
            )
            m5.metric(
                "Remote calls avoided",
                pct(cost.get("remote_calls_avoided_rate")),
                help="Populated only when a cached always-remote baseline run "
                "exists.",
            )
            m6.metric(
                "Audit sample",
                f"{audit.get('sampled', 0)}/{audit.get('accepted_answers', 0)}",
            )

            if audit.get("enabled"):
                trusted = (
                    "trusted" if audit.get("trusted") else "UNTRUSTED (display only)"
                )
                st.markdown(
                    f"**Layer 3 audit:** {trusted} — calibration "
                    f"{audit.get('calibration_status')} at FP rate "
                    f"{pct(audit.get('calibration_fp_rate'))} "
                    f"(threshold {pct(audit.get('calibration_threshold'))})"
                )

            st.markdown("**Every claim, with its source:**")
            claims = telemetry.get("claims", [])
            st.table(
                {
                    "claim": [c["claim"] for c in claims],
                    "value": [c["value"] for c in claims],
                    "source": [badge(c["source"]) for c in claims],
                }
            )

    st.header("Replayable trajectory example")
    if trajectory:
        st.markdown(
            f"One request, every attempt stored verbatim ({trajectory_source} "
            "data): the local tier fails Layer-1 contract verification, the "
            "router escalates, the remote tier passes. Nothing summarized "
            "away — the row carries the full input and raw output, so any "
            "request can be replayed and re-verified."
        )
        for row in trajectory:
            outcome = "passed" if row.get("verifier_passed") else "FAILED"
            failures = ", ".join(row.get("verifier_failures", [])) or "none"
            with st.expander(
                f"{row.get('tier')} attempt — {row.get('provider')}/"
                f"{row.get('model_id')} — Layer 1 {outcome} (failures: {failures})"
            ):
                st.json(row)
    else:
        st.caption("No trajectory example artifact found.")


st.set_page_config(page_title="Kaaval Assurance", page_icon="✅", layout="wide")

st.title("Kaaval Assurance")
st.subheader("Gemma-first inference assurance plane for AMD compute")
st.markdown(
    "Task contracts → deterministic Layer-1 verification → Layer-2 drift "
    "tracking → Layer-3 sampled adversarial audit → closed-loop routing. "
    "Local open-weight Gemma via vLLM on the AMD hackathon GPU handles the "
    "cheap first pass; Fireworks handles escalation. Every claim on this page "
    "maps to a stored telemetry field with a source tag."
)

tab_live, tab_replay = st.tabs(["Live demo run", "Artifact replay"])
with tab_live:
    render_live()
with tab_replay:
    render_replay()

st.divider()
st.caption(
    "Honesty notes: eval and shift data are synthetic. Layer 3 uses a model "
    "as a sampled, offline audit signal feeding trend statistics — never a "
    "per-response gate; detection is model-generated while aggregation and "
    "thresholding are deterministic. Runtime values are labeled measured "
    "only when produced by a probe or run on the actual hardware."
)
