# Slide Deck Outline (~5 slides, export as PDF)

Pre-screening reads this deck automatically: keep all text machine-readable
(real text, not screenshots of text), and make the AMD proof explicit on
slide 5. Every number on slides 4–5 must come from a stored telemetry or
probe artifact; leave the placeholder brackets until the AMD pod run fills
them.

## Slide 1 — Problem

**Open-weight AI is cheap but hard to trust in production.**

- Local open-weight models cut inference cost dramatically — but nobody
  ships them unattended for consequential work.
- Guardrails check format, not truth. Routers predict, then hope. Quality
  drift goes unnoticed until customers notice.
- Missing piece: continuous, deterministic verification with an audit trail
  that says exactly when the cheap tier can be trusted.

## Slide 2 — Product

**Kaaval Assurance: a Gemma-first inference assurance plane for AMD compute.**

- Every answer verified against an explicit task contract; failures escalate
  automatically; routing tightens itself per category when quality drifts.
- Local tier: open-weight Gemma served through vLLM on the AMD hackathon
  GPU. Escalation tier: Fireworks-hosted models.
- Tagline: *Route efficiently. Verify continuously. Escalate intelligently.*
- Every claim maps to a stored telemetry field — the assurance plane audits
  itself the way it audits models.

## Slide 3 — Architecture

**task input → local Gemma/vLLM on AMD → Layer 1 verifier → escalation →
Layer 2 EWMA → Layer 3 sampled audit**

- Layer 1: deterministic contract verification (schema, required fields,
  enums, ranges) on every response — pure code, no model judging models
  inline.
- Layer 2: per-category EWMA drift over verification outcomes; a
  deterministic policy maps drift bands to routing thresholds; high-drift
  categories pre-route to the remote tier with the reason recorded.
- Layer 3: sampled offline adversarial audit of accepted answers,
  calibration-gated against gold answers. Detection is model-generated;
  aggregation and thresholding are deterministic. A statistical sensor, not
  a judge of record.
- Every attempt is a replayable trajectory row: input, output, checks, cost.

## Slide 4 — Telemetry Truth

**No claim without a stored field. No field without a source tag.**

| Claim | Value | Source |
|---|---|---|
| Final verified rate | [from artifact] | measured |
| Local (Gemma-tier) pass rate | [from artifact] | measured |
| Escalation rate | [from artifact] | measured |
| Remote calls avoided vs always-remote | [from artifact] | measured |
| Cost per verified answer | [from artifact] | measured |
| Audit calibration false-positive rate | [from artifact] | measured |
| Runtime profile (Gemma/vLLM/ROCm settings) | [from artifact] | configured/measured |

- Source tags: measured (derived from stored rows), configured (recorded
  settings), not_available, planned. Sample data is labeled synthetic until
  the AMD run replaces it.

## Slide 5 — Demo + AMD Proof

**AMD compute usage, evidenced — not asserted.**

- `runtime_probe` artifact from the AMD notebook pod: GPU product name and
  VRAM via rocm-smi, vLLM version, served Gemma model id — source: measured.
- Pod eval run: local Gemma tier verified rates + runtime profile recorded
  in telemetry ([artifact filename]).
- Hosted replay console (URL): replays the captured AMD telemetry — no live
  endpoint required, nothing simulated presented as measured.
- Next steps: per-request EWMA updates online, repair-hint escalation
  briefing, deeper white-box signals (per-token logprobs) that only an
  open-weight stack can expose.
