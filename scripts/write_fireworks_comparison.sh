#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <smoke_db_path> <baseline_db_path>"
    exit 1
fi

SMOKE_DB=$1
BASELINE_DB=$2

if [ -n "${KAAVAL_PYTHON:-}" ]; then
    PYTHON_BIN="$KAAVAL_PYTHON"
elif [ -x ".venv/bin/python" ]; then
    PYTHON_BIN=".venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python3)"
else
    echo "Python 3 is required. Set KAAVAL_PYTHON to a Python interpreter." >&2
    exit 1
fi

TIMESTAMP=$(date -u +"%Y%m%dT%H%M%SZ")
OUTPUT_PREFIX="artifacts/fireworks-cost-comparison-${TIMESTAMP}"

echo "Comparing Fireworks smoke vs baseline..."
"$PYTHON_BIN" -m kaaval_assurance.compare_runs --smoke-db "$SMOKE_DB" --baseline-db "$BASELINE_DB" --output-prefix "$OUTPUT_PREFIX"

echo "Comparison complete."
echo "Results:"
echo "- ${OUTPUT_PREFIX}.json"
echo "- ${OUTPUT_PREFIX}.md"
