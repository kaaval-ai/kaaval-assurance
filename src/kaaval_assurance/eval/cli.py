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
from ..providers import FAILURE_MODES, MockProvider
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
            f"ewma drift {cat.ewma_drift:.3f}"
        )
    failed = [r for r in report.results if not r.passed]
    if failed:
        print(f"unverified after escalation: {', '.join(r.case_id for r in failed)}")


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
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        cases = load_dataset(args.dataset)
    except (OSError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    store = TrajectoryStore(args.db)
    try:
        pipeline = AssurancePipeline(
            router=Router(),
            local_provider=MockProvider(
                tier="local",
                failure_mode=args.failure_mode,
                failure_rate=args.failure_rate,
                seed=args.seed,
            ),
            remote_provider=MockProvider(tier="remote", model_id="mock-remote-strong"),
            store=store,
        )
        report = run_eval(pipeline, cases, ewma_alpha=args.ewma_alpha)
    finally:
        store.close()

    if args.json:
        print(report.model_dump_json(indent=2))
    else:
        _print_text(report, args.dataset)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
