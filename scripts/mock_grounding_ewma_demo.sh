#!/usr/bin/env bash
# Mock-only demo: grounding catch -> recovery -> EWMA routing adaptation.
# Zero network, zero keys, zero spend. MockProvider both tiers only.
set -euo pipefail
cd "$(dirname "$0")/.."

PYTHONPATH=src python3 -m kaaval_assurance.grounding_ewma_demo
