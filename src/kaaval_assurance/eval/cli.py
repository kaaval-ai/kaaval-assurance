"""CLI: run the gold eval locally through the mock pipeline.

Zero cloud access. Failure-injection knobs simulate local-tier degradation so
the Layer-2 metrics and EWMA drift are demonstrable before real providers land.

    python -m kaaval_assurance.eval.cli --dataset data/eval/telecom_gold.jsonl
    python -m kaaval_assurance.eval.cli --failure-mode bad_enum --failure-rate 0.4
"""

import argparse
import sys
from pathlib import Path

from ..metrics import DEFAULT_EWMA_ALPHA, MetricsReport
from ..pipeline import AssurancePipeline
from ..providers import FAILURE_MODES, FireworksError, MockProvider, VllmError
from ..router import Router
from ..trajectory import TrajectoryStore
from .dataset import load_dataset
from .runner import EvalRunReport, run_eval

DEFAULT_DATASET = Path("data/eval/telecom_gold.jsonl")


def _fmt_cost(value) -> str:
    return "n/a" if value is None else f"${value:.4f}"


def _print_text(report: EvalRunReport, dataset: Path) -> None:
    m: MetricsReport = report.metrics
    print(f"kaaval-assurance eval — {report.n_cases} cases from {dataset}")
    print(
        f"requests {m.requests} | attempts {m.attempts} | "
        f"pass rate {m.pass_rate:.1%} | escalation rate {m.escalation_rate:.1%}"
    )
    print(
        f"latency p50 {m.latency_ms_p50:.1f}ms p95 {m.latency_ms_p95:.1f}ms | "
        f"total cost {_fmt_cost(m.total_cost_usd)} | "
        f"cost per verified answer {_fmt_cost(m.cost_per_verified_usd)}"
    )
    if m.failure_counts:
        counts = ", ".join(f"{k}={v}" for k, v in sorted(m.failure_counts.items()))
        print(f"verifier failures by check: {counts}")
    else:
        print("verifier failures by check: none")
    print(f"per category (EWMA alpha {m.ewma_alpha}):")
    for name, cat in m.by_category.items():
        print(
            f"  {name}: requests {cat.requests} | pass {cat.pass_rate:.1%} | "
            f"local-pass {cat.local_pass_rate:.1%} | "
            f"escalation {cat.escalation_rate:.1%} | "
            f"preroute-remote {cat.preroute_remote_rate:.1%} | "
            f"ewma drift {cat.ewma_drift:.3f}"
        )
    failed = [r for r in report.results if not r.passed]
    if failed:
        print(f"unverified after escalation: {', '.join(r.case_id for r in failed)}")


def _print_demo(demo, dataset: Path) -> None:
    from .closed_loop import ClosedLoopDemoReport  # noqa: F401 (type context)

    def phase_line(label, report):
        m = report.metrics
        print(f"{label}: pass {m.pass_rate:.1%} | escalation {m.escalation_rate:.1%} | "
              f"preroute-remote {m.preroute_remote_rate:.1%} | "
              f"cost/verified {_fmt_cost(m.cost_per_verified_usd)}")
        for name, cat in m.by_category.items():
            print(f"    {name}: drift {cat.ewma_drift:.2f} | "
                  f"local-pass {cat.local_pass_rate:.1%} | "
                  f"escalation {cat.escalation_rate:.1%} | "
                  f"preroute-remote {cat.preroute_remote_rate:.1%}")

    print(f"closed-loop routing demo — {demo.phase_a.n_cases} cases from {dataset}")
    phase_line("phase A (healthy local tier)", demo.phase_a)
    phase_line("phase B (degraded local tier, default routing)", demo.phase_b)
    print("policy applied from phase-B drift:")
    for name, policy in demo.policy_after_b.items():
        print(f"    {name}: drift {policy.drift:.2f} -> {policy.action} "
              f"(threshold {policy.threshold:.2f})")
    phase_line("phase C (degraded local tier, adapted routing)", demo.phase_c)
    prerouted = [r for r in demo.phase_c.results if "forces remote" in r.routing_reason]
    if prerouted:
        print(f'example phase-C routing reason ({prerouted[0].case_id}): '
              f'"{prerouted[0].routing_reason}"')


def _print_audit(summary) -> None:
    cal = summary.calibration
    if cal.status == "skipped":
        cal_line = "calibration skipped (results untrusted)"
    else:
        cal_line = (
            f"calibration {cal.status} (false-positive rate "
            f"{cal.false_positive_rate:.1%}, threshold {cal.threshold:.1%})"
        )
    trust = "trusted" if summary.trusted else "UNTRUSTED — display only, no routing signal"
    print(
        f"layer-3 audit ({summary.audit_provider}, {summary.audit_model_id}): "
        f"{cal_line} | signal {trust}"
    )
    if cal.status == "failed":
        print(
            "  audit disabled as a routing signal: challenger flagged "
            f"{cal.false_positives}/{cal.total_gold} known-good gold answers "
            f"({', '.join(cal.flagged_case_ids) or 'none listed'})"
        )
    severities = (
        ", ".join(f"{k}={v}" for k, v in sorted(summary.violations_by_severity.items()))
        or "none"
    )
    print(
        f"  sampled {summary.sampled}/{summary.accepted_answers} accepted "
        f"(rate {summary.sample_rate:.0%}) | pass {summary.passed} "
        f"fail {summary.failed} errors {summary.errors} | violations: {severities}"
    )
    print(
        f"  audit cost total {_fmt_cost(summary.total_cost_usd)} | "
        f"per sampled {_fmt_cost(summary.cost_per_sampled_usd)} | "
        f"per verified accepted {_fmt_cost(summary.cost_per_verified_accepted_usd)} | "
        f"audit tokens {summary.audit_tokens}"
    )


def _judge_line(report, summary) -> str:
    line = (
        f"Layer 3 sampled {summary.sample_rate:.0%} of accepted answers, "
        f"calibration false-positive rate was "
        f"{summary.calibration.false_positive_rate:.1%}, "
        f"audit cost per verified answer was "
        f"{_fmt_cost(summary.cost_per_verified_accepted_usd)}"
    )
    if report.metrics.preroute_remote_rate > 0:
        line += (
            ", and high-drift categories were routed away from the local "
            "Gemma tier until confidence recovered"
        )
    return line + "."


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="kaaval-eval",
        description="Replay the gold eval set through the mock assurance pipeline "
        "and report Layer-2 metrics.",
    )
    parser.add_argument(
        "--dataset", type=Path, default=DEFAULT_DATASET, help="JSONL eval dataset"
    )
    parser.add_argument(
        "--db",
        default=":memory:",
        help="trajectory SQLite path (default in-memory)",
    )
    parser.add_argument(
        "--local-provider",
        choices=["mock", "vllm"],
        default="mock",
        help="local tier: deterministic mock (default) or a Gemma model on an "
        "OpenAI-compatible vLLM endpoint (reads VLLM_* env vars)",
    )
    parser.add_argument(
        "--remote-provider",
        choices=["mock", "fireworks"],
        default="mock",
        help="escalation tier: deterministic mock (default) or Fireworks AI "
        "(reads FIREWORKS_* env vars)",
    )
    parser.add_argument(
        "--failure-mode",
        choices=FAILURE_MODES,
        default=None,
        help="inject this failure into the local mock tier",
    )
    parser.add_argument(
        "--failure-rate",
        type=float,
        default=0.0,
        help="probability a local response carries the failure (0 with a mode "
        "set = fail every time)",
    )
    parser.add_argument("--seed", type=int, default=0, help="failure-injection RNG seed")
    parser.add_argument(
        "--ewma-alpha", type=float, default=DEFAULT_EWMA_ALPHA, help="EWMA smoothing"
    )
    parser.add_argument(
        "--json", action="store_true", help="emit full report as JSON instead of text"
    )
    parser.add_argument(
        "--closed-loop-demo",
        action="store_true",
        help="run the three-phase closed-loop routing demo: healthy baseline, "
        "degraded local tier, then drift-driven routing adaptation",
    )
    parser.add_argument(
        "--audit-provider",
        choices=["none", "mock", "fireworks"],
        default="none",
        help="layer-3 offline sampled audit challenger (default: no audit)",
    )
    parser.add_argument(
        "--audit-sample-rate",
        type=float,
        default=0.10,
        help="fraction of accepted answers sampled for audit",
    )
    parser.add_argument(
        "--audit-seed", type=int, default=0, help="audit sampling RNG seed"
    )
    parser.add_argument(
        "--audit-calibration-threshold",
        type=float,
        default=0.20,
        help="max challenger false-positive rate on gold answers before the "
        "audit signal is marked untrusted",
    )
    parser.add_argument(
        "--skip-audit-calibration",
        action="store_true",
        help="local development only: skip the gold-answer calibration gate; "
        "audit results stay marked untrusted",
    )
    parser.add_argument(
        "--telemetry-summary",
        action="store_true",
        help="print the judge-ready telemetry truth block (claim -> value -> "
        "source)",
    )
    parser.add_argument(
        "--telemetry-json",
        action="store_true",
        help="print the full telemetry summary as JSON",
    )
    parser.add_argument(
        "--telemetry-markdown",
        type=Path,
        default=None,
        help="write the telemetry truth summary to a markdown file",
    )
    parser.add_argument(
        "--always-remote-baseline-db",
        type=Path,
        default=None,
        help="trajectory DB of a cached always-remote run; enables "
        "remote-calls-avoided and cost-saved telemetry",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        cases = load_dataset(args.dataset)
    except (OSError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    if args.remote_provider == "fireworks":
        from ..providers.fireworks import FireworksConfig, FireworksProvider

        try:
            remote_provider = FireworksProvider(FireworksConfig.from_env())
        except ValueError as e:
            print(f"error: {e}", file=sys.stderr)
            return 2
    else:
        remote_provider = MockProvider(tier="remote", model_id="mock-remote-strong")

    if args.audit_provider != "none" and args.closed_loop_demo:
        print(
            "error: audit runs on the standard eval path, not the closed-loop "
            "demo",
            file=sys.stderr,
        )
        return 2

    telemetry_requested = (
        args.telemetry_summary
        or args.telemetry_json
        or args.telemetry_markdown is not None
    )
    if telemetry_requested and args.closed_loop_demo:
        print(
            "error: telemetry summary runs on the standard eval path, not the "
            "closed-loop demo",
            file=sys.stderr,
        )
        return 2

    challenger = None
    if args.audit_provider == "mock":
        from ..audit import MockAuditChallenger

        challenger = MockAuditChallenger(seed=args.audit_seed)
    elif args.audit_provider == "fireworks":
        from ..audit import FireworksAuditChallenger, FireworksAuditConfig

        try:
            challenger = FireworksAuditChallenger(FireworksAuditConfig.from_env())
        except ValueError as e:
            print(f"error: {e}", file=sys.stderr)
            return 2

    if args.local_provider == "vllm":
        if args.closed_loop_demo:
            print(
                "error: --closed-loop-demo drives the mock local tier only",
                file=sys.stderr,
            )
            return 2
        if args.failure_mode:
            print(
                "error: --failure-mode injects failures into the mock local "
                "tier only",
                file=sys.stderr,
            )
            return 2
        from ..providers.vllm import VllmConfig, VllmProvider

        try:
            local_provider = VllmProvider(VllmConfig.from_env())
        except ValueError as e:
            print(f"error: {e}", file=sys.stderr)
            return 2
    else:
        local_provider = MockProvider(
            tier="local",
            failure_mode=args.failure_mode,
            failure_rate=args.failure_rate,
            seed=args.seed,
        )

    store = TrajectoryStore(args.db)
    try:
        if args.closed_loop_demo:
            from .closed_loop import run_closed_loop_demo

            demo = run_closed_loop_demo(
                cases,
                store,
                remote_provider,
                failure_mode=args.failure_mode or "bad_enum",
                failure_rate=args.failure_rate,
                seed=args.seed,
                ewma_alpha=args.ewma_alpha,
            )
            if args.json:
                print(demo.model_dump_json(indent=2))
            else:
                _print_demo(demo, args.dataset)
            return 0

        pipeline = AssurancePipeline(
            router=Router(),
            local_provider=local_provider,
            remote_provider=remote_provider,
            store=store,
        )
        report = run_eval(pipeline, cases, ewma_alpha=args.ewma_alpha)

        run_rows = []
        if challenger is not None or telemetry_requested:
            for result in report.results:
                run_rows.extend(store.rows_for_request(result.request_id))

        if challenger is not None:
            from ..audit import (
                calibrate_challenger,
                run_sampled_audit,
                skipped_calibration,
            )

            if args.skip_audit_calibration:
                calibration = skipped_calibration(args.audit_calibration_threshold)
            else:
                calibration = calibrate_challenger(
                    challenger, cases, threshold=args.audit_calibration_threshold
                )
            summary, _ = run_sampled_audit(
                store,
                run_rows,
                challenger,
                calibration,
                sample_rate=args.audit_sample_rate,
                seed=args.audit_seed,
            )
            report.audit = summary
            # audit wrote audit_* fields; refresh rows for telemetry
            if telemetry_requested:
                run_rows = []
                for result in report.results:
                    run_rows.extend(store.rows_for_request(result.request_id))

        telemetry = None
        if telemetry_requested:
            from ..telemetry import baseline_from_rows, build_telemetry_summary

            baseline = None
            if args.always_remote_baseline_db is not None:
                baseline_store = TrajectoryStore(args.always_remote_baseline_db)
                try:
                    baseline = baseline_from_rows(baseline_store.all_rows())
                finally:
                    baseline_store.close()
            telemetry = build_telemetry_summary(
                report,
                run_rows,
                runtime_profile=local_provider.runtime_profile(),
                always_remote_baseline=baseline,
            )
    except (FireworksError, VllmError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    finally:
        store.close()

    if args.json:
        print(report.model_dump_json(indent=2))
    else:
        profile = local_provider.runtime_profile()
        if profile is not None:
            print(
                f"local runtime profile: {profile.provider} "
                f"model={profile.model_id} target={profile.hardware_target} "
                f"dtype={profile.dtype} kv-cache={profile.kv_cache_dtype} "
                f"tp={profile.tensor_parallel_size} "
                f"gpu-mem-util={profile.gpu_memory_utilization} "
                f"prefix-caching={'on' if profile.prefix_caching_enabled else 'off'} "
                f"structured-output={profile.structured_output_mode}"
            )
        _print_text(report, args.dataset)
        if report.audit is not None:
            _print_audit(report.audit)
            print(_judge_line(report, report.audit))

    if telemetry is not None:
        from ..telemetry import render_summary_markdown, render_summary_text

        if args.telemetry_summary:
            print(render_summary_text(telemetry))
        if args.telemetry_json:
            print(telemetry.model_dump_json(indent=2))
        if args.telemetry_markdown is not None:
            args.telemetry_markdown.write_text(
                render_summary_markdown(telemetry) + "\n", encoding="utf-8"
            )
            print(f"telemetry markdown written to {args.telemetry_markdown}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
