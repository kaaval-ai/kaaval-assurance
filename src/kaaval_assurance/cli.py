"""Unified Kaaval command tree.

Existing ``kaaval-eval`` and ``kaaval-agent`` entry points remain available for
compatibility. New developer-facing surfaces are added under ``kaaval``.
"""

from __future__ import annotations

import argparse

from . import __version__


def _positive_float(value: str) -> float:
    parsed = float(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="kaaval",
        description="Kaaval developer tools for model-call assurance.",
    )
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command", required=True)

    top = commands.add_parser(
        "top",
        help="watch assured model decisions in a read-only terminal view",
        description=(
            "Watch contract outcomes, recovery paths, provider failures, and "
            "redacted receipts. K Top never renders prompt or response content."
        ),
    )
    source = top.add_mutually_exclusive_group()
    source.add_argument(
        "--demo",
        action="store_true",
        help="use a deterministic offline SAMPLE fixture; no credentials or model",
    )
    source.add_argument(
        "--endpoint",
        "--url",
        help=(
            "Kaaval API base URL (default KAAVAL_ENDPOINT or "
            "http://127.0.0.1:8000)"
        ),
    )
    top.add_argument(
        "--refresh",
        type=_positive_float,
        default=1.0,
        metavar="SECONDS",
        help="live refresh interval (default: 1)",
    )
    top.add_argument(
        "--timeout",
        type=_positive_float,
        default=5.0,
        metavar="SECONDS",
        help="HTTP request timeout (default: 5)",
    )
    top.add_argument(
        "--filter",
        default="",
        help="initial filter over contract, model, outcome, or failed check ID",
    )
    top.add_argument(
        "--once",
        action="store_true",
        help="render one plain-text frame and exit",
    )
    top.add_argument(
        "--json",
        action="store_true",
        help="print the public operations snapshot as JSON and exit",
    )
    top.add_argument(
        "--width",
        type=int,
        default=None,
        help="plain-text render width for --once",
    )
    top.add_argument(
        "--height",
        type=int,
        default=36,
        help="plain-text render height for --once (default: 36)",
    )
    top.add_argument(
        "--no-color",
        action="store_true",
        help="accepted for script compatibility; the MVP uses textual labels",
    )
    top.add_argument(
        "--no-raw-content",
        action="store_true",
        default=True,
        help="explicitly retain the mandatory content-withheld policy",
    )
    top.set_defaults(handler="top")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.handler == "top":
        from .top import run_top

        return run_top(args)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
