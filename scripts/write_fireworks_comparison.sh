#!/usr/bin/env bash
set -e

if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <smoke_db_path> <baseline_db_path>"
    exit 1
fi

SMOKE_DB=$1
BASELINE_DB=$2

# Ensure using the correct python interpreter
PYTHON="/Users/hari/Documents/amd-hackathon/.venv/bin/python"

TIMESTAMP=$(date -u +"%Y%m%dT%H%M%SZ")
OUTPUT_PREFIX="artifacts/fireworks-cost-comparison-${TIMESTAMP}"

echo "Comparing Fireworks smoke vs baseline..."
$PYTHON -m kaaval_assurance.compare_runs --smoke-db "$SMOKE_DB" --baseline-db "$BASELINE_DB" --output-prefix "$OUTPUT_PREFIX"

echo "Comparison complete."
echo "Results:"
echo "- ${OUTPUT_PREFIX}.json"
echo "- ${OUTPUT_PREFIX}.md"
