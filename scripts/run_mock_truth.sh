#!/usr/bin/env bash
# Mock truth run: zero network, zero keys, zero spend.
# Produces the judge-ready telemetry block plus artifacts under artifacts/.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p artifacts

PYTHONPATH=src python3 -m kaaval_assurance.eval.cli \
  --dataset data/eval/telecom_gold.jsonl \
  --audit-provider mock --audit-sample-rate 1.0 \
  --telemetry-summary \
  --telemetry-markdown artifacts/telemetry-mock.md \
  --db artifacts/trajectory-mock.db

echo "artifacts: artifacts/telemetry-mock.md artifacts/trajectory-mock.db"
