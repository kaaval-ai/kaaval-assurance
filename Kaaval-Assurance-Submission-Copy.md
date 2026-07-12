# Kaaval Assurance — Paste-Ready Submission Copy

## Title (max 50 characters)

Kaaval Assurance: Verify, Don’t Predict

## Short description (max 255 characters)

Kaaval Assurance runs Gemma locally on AMD ROCm/vLLM, checks each AI decision against deterministic task contracts, escalates failures to Fireworks, and stores source-tagged receipts for routing, cost, latency, and acceptance.

## Long description

Kaaval Assurance is a provider-neutral assurance gateway for consequential AI
decisions. It runs an open-weight primary tier first, checks every response
against an explicit deterministic task contract, escalates only when the
contract fails or routing policy changes, and stores each attempt as a
replayable receipt.

The submitted build demonstrates Gemma 3 1B served through ROCm and vLLM on a
measured AMD host. Its committed evidence bundle records the runtime probe,
model identity, contract outcomes, latency, tokens, routing, and source tags.
A separate captured Fireworks comparison demonstrates selective escalation
economics without presenting that comparison as the AMD run.

The Flight Deck has two modes. Evidence Baseline loads the immutable measured
bundle without credentials. Live Session connects Fireworks BYOK, local
Ollama/vLLM, or an operator-approved OpenAI-compatible endpoint. Credentials
remain ephemeral, paid execution requires explicit confirmation, and a double
failure returns NO SAFE ANSWER with the rejected payload withheld.

Kaaval does not claim that schema conformance proves semantic correctness.
Layer 1 enforces deterministic contracts, Layer 2 tracks exponentially
weighted contract-failure drift, and Layer 3 is a sampled, FP-calibrated,
display-only audit signal. The product path begins in shadow mode and advances
to enforcement only after contracts, false-accept/reject rates, and operational
economics are validated with design partners.

## Technologies

AMD GPU, ROCm, vLLM, Gemma 3, Fireworks AI, FastAPI, React, TypeScript,
SQLite, Docker/Finch, Pydantic, GHCR

## Additional information

Kaaval Assurance is the reusable assurance engine within the broader KaavalAI
Agentic Guardian direction. The near-term commercial wedge is a self-hostable,
provider-neutral gateway that observes consequential decisions in shadow mode,
produces contract and cost receipts, and later gates actions after customer
validation. BYOK keeps model credentials and spend under the operator’s
control. The next validation phase adds blind semantic benchmarks, two-sided
Layer 3 calibration, end-to-end TCO measurement, durable recovery, and two
design partners running shadow traffic.

## Links

- Repository: https://github.com/kaaval-ai/kaaval-assurance
- Release: https://github.com/kaaval-ai/kaaval-assurance/releases/tag/act-ii-submission
- Container: ghcr.io/kaaval-ai/kaaval-assurance:act-ii
- Immutable tag: ghcr.io/kaaval-ai/kaaval-assurance:sha-a8c95e42c10b
- Hosted demo: ADD AFTER AZURE OR AWS DEPLOYMENT

