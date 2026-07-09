# Demo Video Script (~2 minutes)

Target: judge understands the problem, sees the loop close, and hears the
honesty lines. Screen: demo console + terminal. Numbers on screen must come
from recorded telemetry artifacts.

## 0:00 — Problem (20s)

"Agent workloads want cheap local models, but nobody trusts them unattended.
Kaaval Assurance is an inference assurance plane: every answer is verified
against an explicit task contract, quality drift is detected per category,
and routing tightens itself before bad answers pile up."

Screen: console header + request-flow panel.

## 0:20 — Architecture (25s)

"Requests hit a provider-neutral router. The local tier is Gemma-first —
open weights served through vLLM on the AMD hackathon GPU. Layer 1 verifies
every response deterministically: schema, required fields, enums, ranges.
Failures escalate to a Fireworks-hosted remote model. Every attempt is stored
as a replayable trajectory row."

Screen: flow panel; open the replayable trajectory example — local attempt
fails Layer 1, escalated remote attempt passes.

## 0:45 — Local Gemma on AMD (25s)

"The runtime profile records exactly what served each answer — model id,
dtype, KV-cache mode, GPU memory settings — and the runtime probe records
what the AMD pod actually provided. Everything is source-tagged: measured,
configured, or planned. We don't claim numbers we didn't measure."

Screen: runtime profile panel with source badges; probe output from the pod.

## 1:10 — Verification and escalation (25s)

"Here a category degrades: enum failures spike, per-category drift crosses
0.5, and the routing policy pre-routes that category to the remote tier —
deterministically, with the reason recorded on every decision. Quality
recovers, and the cost per verified answer shows exactly what that recovery
cost."

Screen: closed-loop demo transcript (phase B drift → policy → phase C).

## 1:35 — Telemetry truth (20s)

"Layer 3 adversarially audits a sample of accepted answers — offline, never
gating a response. The challenger is calibrated against known-good gold
answers first; if it over-flags, its signal is untrusted. Honesty lines:
our shift data is synthetic, and Layer 3 is a sampled offline audit signal
feeding trend statistics — not a judge of record."

Screen: telemetry truth table — every claim with its source tag; calibration
false-positive rate visible.

## 1:55 — Close (10s)

"Cheap local tokens on AMD, verified answers, self-tightening routing, and a
telemetry trail for every claim. Kaaval Assurance — route efficiently, verify
continuously, escalate intelligently."

Screen: console header; repo URL on screen.
