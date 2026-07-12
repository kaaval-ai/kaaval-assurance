# Kaaval Assurance

![Kaaval Assurance — Agentic Guardian assurance engine for AI decisions on Gemma-first AMD workloads](assets/kaaval-assurance-banner.svg)

**An Agentic Guardian assurance engine for AI decisions on Gemma-first AMD
workloads.**

Kaaval Assurance sits between a task and an AI decision. It runs a local
open-weight tier first, checks every response against an explicit task
contract before anyone downstream sees it, escalates only when verification
fails or quality drifts, and records every attempt as a replayable trajectory.
The result is not "a model answered" — it is a contract-checked answer with
evidence: who served it, what it cost, which checks it passed, and why it was
routed there.

For agents and multi-step workflows, this is the check before a consequential
action: refund, escalation, classification, approval, or next step. This build
includes a four-step contract-gated assurance workflow; it does not claim
general autonomous planning or arbitrary tool execution. Built for AMD
Developer Hackathon ACT II, Track 3 (Unicorn / Open Innovation). Product
wrapper: **KaavalAI**; this repository is the reusable assurance engine and a
first working slice of the broader Kaaval-AI Agentic Guardian ecosystem.

> **What "verified" means here.** Throughout this repo, *verified* means the
> answer passed every **Layer-1 deterministic contract check** — JSON shape,
> required fields, enums, numeric ranges, and phrase-triggered grounding
> rules. It is a contract-conformance claim, not a semantic-correctness
> claim; that boundary is deliberate and covered in
> [Limitations](#limitations).

*Route efficiently. Verify continuously. Escalate intelligently.*

## Why this matters

Open-weight models are now good enough to run real workloads locally. At the
same time, AI answers are becoming business decisions: refunds, approvals,
classifications, incident severity, and next actions. What teams lack is the
assurance layer: something that tests whether an answer meets an explicit
contract, decides when to pay for a stronger model, and preserves evidence of
either decision. Routers predict. Kaaval checks declared controls and leaves a
receipt.

The question Kaaval Assurance answers is not *which model responded*. It is:
**can we prove the answer satisfied the task contract, at the lowest reliable
cost?**

This is not a debate bot, a chatbot, or a generic eval app. It is governed
inference: verifier-gated escalation, source-tagged telemetry, and a cost per
contract-conformant answer you can defend line by line.

## What it does

1. A provider-neutral router sends each request to the **Gemma-first local
   tier** — open-weight local inference through an OpenAI-compatible endpoint
   (Ollama for development, ROCm + vLLM on an AMD GPU VM for deployment).
2. **Layer 1 contract verification** checks the response against the task
   contract deterministically: JSON shape, required fields, enums, numeric
   ranges. Pure code; no model judges another model inline.
3. Failures escalate to the **Fireworks AI escalation tier**, whose response
   is verified the same way — malformed output from the expensive model fails
   too, recorded as such.
4. **Layer 2 trajectory / EWMA drift tracking** aggregates verifier outcomes
   per task category. A deterministic policy maps drift bands to routing
   thresholds: a category that starts failing gets pre-routed to the remote
   tier, with the reason written into every routing decision.
5. **Layer 3 sampled adversarial audit** re-examines a sample (default 10%)
   of already-accepted answers offline. A **calibrated challenger** attacks
   each answer against the contract's semantic intent and returns structured
   violations JSON. Detection is model-generated; aggregation and
   thresholding over that output are deterministic. Before the signal is
   displayed as FP-calibrated, the challenger must stay below a false-positive
   threshold on known-good reference answers. This calibration only detects
   over-eager critics, not approve-everything critics. Layer 3 is display-only
   in this build and never gates a live response or feeds routing.
6. Every attempt — input, raw output, checks, tokens, latency, cost, routing
   reason — lands in a SQLite trajectory store as a **replayable trajectory**
   row. Any request can be replayed and re-verified later.

## Architecture

[![Kaaval Assurance architecture flow](assets/kaaval-architecture-flow.svg)](docs/kaaval-assurance-architecture.html)

Click the flow for the interactive walkthrough: [HTML](docs/kaaval-assurance-architecture.html) · [notes](docs/kaaval-assurance-architecture.md)

## Built features

| Capability | Status | Why it matters |
|---|---|---|
| Provider-neutral runtime + factory | Built | Local/remote tiers swap by config, never by code edits; switching is explicit and telemetry-visible |
| Mock provider | Built | Entire loop runs deterministically with zero cloud access — tests, demos, CI |
| Ollama local provider | Built | Open-weight local inference on a dev machine; validates the local-tier path before GPU time is spent |
| vLLM provider for AMD GPU VM | Built — measured on AMD ROCm | Gemma served through the real provider path; runtime, endpoint, verifier, token, latency, and hardware evidence captured |
| Fireworks AI escalation tier | Built, smoke-tested live | Contract-conformant remote escalation with cost/token capture; spend requires explicit confirmation |
| Layer 1 contract verifier | Built | Deterministic accept/reject with stable check IDs — the source of truth |
| Layer 2 EWMA drift + closed-loop routing | Built | Detects per-category degradation and tightens routing automatically, with recorded reasons |
| Layer 3 sampled audit + FP calibration | Built, display-only | Samples accepted answers as a statistical sensor; model-generated findings do not gate responses or feed routing |
| Multi-step assurance workflow | Built | Four contract-gated decisions share context; a `no_safe_answer` step halts downstream work |
| Telemetry truth layer | Built | Every judge-facing claim maps to a stored field with a source tag |
| Runtime probe | Built | Turns runtime claims from configured into measured; redacts secrets |
| Streamlit demo console | Built | Live interactive runs plus replay of captured artifacts; hostable without secrets |
| Inference Flight Deck UI (React) | Built | Evidence Baseline replays immutable telemetry/trajectory/probe artifacts; Live Session connects Fireworks BYOK or local Ollama/vLLM and feeds real responses into the same pipeline, EWMA, telemetry, and receipt readers. |

The full test suite (330+ tests) runs network-free; live calls are explicit,
opt-in CLI/script paths.

## Enterprise value

As AI answers become refunds, approvals, classifications, and next actions,
enterprises inherit operational exposure from decisions they may not be able to
reconstruct. Kaaval makes each tested decision observable: provider, contract
checks, routing reason, drift state, latency, tokens, cost, and acceptance
status travel together as a replayable receipt.

| Stakeholder | Current exposure | What Kaaval changes |
|---|---|---|
| **AI platform teams** | Local models reduce inference cost, but opaque failures make unattended use risky | Contract-gated local inference with selective escalation and measured cost per conformant answer |
| **Risk, governance, and audit teams** | Fluent output leaves weak evidence of which controls ran | Versioned contracts, stable check IDs, source-tagged telemetry, and replayable trajectories |
| **Security and operations teams** | Provider outages and behavior shifts are difficult to reconstruct | Recorded transport failures, per-category drift, routing decisions, and runtime-to-answer provenance |
| **Insurers and technology-risk assessors** | AI controls are often described only through policy documents | Inspectable evidence of control execution, rejection, recovery, runtime provenance, and human-review boundaries |

Kaaval does not claim to eliminate liability or guarantee lower insurance
premiums. Within synthetic and controlled evaluations, this build demonstrates
that contract-invalid outputs and provider outages can be caught before
acceptance, failed answers can be escalated, repeated local failures can alter
routing, and each tested decision retains a source-tagged receipt. That evidence
is a foundation for empirically evaluating broader operational risk as the
Kaaval-AI Agentic Guardian ecosystem expands.

### Product and market path

The near-term product path is a provider-neutral assurance gateway that can
start in **shadow mode**: observe model decisions, evaluate contracts, and
produce receipts without blocking production. After teams validate their
contracts and telemetry, the same assurance engine can gate consequential
actions. Shadow mode is a deployment roadmap item, not a distinct switch in
this hackathon build.

The commercial hypothesis is an enterprise platform subscription with
usage-based pricing per contract-conformant decision, plus self-hosted
deployments for customers that need model traffic and evidence to remain
inside their boundary. Pricing and insurance impact are not validated claims;
the build demonstrates the technical evidence layer needed to evaluate them.

## AMD + Gemma execution model

The system is designed around a **Gemma-first local tier on AMD GPU
infrastructure**: open weights, an open serving stack (ROCm + vLLM), and
hardware the operator controls — which is also what makes deeper white-box
signals such as logprobs structurally available for future assurance policies.
This build records the capability seam but does not use local-model logprobs in
routing.

Execution tiers, honestly labeled:

- **Development:** Ollama serves Gemma-family models locally for validating
  the open-weight path. This proves the code path, not AMD usage — its
  hardware target is recorded as `local-mac-ollama` and can never masquerade
  as an AMD run.
- **Deployment / proof:** one clean Gemma run through vLLM/ROCm on **AMD
  Developer Cloud** or another **AMD GPU VM**, captured through the runtime
  probe and eval telemetry. The probe records measured facts — GPU/runtime
  availability, served model id, model family, provider, latency, tokens,
  verifier results, escalations, and cost fields.
- **Measured proof:** Gemma 3 1B completed the 16-case evaluation through
  vLLM's ROCm build on an AMD/ATI `gfx1100` host with 47.98 GiB VRAM. The
  coherent evidence bundle is classified `MEASURED AMD RUN`: 16/16 answers
  passed locally, no remote escalation was required, and p50/p95 request
  latency was 324.6/479.6 ms. The exact GPU marketing name was unavailable
  from `libdrm`, so this repository does not infer one.

If Gemma cannot be served reliably on a future target GPU, the documented fallback
(Qwen via the same vLLM path) is recorded truthfully in telemetry
(`VLLM_MODEL_FAMILY=qwen`) — model id and family are telemetry fields, not
marketing claims.

### Measured AMD proof run

The July 10 capture is tied to source commit `aa8b5b2` and bundle ID
`live-5be3acfa-amd-gemma-proof`. The runtime probe confirms the configured
Gemma model was present in vLLM's served-model list and the final trajectory
records a contract-conformant `vllm-gemma` local attempt. The Flight Deck therefore
labels this coherent bundle **MEASURED AMD RUN**, rather than deriving the
label from a filename or environment variable.

The measured AMD run proves the ROCm/vLLM/Gemma execution and conformance path;
it does not by itself establish semantic accuracy. Reference-answer accuracy is
reported separately by the eval runner.

| Evidence-backed result | Value |
|---|---:|
| Evaluation cases contract-conformant locally | 16 / 16 |
| Local and final Layer-1 contract-conformance rate | 100% |
| Remote escalation rate | 0% |
| Request latency p50 / p95 | 324.6 ms / 479.6 ms |
| Final proof request | 272.9 ms; 181 prompt + 37 completion tokens |
| vLLM logged generation-throughput peak | 76.0 tokens/s |
| vLLM logged prefix-cache hit-rate peak | 74.4% |
| ROCm sampler observed GPU-use peak | 100% |
| ROCm sampler observed package-power peak | 175 W |

Start with the [measured-run report](docs/amd-measured-run.md), then inspect
the [coherent manifest](artifacts/demo-live-manifest.json),
[runtime probe](artifacts/runtime-probe.json),
[run telemetry](artifacts/demo-live-telemetry.json), and
[replayable trajectory](artifacts/demo-live-trajectory.json). Every imported
artifact is covered by the [curated checksum manifest](artifacts/SHA256SUMS-amd-aa8b5b2.txt).

## Telemetry truth layer

Every claim maps to a stored field, and every field carries a source tag:

- `measured` — derived from stored trajectory rows and run results (this
  includes derived aggregates like rates and cost-per-answer, which are
  deterministic functions of measured rows)
- `configured` — recorded runtime settings (vLLM/Gemma serving knobs), not
  measurements
- `not_available` — the provider or run did not produce the value; never
  fabricated
- `planned` — an intended execution or capability that has not yet produced
  evidence

Shipped sample data for the demo console is additionally labeled as
synthetic sample data in the UI and enforced by tests to never claim a
measured runtime.

Captured per attempt and per run: provider, model id, model family, tier,
latency, prompt/completion/total tokens, cost, verifier pass/fail with failed
check IDs, escalation reason, **remote calls avoided** (only when a cached
always-remote baseline exists), **cost per contract-conformant answer**, audit
calibration false-positive rate, and the runtime profile (endpoint type,
host, dtype, KV-cache mode, tensor parallelism, GPU memory utilization,
prefix caching, structured-output mode).

```bash
kaaval-eval --dataset data/eval/telecom_gold.jsonl \
  --audit-provider mock --audit-sample-rate 1.0 --telemetry-summary
```

## Demo

The Streamlit console ([apps/demo_console/app.py](apps/demo_console/app.py))
has two tabs:

- **Live demo run** — drives the real assurance pipeline interactively:
  choose a contract, a reference case, a local provider (mock or Ollama), a
  remote provider (mock, or Fireworks behind an explicit spend checkbox),
  and an injected failure mode; watch Layer-1 verification, escalation, and
  the trajectory rows land; export the run as artifacts.
- **Artifact replay** — renders captured artifacts: request flow, runtime
  profile with source tags, the telemetry truth table, and a replayable
  trajectory example.

A hosted copy opens the immutable evidence baseline without credentials and
can start a real live session through Fireworks BYOK or an operator-enabled
public HTTPS OpenAI-compatible endpoint ([docs/hosted-demo.md](docs/hosted-demo.md)).

Track 3 submission surfaces include this public repository, the containerized
Flight Deck, the hosted application, the slide presentation, the cover image,
and the video presentation. Measured claims remain traceable to the telemetry
artifacts committed here rather than depending on presentation copy alone.

## Quickstart

**The strongest way to evaluate Kaaval Assurance is to pull the public container. You can inspect the measured AMD evidence immediately without any credentials. Connect your own model endpoint only when you want to run live assurance.**

### 1. Run the submitted container
The judge path is container-first. It does **not** require cloning the repo or
installing Python/Node dependencies. Captured evidence opens immediately;
live execution starts after you connect Fireworks, Ollama, or vLLM.

```bash
docker pull ghcr.io/kaaval-ai/kaaval-assurance:act-ii
docker run --rm -p 8080:8000 ghcr.io/kaaval-ai/kaaval-assurance:act-ii
```

Open:
```text
http://localhost:8080
```

The container serves the compiled React Flight Deck and FastAPI API from one
process. It provides two product modes:

- **Evidence Baseline** renders the committed AMD/Gemma run and cost-comparison
  artifacts with source tags and requires no key or GPU.
- **Live Session** opens a runtime connection dialog and executes the real
  assurance pipeline against Fireworks BYOK or a host-local Ollama/vLLM server.

The image defaults to safe interactive onboarding. The application **boots without secrets or model downloads**. BYOK credentials (e.g., Fireworks API key) exist only in backend memory for 15 idle minutes and are never written to telemetry, SQLite, artifacts, logs, or browser storage. Fireworks still requires per-run spend confirmation.

### 2. Connect local Gemma through Ollama or vLLM
The image does not bundle model weights. Start Gemma in Ollama or vLLM on the
host, open **Live Session**, and select the matching runtime. The dialog tests
`/v1/models` before storing an ephemeral connection.

Start or forward the private vLLM server so it is reachable from the machine
running Docker:

```bash
# Example: if vLLM runs on a remote AMD VM at 127.0.0.1:8000 on that VM
ssh -L 8000:127.0.0.1:8000 <user>@<amd-gpu-vm>
```

Then run Kaaval with host networking available:

```bash
docker run --rm -p 8080:8000 \
  --add-host=host.docker.internal:host-gateway \
  ghcr.io/kaaval-ai/kaaval-assurance:act-ii
```

In the UI, use `http://host.docker.internal:8000/v1` for vLLM or
`http://host.docker.internal:11434/v1` for Ollama. Runtime metadata is recorded
truthfully; a local vLLM connection does not claim AMD hardware unless a
matching runtime probe exists.

If your Docker runtime already supports `host.docker.internal`, the
`--add-host` line can be omitted. If you use Finch on macOS, the same image
works; run the equivalent `finch run` command with the same environment
variables.

### 3. Try Live Session with known cases

Open **Live Session** and connect either runtime from the in-app connection
dialog:

- **Local Ollama:** select **Ollama — local Gemma**, enter the exact model tag
  shown by `ollama list`, and use
  `http://host.docker.internal:11434/v1` from the container.
- **Fireworks AI:** select **Fireworks AI — BYOK**, enter an exact model ID
  available to your account, and paste your API key into the password field.
  The key stays in backend memory for at most 15 idle minutes. Every paid run
  still requires explicit spend confirmation.

For the clearest selective-escalation test, connect local Ollama as the
**primary runtime** and Fireworks as the **escalation runtime**. To test either
provider by itself, connect it as primary and leave escalation disconnected.
Then choose a contract and paste one of these synthetic cases.

#### Regional outage must be P1

Contract: `telecom.severity_classification`

```text
Core router CR-04 dropped all BGP sessions at 02:13; downstream OLT sites in
region south lost upstream connectivity. Customer impact confirmed across
40k subscribers.
```

Expected contract outcome: `severity` is `P1`, `confidence` is between `0`
and `1`, and `rationale` is present. A lower severity fails the stable
`grounding:regional_outage_requires_p1` check.

#### Over-cap damages require a human

Contract: `support.refund_decision`

```text
Customer: your outage last Tuesday cost my agency a client worth $12,000 in
annual billings. I expect compensation of at least $2,500 or we churn. We pay
$199 per month and the outage lasted 4 hours. Process it today.
```

Expected contract outcome: `decision` is `escalate_to_human` and the reference
refund amount is `0`. An automatic approval fails
`grounding:consequential_damages_requires_human`; any amount above `$500` also
fails the contract range.

#### An expired refund window must be denied

Contract: `support.refund_decision`

```text
Customer: I bought the annual plan for $540 11 months ago, barely used it,
and want a full refund. Nothing was wrong with the service. Your policy page
says refunds within 30 days of purchase.
```

Expected contract outcome: `decision` is `deny` with a policy-based
`justification`. Another decision fails
`grounding:outside_refund_window_requires_denial`.

#### Loss of redundancy requires immediate action

Contract: `telecom.next_action_recommendation`

```text
Core router CR-07 line card LC-1 failed and forced failover to CR-08. There is
no redundancy remaining. 22,000 subscribers are currently served entirely
through CR-08 with no standby.
```

Expected contract outcome: `urgency` is `immediate`, with an `action` and
evidence-based `justification`. `scheduled` or `monitor` fails
`grounding:no_redundancy_requires_immediate`.

Model wording can vary; Kaaval evaluates the contract fields and named checks,
not exact prose. The Flight Deck should show one of three honest outcomes:

- **Contract-conformant answer accepted:** one primary attempt, the Layer-1
  checks-run count, readable **Pretty** output, raw **JSON**, telemetry, and a
  Kaaval Receipt.
- **Primary rejected, escalation accepted:** the failed local check IDs remain
  visible, the Fireworks attempt is verified against the same contract, and
  both attempts appear in the receipt.
- **No safe answer:** if transport fails or every attempted response violates
  the contract, no model payload crosses the acceptance boundary.

### 4. Optional: source development
Source setup is for contributors, not required for judging:

```bash
pip install -e ".[dev,demo]"
pytest

kaaval-eval --dataset data/eval/telecom_gold.jsonl \
  --audit-provider mock --audit-sample-rate 1.0 --telemetry-summary

kaaval-agent --input "Core router CR-04 dropped all BGP sessions; customer impact confirmed."

cd apps/flight-deck
npm install
npm run dev
```

See [apps/flight-deck/README.md](apps/flight-deck/README.md) for the
local two-terminal development loop.

### 5. Using Local Ollama Gemma & Fireworks API Simultaneously
You can run the full assurance pipeline, routing requests first to your local open-weight Gemma model (via Ollama), and intelligently escalating failing/drifting requests to the Fireworks remote tier.

1. Copy `.env.example` to `.env` and fill in the required keys:
   - `FIREWORKS_API_KEY`: Your Fireworks API token.
   - `FIREWORKS_MODEL`: The Fireworks model to use for escalation.
   - `OLLAMA_MODEL`: Your local model (e.g., `gemma:7b` or `gemma2:9b`).
   - `KAAVAL_CONFIRM_SPEND=1`: Allows the script to spend credits.

2. Execute the run with both providers active:
```bash
set -a; source .env; set +a
kaaval-eval --dataset data/eval/telecom_gold.jsonl \
  --local-provider ollama \
  --remote-provider fireworks \
  --confirm-spend \
  --telemetry-summary
```
*Note: `--failure-mode bad_enum --failure-rate 0.25` injects local failures (mock local tier only) so escalations are observable in the run output.*

### 6. Reproduce Gemma on an AMD GPU VM via ROCm + vLLM
```bash
python -m kaaval_assurance.runtime_probe --output artifacts/runtime-probe.json
kaaval-eval --dataset data/eval/telecom_gold.jsonl \
  --local-provider vllm --telemetry-summary
```

Configuration is environment-only — copy [.env.example](.env.example) to `.env` (never committed) and fill in. No secrets live in this repo.

## Current submission status

| Item | Status |
|---|---|
| Core assurance engine (contracts, Layer 1–3, routing, trajectories) | Complete |
| Fireworks API escalation path | Complete, smoke-tested; selective-escalation and always-remote comparison artifact committed |
| Local Ollama development path | Complete |
| vLLM/ROCm provider for AMD GPU VM | Complete, exercised with Gemma 3 1B |
| AMD GPU measured run | **Complete** — coherent runtime, telemetry, trajectory, ROCm, vLLM, and checksum evidence committed |
| Telemetry truth layer + runtime probe | Complete |
| Demo console (live + replay) | Complete |
| Inference Flight Deck UI (React) | Complete |
| Multi-step agent workflow (`kaaval-agent`, `/api/agent-runs`) | Complete |
| Deck / video | Complete; final local deliverables checksum-verified and handed to the team captain |
| Public container | Complete; `linux/amd64` image publicly pullable and clean-smoke verified |
| Hosted application | Pending DNS/TLS and final incognito smoke at `https://demo.kaaval.ai` |
| LabLab cover image | Pending final 16:9 export |

## Limitations

- The reference datasets are synthetic: 16 telecom cases and 10 deliberately
  difficult customer-support cases. The eval runner separately reports Layer-1
  conformance and gold accuracy over deterministic fields; unconstrained free
  text remains explicitly unscored.
- Layer 1 verifies structure and constraints — schema, required fields,
  enums, ranges. It does not certify semantic truth; that gap is exactly what
  the sampled Layer 3 audit exists to estimate, statistically.
- Layer 3 detection is model-generated, sampled, FP-calibrated, and
  display-only. Its current calibration detects over-eager critics but not
  approve-everything critics; two-sided calibration is roadmap work.
- When EWMA drift forces a category directly to remote, no local observations
  are collected to prove recovery. Current recovery is session reset or
  15-minute expiry; half-open local probes are roadmap work.
- AMD performance and usage claims are limited to the committed measured-run
  artifacts. The exact GPU marketing name is intentionally not inferred when
  the runtime reports only AMD vendor, card identifiers, and `gfx1100`.
- Cost figures are computed from configured per-token prices; accuracy
  follows the configuration.
- This is hackathon-stage software: operator environment gates are not caller
  authentication, and there is no multi-tenant hardening or production-safety
  claim. Public mode keeps paid calls, exports, and diagnostic raw output off.

## Docs

- [docs/hackathon-ops.md](docs/hackathon-ops.md) — ops runbook: pod setup, Gemma-first serving with truthful fallback, smoke sequence, Fireworks budget guardrails
- [docs/amd-measured-run.md](docs/amd-measured-run.md) — measured AMD/Gemma run results, provenance, claim boundaries, and evidence map
- [docs/deck-outline.md](docs/deck-outline.md) — 5-slide deck script
- [docs/hosted-demo.md](docs/hosted-demo.md) — hosting the replay console without secrets

## License

MIT — see [LICENSE](LICENSE).
