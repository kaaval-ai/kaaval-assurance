#!/usr/bin/env bash
# Mock-only demo: grounding catch -> recovery -> EWMA routing adaptation.
# Zero network, zero keys, zero spend. MockProvider both tiers only.
set -euo pipefail
cd "$(dirname "$0")/.."

if [ -n "${KAAVAL_PYTHON:-}" ]; then
  PYTHON_BIN="$KAAVAL_PYTHON"
elif [ -x ".venv/bin/python" ]; then
  PYTHON_BIN=".venv/bin/python"
elif command -v uv >/dev/null 2>&1; then
  PYTHON_BIN="uv run python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
else
  echo "Error: Python interpreter not found." >&2
  exit 1
fi

PYTHONPATH=src $PYTHON_BIN -m kaaval_assurance.grounding_ewma_demo
