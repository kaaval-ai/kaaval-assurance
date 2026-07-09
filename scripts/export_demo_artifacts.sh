#!/usr/bin/env bash
# Export judge-facing demo artifacts in mock mode: zero network, zero spend.
# Output: eval transcript, telemetry truth markdown, closed-loop demo
# transcript, trajectory DBs — everything the video/deck needs without a
# live endpoint.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p artifacts

PYTHONPATH=src python3 -m kaaval_assurance.eval.cli \
  --dataset data/eval/telecom_gold.jsonl \
  --audit-provider mock --audit-sample-rate 1.0 \
  --telemetry-summary \
  --telemetry-markdown artifacts/telemetry-truth.md \
  --db artifacts/trajectory-demo.db | tee artifacts/eval-output.txt

PYTHONPATH=src python3 -m kaaval_assurance.eval.cli \
  --dataset data/eval/telecom_gold.jsonl \
  --closed-loop-demo --failure-mode bad_enum --failure-rate 1.0 \
  | tee artifacts/closed-loop-demo.txt

echo "demo artifacts written to artifacts/"
