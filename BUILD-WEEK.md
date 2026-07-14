# OpenAI Build Week ledger — K Top by Kaaval

Change ledger required by the Build Week plan: what existed before, what was
added during the submission period, with commits and evidence. Submission due
**Tuesday, July 21, 2026, 5:00 PM PT**. Free Codex credits must be requested
by **Friday, July 17, 12:00 PM PT**.

## Boundary

Everything at or before tag **`pre-build-week`** (commit `68d6616`, July 13,
2026) is prior work — the AMD ACT-II Track 3 submission: the assurance engine
(contracts, Layer-1 verifier, grounding rules, EWMA routing, fail-closed
pipeline, trajectory store, Layer-3 sampled display-only audit), the Flight
Deck, the container/GHCR release, and 372 passing tests.

Everything after that tag is Build Week work, logged here.

## Build Week changes

| Date | Commit / branch | What | Author context |
|---|---|---|---|
| Jul 13 | `1ebc24b` (this branch) | K Top quick-MVP: `kaaval top --demo` (content-free SAMPLE fixture), live `--endpoint` polling of redacted `/api/ops/snapshot`, receipt inspector, filtering, `--once`/JSON | Codex session |
| Jul 13 | `94b8680` (this branch) | Product roadmap + workspace migration docs committed | Codex session |
| Jul 13 | PR #12 (`task/sdk-tier0`) | Tier-0 SDK: `@kaaval.assure` decorator, shadow/enforce, `NoSafeAnswer`, 11 tests | Claude session |
| Jul 13 | `task/provider-neutral` (WIP) | Generic OpenAI-compatible remote provider (`KAAVAL_REMOTE_*` env config; factory wiring in progress) | Claude session |
| Jul 13 | this file | Ledger started; receipt-schema boundary frozen (below) | Claude session |

Codex `/feedback` session ID for the submission: _to be added at submission._

## Receipt schema boundary (frozen, Day 0)

Two layers, deliberately different, and the difference is the design:

1. **Raw evidence store (`TrajectoryStore`) — verbatim, local, operator-controlled.**
   Stores `task_input` and `raw_text` exactly as they occurred. This is what
   makes decisions *replayable* (re-verify any answer later) and it never
   leaves the operator's boundary. Unchanged during Build Week.
2. **Redacted receipt surface (`/api/ops/snapshot`, K Top, MCP tools) — content-free.**
   Everything shown to K Top, exported, or exposed through MCP carries only:
   contract id + version, outcome (`accepted` / `recovered` / `no_safe_answer`
   / `provider_error`), failed check IDs, attempt count and escalation lineage,
   provider/model identifiers, latency/tokens/cost, evidence source tags, and a
   NanoCanary evidence reference. **No prompt text, no response text, no
   credentials, no raw provider errors.**

Rule frozen for the week: anything crossing from layer 1 to layer 2 goes
through the redaction boundary in `ops.py`; MCP tools read layer 2 only. Tests
must prove no sensitive content reaches MCP or K Top output (Day 3/Day 5 gates).

## Acceptance gates (from the build plan)

- One-command credential-free demo (`kaaval top --demo`) works.
- One real GPT-5.6 path works through the OpenAI Responses wrapper.
- All four operational states demonstrated truthfully.
- K Top and MCP outputs contain no prompt, response, key, or raw provider error.
- Runtime failures are never scored as model behavior.
- The agent explains receipts; it never manufactures or alters verdicts.
- Unsupported provider capabilities fail explicitly.
- NanoCanary evidence labeled by scope and freshness.
- Fresh wheel installation works.
- Prior work vs Build Week work separated (this ledger + tag).
- Public claims match code and recorded evidence.
