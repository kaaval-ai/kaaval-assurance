"""CLI entry point for the runnable multi-step assurance workflow."""

import argparse
import json
import sys

from .agent import NOC_INCIDENT_WORKFLOW, rows_for_agent_run, run_agent_workflow
from .pipeline import AssurancePipeline
from .providers.factory import (
    SpendConfirmationRequired,
    create_local_provider,
    create_remote_provider,
)
from .router import Router
from .trajectory import TrajectoryStore


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="kaaval-agent",
        description=(
            "Run the four-step NOC assurance workflow. Each accepted finding "
            "feeds the next step; any no-safe-answer result halts the chain."
        ),
    )
    parser.add_argument("--input", required=True, help="incident text")
    parser.add_argument(
        "--local-provider", choices=["mock", "ollama", "vllm"], default="mock"
    )
    parser.add_argument(
        "--remote-provider", choices=["mock", "fireworks"], default="mock"
    )
    parser.add_argument("--confirm-spend", action="store_true")
    parser.add_argument("--db", default=":memory:", help="trajectory SQLite path")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        local = create_local_provider(args.local_provider)
        remote = create_remote_provider(
            args.remote_provider, confirm_spend=args.confirm_spend
        )
    except (SpendConfirmationRequired, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    store = TrajectoryStore(args.db)
    try:
        pipeline = AssurancePipeline(Router(), local, remote, store)
        result = run_agent_workflow(
            pipeline, args.input, NOC_INCIDENT_WORKFLOW
        )
        rows = rows_for_agent_run(store, result)
        payload = {
            "run_id": result.run_id,
            "status": "completed" if result.completed else "blocked",
            "blocked_at": result.blocked_at,
            "steps": [
                {
                    "request_id": step.request_id,
                    "status": step.status,
                    "contract_conformant": step.verification.passed,
                    "attempts": step.attempts,
                    "escalated": step.escalated,
                    "accepted_answer": (
                        step.accepted_response.parsed
                        if step.accepted_response is not None
                        else None
                    ),
                }
                for step in result.steps
            ],
            "trajectory_rows": len(rows),
        }
        print(json.dumps(payload, indent=2))
        return 0 if result.completed else 1
    finally:
        store.close()


if __name__ == "__main__":
    raise SystemExit(main())
