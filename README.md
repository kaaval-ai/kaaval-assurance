# Kaaval-AI: kaaval-assurance

The Kaaval **inference assurance plane**: task contracts, deterministic verification, per-category drift tracking, and sampled adversarial audit for AMD + Gemma agent workloads.

*Route efficiently. Verify continuously. Escalate intelligently.*

Built for the AMD Developer Hackathon ACT II (Track 3). Product wrapper: **KaavalAI**.

## What it does

Every request runs against an explicit **task contract**. The router sends it to the cheap local tier first (Gemma on AMD Instinct MI300X via ROCm + vLLM); **Layer 1** verifies the response deterministically against the contract (schema, required fields, enums, ranges); failures escalate to the remote tier (Fireworks). Every attempt writes a replayable row to the SQLite **trajectory store**.

**Layer 2** aggregates that telemetry: pass rates, failure rates by verifier check, escalation rates, latency percentiles, cost per verified answer, and a per-category EWMA drift score over local-tier verification outcomes — deterministic code over replayable rows, no model calls.

Coming layers:

- **Layer 3** — sampled, offline adversarial audit of accepted answers (5–10%). An LLM challenger produces structured violations JSON; deterministic code validates, aggregates, and thresholds it. It is a statistical sensor feeding trend statistics, never a per-response gate.

## Quickstart (mock mode, zero cloud access)

```bash
pip install -e ".[dev]"
pytest
```

```python
from kaaval_assurance.pipeline import AssurancePipeline
from kaaval_assurance.providers import MockProvider
from kaaval_assurance.router import Router
from kaaval_assurance.trajectory import TrajectoryStore

pipeline = AssurancePipeline(
    router=Router(),
    local_provider=MockProvider(tier="local"),
    remote_provider=MockProvider(tier="remote", model_id="mock-remote-strong"),
    store=TrajectoryStore("trajectory.db"),
)

result = pipeline.handle_request(
    "Core router CR-04 dropped all BGP sessions; region south offline.",
    "telecom.severity_classification",
)
print(result.verification.passed, result.routing.reason)
```

## Eval harness

Gold dataset: 16 telecom-triage cases (4 per contract) with known-good gold answers in [data/eval/telecom_gold.jsonl](data/eval/telecom_gold.jsonl). Gold answers double as the Layer-3 challenger false-positive calibration set later. All eval data is synthetic.

```bash
# healthy local tier
python -m kaaval_assurance.eval.cli --dataset data/eval/telecom_gold.jsonl

# simulate local-tier degradation -> escalations, drift, rescue cost
python -m kaaval_assurance.eval.cli --failure-mode bad_enum --failure-rate 0.4 --db run.db

# full report as JSON
python -m kaaval_assurance.eval.cli --json
```

Installed entrypoint: `kaaval-eval` (same flags).

### Remote escalation via Fireworks AI

The escalation tier can target a Fireworks-hosted model instead of the remote mock. Configuration is environment-only (`FIREWORKS_API_KEY`, `FIREWORKS_MODEL`, `FIREWORKS_BASE_URL`, `FIREWORKS_TIMEOUT_SECONDS`, optional `FIREWORKS_COST_PER_PROMPT_TOKEN` / `FIREWORKS_COST_PER_COMPLETION_TOKEN`). Keep secrets in an untracked local env file and source it — never commit keys.

```bash
set -a; source .env; set +a
kaaval-eval --dataset data/eval/telecom_gold.jsonl \
  --remote-provider fireworks --failure-mode bad_enum --failure-rate 0.4
```

The local tier stays mock here; injected local failures escalate to the live Fireworks endpoint, and Layer 1 verifies whatever comes back — malformed or prose output is recorded as a `json_parse` failure, not silently accepted.

### Local Gemma tier via vLLM

`VllmProvider` is the planned local Gemma tier for AMD Developer Cloud, targeting any OpenAI-compatible vLLM endpoint (ROCm backend). Configuration is environment-only: `VLLM_MODEL` (required), `VLLM_BASE_URL`, `VLLM_TIMEOUT_SECONDS`, optional `VLLM_API_KEY`, plus runtime knobs mirroring vLLM engine args — `VLLM_DTYPE`, `VLLM_KV_CACHE_DTYPE` (FP8 KV cache), `VLLM_ENABLE_PREFIX_CACHING`, `VLLM_GPU_MEMORY_UTILIZATION`, `VLLM_TENSOR_PARALLEL_SIZE`, `VLLM_STRUCTURED_OUTPUTS`.

A `RuntimeProfile` records the configured serving settings (dtype, KV-cache dtype, tensor parallelism, GPU memory utilization, prefix caching, structured-output mode) alongside eval output, so results state which runtime configuration produced them. These are recorded settings, not measured performance claims. When structured outputs are enabled the request asks for a JSON object, but Layer 1 verifies every output either way — prose or fenced responses fail the contract check and escalate.

```bash
# local Gemma via vLLM first, Fireworks escalation
set -a; source .env; set +a
kaaval-eval --dataset data/eval/telecom_gold.jsonl \
  --local-provider vllm --remote-provider fireworks
```

## Task contracts (initial set)

Four telecom incident-triage contracts, versioned:

| Contract | Category |
|---|---|
| `telecom.severity_classification` | Severity tier (P1–P4) with confidence + rationale |
| `telecom.component_extraction` | Involved components + root-cause component |
| `telecom.incident_summary` | NOC handover summary, impact, affected services |
| `telecom.next_action_recommendation` | Next action with urgency + justification |

## Layout

```
src/kaaval_assurance/
├── models.py        # ModelResponse, VerificationResult, TrajectoryRow, ...
├── contracts/       # TaskContract model + telecom contract definitions
├── providers/       # Provider interface + MockProvider (vLLM/Fireworks later)
├── router.py        # per-category tier choice; Layer 2 tightening seam
├── verifier.py      # Layer 1 deterministic contract checks
├── trajectory.py    # SQLite store, replayable rows, audit columns reserved
└── pipeline.py      # end-to-end request path
```

## Deployment Targets

kaaval-assurance is designed to run provider-neutral assurance flows across:

- local/open-weight Gemma serving on AMD Developer Cloud via ROCm + vLLM
- remote escalation through Fireworks AI-hosted model endpoints
- deterministic MockProvider execution for tests, evals, and demos

Provider configuration is intentionally injectable, and trajectory records remain provider-neutral: provider, model_id, tier, latency, token counts, cost, and verifier outcome.

Planned local tier: `gemma-3-12b-it` on **AMD Instinct MI300X** (192 GB HBM3). Model ID, ROCm version, and GPU details will be recorded here once deployed.

## License

MIT — see [LICENSE](LICENSE).
