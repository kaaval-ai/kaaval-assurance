# Prior work vs Build Week work — commit-backed

Required by the Build Week rules and the Kaaval Top brief (§15): every surface
mapped to commits and evidence, replacing the placeholder table. Boundary tag:
**`pre-build-week`** = commit `68d6616` (July 13, 2026 — final AMD ACT-II
submission asset commit). See `BUILD-WEEK.md` for the running change ledger.

## Phase-0 evidence gate — closed on this machine, 2026-07-14

The brief was authored from an environment without this repository and marked
several reported capabilities `planned` pending verification. Verified here:

| Reported claim | Status now | Evidence |
|---|---|---|
| Test suite passes | **measured** — 390 passed | `uv run pytest -q` on `build-week/day0-baseline` (2026-07-14) |
| Credential-free demo | **measured** | `uv run kaaval top --demo --once` output captured: `docs/evidence/ktop-demo-once-2026-07-14.txt` |
| Four truthful outcomes in demo | **measured** | Same capture: CONFORMANT, RECOVERED, NO SAFE, PROVIDER ERROR rows |
| Redacted ops schema + JSON | **measured** | `docs/evidence/ktop-demo-snapshot-2026-07-14.json` (schema_version 0.1) |
| Redaction (no prompts/responses/keys) | **measured** | Sentinel grep: only `prompt_tokens` field-name hits; deep scan found zero free-text values |
| Wheel build | **measured** | `uv build` → `dist/kaaval_assurance-0.1.0-py3-none-any.whl` |
| Empty-environment install + console command | **measured** | Fresh venv → `pip install dist/*.whl` → `kaaval top --demo --once` exit 0 |
| Live API→terminal path | **measured** | Running server answered `GET /api/ops/snapshot` with `provenance:"live"` redacted JSON |
| EWMA route-adjustment loop implemented (not design-only) | **measured** | `src/kaaval_assurance/router.py` + `routing_policy.py` (pre-existing, tested); demo header shows `refund_decision 0.51 FORCE_REMOTE` |

One correction to the brief's assumption set: the implemented EWMA loop routes
between **tiers** (local → remote) with tighten/force bands over verifier
outcomes. The brief's Phase-4 "primary → recovery *profile*" transition is a
**new** concept on top of that machinery and is submission-period work.

## Surface table (commit-backed)

| Surface | Prior work (≤ `pre-build-week`) | Submission-period extension |
|---|---|---|
| Contract verifier + grounding rules | Pre-existing (`src/kaaval_assurance/verifier.py`, `contracts/`; 5 grounding rules) | Refund/OpenAI fixtures as needed |
| Provider interface + factory | Pre-existing (`providers/`: mock, ollama, vllm, fireworks) | `openai_compatible` remote provider WIP (`task/provider-neutral`); **OpenAIResponsesProvider** to come (Phase 1) |
| Recovery / NoSafeAnswer / fail-closed | Pre-existing (`pipeline.py` `_attempt`, typed `no_safe_answer`; `tests/test_fail_closed.py`) | Exercised through the OpenAI path (Phase 1) |
| Trajectory receipts | Pre-existing (`trajectory.py`, verbatim local store) | +40 lines during Build Week (commit `1ebc24b`): ops-projection support; KPI evidence fields to come (Phase 2) |
| EWMA routing (tier-level) | Pre-existing (`router.py`, `routing_policy.py`) | Profile-level route transitions + route-decision receipts (Phase 4) |
| K Top TUI + ops projection | **Build Week** — commit `1ebc24b` (2026-07-13): `cli.py`, `top.py`, `ops.py`, 3 test files | KPI-first redesign (Phase 3) |
| STR / CC-STR / NDR projection | Does not exist | Phase 2 (new) |
| Tier-0 SDK (`@assure`) | **Build Week** — PR #12 (2026-07-13) | — |
| Improvement agent / MCP server / Strands / NanoCanary integration | Do not exist in this repo | **Excluded from critical path** per brief §16 |
| Flight Deck, container, AMD evidence bundle | Pre-existing (AMD ACT-II submission) | Untouched |

## Commits after 2026-07-13 09:00 PT (submission period)

- `1ebc24b` — K Top quick-MVP (Codex-authored slice, committed with timestamps)
- `94b8680` — roadmap + workspace-migration docs
- (this branch) — Build Week ledger, frozen redaction boundary, briefs, this file
- `task/sdk-tier0` / PR #12 — Tier-0 SDK
- `task/provider-neutral` — `openai_compatible` provider WIP

Codex `/feedback` session ID: _added at submission (Phase 5)._
