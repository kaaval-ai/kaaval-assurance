# K Top OpenAI Hackathon Plan

Status: planned hackathon wedge, based on Milind's reported local MVP.

Evidence boundary: reported by Milind on 2026-07-13. Not yet verified in this
repo. Do not treat as durable Kaaval evidence until committed, pushed, and
reviewed against the engineering operating standard.

## Hackathon Thesis

K Top is the developer-facing flight recorder for Kaaval assurance.

It should show OpenAI and agent-app developers whether each AI call crossed a
safe acceptance boundary, recovered through escalation, produced no safe answer,
or failed at the provider/runtime layer.

The hackathon story is:

```text
Kaaval assurance pipeline
  -> trajectory receipts
  -> redacted operations schema
  -> K Top terminal view
```

K Top must not duplicate verifier, routing, or provider logic. It observes
redacted receipts produced by the assurance pipeline.

## MVP Scope

The hackathon MVP should optimize for one clean developer experience:

```bash
uv sync --group dev
uv run kaaval top --demo
```

Reported demo states:

- Contract-conformant locally.
- Failed locally, recovered through escalation.
- No safe answer.
- Provider or transport failure.

Reported live path:

```bash
KAAVAL_LIVE_RUNS_ENABLED=1 uv run uvicorn apps.api.server:app --port 8000
uv run kaaval top --endpoint http://127.0.0.1:8000
```

K Top should monitor only decisions produced through Kaaval's assurance API or
Flight Deck path. It does not automatically discover arbitrary model or agent
traffic.

## Product Boundary

K Top is the local developer-adoption wedge.

Kaaval Console is the enterprise system of record.

Do not claim the enterprise control plane is complete until these exist:

- Durable, tenant-aware decision history.
- Authentication and RBAC.
- SSE event streaming and reconnect cursors.
- Cross-worker aggregation.
- Retention and export policies.
- Alerts and nanoCanary evidence integration.
- Shared contracts and fleet-wide shadow/enforcement controls.

## Required Hackathon Signals

K Top should make these visible without leaking sensitive data:

- Contract and contract version.
- Local-to-remote execution path.
- Contract-conformant, recovered, no-safe-answer, and provider-error states.
- Failed verifier check IDs.
- Escalations and attempt counts.
- Recorded model-call latency, tokens, and cost.
- Per-category EWMA routing state.
- Receipt inspection, filtering, pause, refresh, and keyboard navigation.
- Explicit `LIVE`, `SAMPLE`, `UNAVAILABLE`, `ENFORCED`, and `DISPLAY ONLY`
  labels.

Must withhold:

- Prompts.
- Responses.
- Credentials.
- Exception bodies.
- Sensitive filesystem paths.
- Raw provider payloads.

## Verification Required Before Kaaval Evidence Promotion

Before this becomes a supported Kaaval build claim, capture:

- Commit hash and branch.
- Full test command and result showing the reported `390 passed`.
- Fresh wheel build command.
- Empty-environment install command.
- `kaaval` console command verification from the installed wheel.
- One saved redacted demo receipt or fixture.
- Terminal screenshot or short recording of `kaaval top --demo`.
- Exact live API-to-terminal verification command.
- Independent review source: human, agent, or tool-assisted.
- List of unrelated worktree changes preserved.

Until then, K Top is promising reported work, not durable evidence.

## Positioning Line

For the OpenAI hackathon:

> K Top is a content-free terminal flight recorder for agent assurance. It turns
> OpenAI app calls into redacted, replayable receipts so developers can see
> whether their AI system answered safely, recovered safely, refused safely, or
> failed at the provider layer.

## Non-Goals

- Do not claim arbitrary traffic discovery.
- Do not claim enterprise governance is complete.
- Do not claim benchmark-grade model reliability.
- Do not expose raw model content.
- Do not make K Top the source of verifier truth.
