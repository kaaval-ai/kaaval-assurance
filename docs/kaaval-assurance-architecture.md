# Kaaval Assurance — Architecture Walkthrough

Companion notes for [kaaval-assurance-architecture.html](kaaval-assurance-architecture.html) — a single-file, offline, dependency-free interactive diagram. Open it in any browser: dark mission-control theme, animated packets, a step player (play / pause / next / previous / reset), three execution modes, and a side panel that explains each step's payload, telemetry source tag, and why it matters.

## What the diagram shows

The full assurance plane as data actually moves through it: task input → provider router → Gemma local tier → Layer 1 contract verifier → Fireworks escalation when needed → trajectory store → Layer 2 EWMA drift tracker → Layer 3 sampled audit → telemetry truth layer → demo console and submission artifacts, with the runtime probe feeding measured host facts into telemetry.

Three modes relabel the local tier honestly:

- **Dev Mode** — mock + Ollama: proves the code path on a laptop. Not AMD usage, and never presented as such.
- **AMD GPU Mode** — Gemma on ROCm + vLLM on an AMD GPU VM / AMD Developer Cloud: the deployment path. Marked **pending** until measured artifacts exist.
- **Submission Replay Mode** — captured artifacts only; no secrets, no live endpoints.

## The five flows

1. **Verified Local Pass** — the happy path: local Gemma answers, Layer 1 passes all contract checks, the answer is accepted, a replayable trajectory row is written, and telemetry records provider, model id, latency, tokens, verifier result, and cost.
2. **Contract Failure → Escalation** — the local output breaks the contract (`enum:severity`, `json_parse`, …). Layer 1 rejects with a stable check id, the router escalates to Fireworks, and the remote answer goes through the *same* verifier before acceptance. Both attempts persist.
3. **Drift-Aware Routing** — repeated failures in one category raise its EWMA drift score; a deterministic policy tightens that category's routing threshold; future requests pre-route to the remote tier with the drift band recorded in the routing reason. Remote-calls-avoided is shown only when a cached always-remote baseline exists.
4. **Sampled Audit** — a seeded sampler picks ~10% of accepted answers offline. The calibration gate runs first: the challenger must not over-flag known-good gold answers, or its signal is marked untrusted. Detection is model-generated; aggregation and thresholding over the structured violations output are deterministic. It is a statistical sensor, never a live per-response judge.
5. **AMD Proof Run** — the runtime probe records GPU/runtime facts (rocm-smi, vLLM version, served model id, model family), Gemma serves through ROCm + vLLM, the eval writes telemetry artifacts, and the hosted demo replays them. **The AMD GPU measured run is pending until those artifacts exist** — this flow shows the plan and the evidence path, not a completed run.

## Why this is an inference assurance plane, not a debate bot

No model argues with another model in the request path. Layer 1 is deterministic code; escalation is verifier-gated, not vibes-gated; drift tracking is arithmetic over stored rows; and the only adversarial component is offline, sampled, and calibration-gated. The product is governed inference with an evidence trail — replayable trajectories, source-tagged claims, and a cost per verified answer.

## Built vs pending

**Built and tested:** provider-neutral runtime with explicit provider switching (mock / Ollama / vLLM / Fireworks), task contracts, Layer 1 verifier, Layer 2 EWMA + closed-loop routing, Layer 3 sampled audit with calibration gate, trajectory store, telemetry truth layer, runtime probe, eval CLI, Streamlit demo console.

**Pending:** the AMD GPU measured run. Until runtime probe + telemetry artifacts from an AMD GPU VM exist, all AMD runtime claims stay tagged `configured` / `planned`.

## How this supports Track 3 judging

Track 3 pre-screening inspects the repo, the slide deck PDF, and the hosted URL — not the demo video. This walkthrough gives judges the architecture in two minutes without running anything, and every animated claim maps to a mechanism that exists in `src/kaaval_assurance/` with a stored telemetry field behind it. AMD usage is demonstrated through artifacts (probe + eval telemetry), and the diagram says plainly which artifact is still pending.
