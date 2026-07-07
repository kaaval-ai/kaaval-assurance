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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
