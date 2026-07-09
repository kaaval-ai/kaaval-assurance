#!/usr/bin/env bash
# vLLM smoke against the pod endpoint: probe first (measured evidence), then
# a Gemma-first local-tier eval with the mock remote tier (no Fireworks spend).
set -euo pipefail
cd "$(dirname "$0")/.."
if [ -f .env ]; then set -a; . ./.env; set +a; fi
mkdir -p artifacts

# Probe gates the run: measured evidence first, and no point evaluating
# against an endpoint that is not serving.
PYTHONPATH=src python3 -m kaaval_assurance.runtime_probe \
  --text --require-endpoint --output artifacts/runtime-probe.json

: "${VLLM_MODEL:?VLLM_MODEL not set; pick one of the served models listed by the probe}"

PYTHONPATH=src python3 -m kaaval_assurance.eval.cli \
  --dataset data/eval/telecom_gold.jsonl \
  --local-provider vllm \
  --telemetry-summary \
  --telemetry-markdown artifacts/telemetry-vllm.md \
  --db artifacts/trajectory-vllm.db

echo "artifacts: artifacts/runtime-probe.json artifacts/telemetry-vllm.md artifacts/trajectory-vllm.db"
