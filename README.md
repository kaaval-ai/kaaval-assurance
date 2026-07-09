# kaaval-assurance

The Kaaval **inference assurance plane** for AMD + Gemma workloads: task contracts, deterministic verification, provider-neutral routing, per-category drift tracking, and seams for sampled adversarial audit.

*Route efficiently. Verify continuously. Escalate intelligently.*

Built for the AMD Developer Hackathon ACT II (Track 3). Hackathon product wrapper: **KaavalAI**.

## What it does

Every request runs against an explicit **task contract**. The router sends it to the cheap local tier first (MockProvider by default, or Gemma via ROCm + vLLM when configured for AMD Developer Cloud); **Layer 1** verifies the response deterministically against the contract (schema, required fields, enums, ranges); failures escalate to the remote tier (MockProvider or Fireworks AI). Every attempt writes a replayable row to the SQLite **trajectory store**.

**Layer 2** aggregates that telemetry: pass rates, failure rates by verifier check, escalation rates, latency percentiles, cost per verified answer, and a per-category EWMA drift score over local-tier verification outcomes — deterministic code over replayable rows, no model calls.

**Layer 3** is a sampled, offline adversarial audit of accepted answers — see its section below. It is a statistical sensor feeding trend statistics, never a per-response gate.

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

The escalation tier can target a Fireworks-hosted model instead of the remote mock. Configuration is environment-only (`FIREWORKS_API_KEY`, `FIREWORKS_MODEL`, `FIREWORKS_BASE_URL`, `FIREWORKS_TIMEOUT_SECONDS`, optional `FIREWORKS_COST_PER_PROMPT_TOKEN` / `FIREWORKS_COST_PER_COMPLETION_TOKEN`). Keep secrets in an untracked local env file and source it — never commit keys. For the AMD hackathon, set `FIREWORKS_MODEL` to a model available in your credit allocation, such as the Kimi or MiniMax endpoints listed for the event, rather than assuming any default model is eligible.

```bash
set -a; source .env; set +a
kaaval-eval --dataset data/eval/telecom_gold.jsonl \
  --remote-provider fireworks --failure-mode bad_enum --failure-rate 0.4
```

The local tier stays mock here; injected local failures escalate to the live Fireworks endpoint, and Layer 1 verifies whatever comes back — malformed or prose output is recorded as a `json_parse` failure, not silently accepted.

### Local Gemma tier via vLLM

`VllmProvider` is the planned local Gemma tier for the AMD hackathon notebook pod, targeting any OpenAI-compatible vLLM endpoint (ROCm backend). Configuration is environment-only: `VLLM_MODEL` (required), `VLLM_BASE_URL`, `VLLM_TIMEOUT_SECONDS`, optional `VLLM_API_KEY`, plus runtime knobs mirroring vLLM engine args — `VLLM_DTYPE`, `VLLM_KV_CACHE_DTYPE` (FP8 KV cache when supported), `VLLM_ENABLE_PREFIX_CACHING`, `VLLM_GPU_MEMORY_UTILIZATION`, `VLLM_TENSOR_PARALLEL_SIZE`, `VLLM_STRUCTURED_OUTPUTS`.

A `RuntimeProfile` records the configured serving settings (dtype, KV-cache dtype, tensor parallelism, GPU memory utilization, prefix caching, structured-output mode) alongside eval output, so results state which runtime configuration produced them. These are recorded settings, not measured performance claims. When structured outputs are enabled the request asks for a JSON object, but Layer 1 verifies every output either way — prose or fenced responses fail the contract check and escalate.

```bash
# local Gemma via vLLM first, Fireworks escalation
set -a; source .env; set +a
kaaval-eval --dataset data/eval/telecom_gold.jsonl \
  --local-provider vllm --remote-provider fireworks
```

## Layer 3: sampled adversarial audit

An offline audit samples a configurable fraction (default 10%) of Layer-1-accepted answers and sends each to a challenger model with the task input, the contract rules, and the contract's semantic intent. The challenger returns strict violations JSON. Detection is model-generated; aggregation and thresholding over that structured output are deterministic code. The audit runs after responses are already served — it never gates the live path and never changes request success semantics.

**Calibration gate.** Before any audit signal can be trusted, the challenger runs against the known-good gold answers in the eval set. If it flags more than the threshold (default 20%) of verified-correct answers, calibration fails and audit results are marked untrusted — displayed, but barred from feeding routing. This prevents an over-eager critic from poisoning the drift signal. It is a statistical sensor, not a judge of record.

```bash
# mock challenger, no keys, no network
kaaval-eval --dataset data/eval/telecom_gold.jsonl --audit-provider mock --audit-sample-rate 1.0

# Fireworks challenger (calibrates against gold answers first)
set -a; source .env; set +a
kaaval-eval --dataset data/eval/telecom_gold.jsonl --audit-provider fireworks
```

Audit results persist into the trajectory rows (`audit_sampled`, `audit_result`, `audit_violations`), and the report includes sampled counts, violation counts by severity, calibration false-positive rate, and audit cost per verified accepted answer.

### Why this is AMD/Gemma-native

- The local tier serves open-weight Gemma-family models through vLLM, intended for AMD Developer Cloud with the ROCm backend; the model id stays configurable and `RuntimeProfile` records the ROCm/vLLM/Gemma serving settings actually used.
- Structured-output requests plus deterministic Layer-1 verification make small local models safely usable: malformed output fails the contract check instead of reaching users.
- Audit prompts use a stable per-contract prefix (schema, scoring policy, contract rules) with case content appended last — designed to benefit from vLLM automatic prefix caching and Fireworks prompt cache keys when available. No cache-hit rates are claimed without measurement.
- FP8 KV cache, tensor parallelism, and GPU memory utilization are recorded as serving knobs in the runtime profile, not claimed results.
- Fireworks serves as the remote challenger/escalation tier with strict JSON output; optional prompt-cache keys and logprob telemetry are passed through when configured, and provider-reported cached tokens are recorded when returned.

## AMD Hackathon Runtime Notes

### Final 2-day runbook

The complete submission-push runbook lives in [docs/hackathon-ops.md](docs/hackathon-ops.md): pod setup, Gemma-first serving with truthful fallback, runtime probe, the four smoke/demo scripts, Fireworks budget guardrails, and the submission checklist. Copy [.env.example](.env.example) to `.env` to configure; `python -m kaaval_assurance.runtime_probe` records what the host and endpoint actually provide (JSON, secrets redacted) and turns runtime claims from configured into measured.

Budget rules in one line: run the always-remote baseline once and cache its DB, iterate demos on the mock challenger, spend Fireworks credits on one final escalation run and one final audit sample, and let the telemetry fields — cost per verified answer, remote calls avoided — make the cost argument.

The hackathon notebook environment is accessed through `https://notebooks.amd.com/hackathon`. Keep the repo, virtual environment, generated SQLite runs, and telemetry artifacts under `/workspace` so they survive pod restarts. The FAQ describes about 48 GB of GPU memory for the hackathon compute instance, so the local model must fit alongside vLLM, KV cache, and runtime overhead. Start with conservative serving settings, then record the actual values in `RuntimeProfile`.

```bash
cd /workspace
git clone https://github.com/kaaval-ai/kaaval-assurance.git
cd kaaval-assurance
pip install -e ".[dev]"

# Gemma-first: pick a Gemma model that fits the pod GPU (see docs/hackathon-ops.md).
vllm serve <chosen-gemma-model> --port 8000 --gpu-memory-utilization 0.3
```

In a second terminal:

```bash
export VLLM_BASE_URL=http://localhost:8000/v1
export VLLM_MODEL=<chosen-gemma-model>
export VLLM_MODEL_FAMILY=gemma
export VLLM_HARDWARE_TARGET=amd-hackathon-gpu

kaaval-eval --dataset data/eval/telecom_gold.jsonl \
  --local-provider vllm \
  --remote-provider mock \
  --audit-provider mock \
  --audit-sample-rate 1.0 \
  --telemetry-summary
```

If Gemma cannot be served reliably on the pod, use the FAQ Qwen command only as an operational fallback and set `VLLM_MODEL_FAMILY=qwen` so telemetry stays truthful.

Track 3 submission framing: no Docker image is required for Track 3; AMD compute proof comes from the runtime probe and telemetry artifacts; a public hosted URL can replay captured AMD telemetry rather than serving a live endpoint.

Use Fireworks credits for the expensive path: remote escalation, always-remote baselines, and challenger audits. The core demo should show that local/open-weight tokens are verified first and external Fireworks calls are minimized.

## Demo console and submission

A lightweight Streamlit console ([apps/demo_console/app.py](apps/demo_console/app.py)) replays recorded assurance telemetry: request flow, runtime profile with source tags, the telemetry truth table, and a replayable trajectory example. It prefers real artifacts from `artifacts/` and ships with synthetic sample data ([demo_artifacts/sample/](demo_artifacts/sample)) so it runs anywhere without secrets or AMD access — suitable for Streamlit Community Cloud or Hugging Face Spaces as a hosted replay surface.

```bash
pip install -e ".[demo]"
streamlit run apps/demo_console/app.py
```

Track 3 submission assets, video plan, deck outline, and hosting guide: [docs/submission-checklist.md](docs/submission-checklist.md) · [docs/demo-script.md](docs/demo-script.md) · [docs/deck-outline.md](docs/deck-outline.md) · [docs/hosted-demo.md](docs/hosted-demo.md).

## Telemetry Truth Layer

Every demo claim maps to a stored telemetry field. `--telemetry-summary` prints a judge-ready block where each line carries its source tag: `measured` (derived from trajectory rows and run results), `configured` (recorded runtime settings from the vLLM/Gemma profile — settings, not measurements), `not_available` (the provider or run did not produce the value), or `planned` (intended AMD Developer Cloud deployment not yet executed). AMD/Gemma/vLLM runtime settings are recorded, never invented; the audit challenger signal is model-generated while aggregation and thresholding stay deterministic; and cost-savings figures appear only when a cached always-remote baseline run exists.

```bash
# judge-ready truth block after a mock run with audit
kaaval-eval --dataset data/eval/telecom_gold.jsonl \
  --audit-provider mock --audit-sample-rate 1.0 --telemetry-summary

# with an always-remote baseline for cost-savings lines
kaaval-eval --dataset data/eval/telecom_gold.jsonl \
  --telemetry-summary --always-remote-baseline-db baseline.db

# machine-readable / file outputs
kaaval-eval --dataset data/eval/telecom_gold.jsonl --telemetry-json
kaaval-eval --dataset data/eval/telecom_gold.jsonl --telemetry-markdown telemetry.md
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
├── models.py          # ModelResponse, VerificationResult, TrajectoryRow, RuntimeProfile
├── contracts/         # TaskContract model + telecom contract definitions
├── providers/         # Provider interface + MockProvider, Fireworks, vLLM Gemma
├── router.py          # per-category tier choice, policy-note routing reasons
├── routing_policy.py  # deterministic drift bands -> per-category thresholds
├── verifier.py        # Layer 1 deterministic contract checks
├── metrics.py         # Layer 2 aggregation + per-category EWMA drift
├── trajectory.py      # SQLite store, replayable rows, audit fields
├── audit/             # Layer 3: challenger prompts, calibration gate, sampled runner
├── eval/              # gold dataset loader, eval runner, closed-loop demo, CLI
└── pipeline.py        # end-to-end request path
```

## Deployment Targets

kaaval-assurance is designed to run provider-neutral assurance flows across:

- local/open-weight serving on the AMD hackathon notebook GPU via ROCm + vLLM
- remote escalation through Fireworks AI-hosted model endpoints
- deterministic MockProvider execution for tests, evals, and demos

Provider configuration is intentionally injectable, and trajectory records remain provider-neutral: provider, model_id, tier, latency, token counts, cost, and verifier outcome.

Planned local tier: a model that fits the AMD hackathon notebook GPU memory budget (the event FAQ says about 48 GB, with KV cache and runtime overhead also consuming memory). Model ID, ROCm version, vLLM version, GPU details, and serving knobs are recorded in telemetry once deployed.

## License

MIT — see [LICENSE](LICENSE).
