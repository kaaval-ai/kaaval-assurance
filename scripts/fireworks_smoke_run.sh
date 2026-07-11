#!/usr/bin/env bash
# Fireworks smoke run — SPENDS CREDITS. Guarded by KAAVAL_CONFIRM_SPEND=1.
# Small by design: mock local tier, ~25% injected failures, so only a few
# requests escalate to the live Fireworks endpoint. No audit calls here.
set -euo pipefail
cd "$(dirname "$0")/.."
if [ -f .env ]; then set -a; . ./.env; set +a; fi

: "${FIREWORKS_API_KEY:?FIREWORKS_API_KEY not set (copy .env.example to .env and fill it in)}"
: "${FIREWORKS_COST_PER_PROMPT_TOKEN:?FIREWORKS_COST_PER_PROMPT_TOKEN not set; configure the current model's USD/token input rate before a paid run}"
: "${FIREWORKS_COST_PER_COMPLETION_TOKEN:?FIREWORKS_COST_PER_COMPLETION_TOKEN not set; configure the current model's USD/token output rate before a paid run}"
if [ "${KAAVAL_CONFIRM_SPEND:-0}" != "1" ]; then
  echo "refusing to spend Fireworks credits: set KAAVAL_CONFIRM_SPEND=1 to confirm" >&2
  exit 2
fi
mkdir -p artifacts
RUN_STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
TRAJECTORY_DB="artifacts/trajectory-fireworks-smoke-${RUN_STAMP}.db"
TELEMETRY_MD="artifacts/telemetry-fireworks-smoke-${RUN_STAMP}.md"

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

PYTHONPATH=src $PYTHON_BIN -m kaaval_assurance.eval.cli \
  --dataset data/eval/telecom_gold.jsonl \
  --remote-provider fireworks \
  --confirm-spend \
  --failure-mode bad_enum --failure-rate 0.25 --seed 3 \
  --telemetry-summary \
  --telemetry-markdown "$TELEMETRY_MD" \
  --db "$TRAJECTORY_DB"

echo "artifacts: $TRAJECTORY_DB $TELEMETRY_MD"
