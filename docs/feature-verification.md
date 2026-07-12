# Feature Verification Matrix

Every claimed capability, its code location, and how it was verified against
the running instance (localhost:8000, restarted from commit `8ff3c9b`) or the
committed evidence. Verified 2026-07-12. This is the source of truth for what
the deck and video may claim.

Legend: **[LIVE]** exercised against the running API · **[TEST]** covered by
the passing suite (361 tests) · **[ARTIFACT]** committed evidence file ·
**[CODE]** read directly in source.

---

## Layer 1 — deterministic contract verification

| Claim | Code | Evidence |
|---|---|---|
| Deterministic checks: JSON parse, required fields, enums, numeric ranges, min-items | `src/kaaval_assurance/verifier.py` | **[LIVE]** happy-path run returned `checks_run: 9`, `contract_conformant: true` |
| Grounding rules (content-aware, string-matched, no LLM) | `src/kaaval_assurance/contracts/base.py` (`GroundingRule`) | **[CODE]** 5 rules registered: `regional_outage_requires_p1`, `no_redundancy_requires_immediate`, `outside_refund_window_requires_denial`, `consequential_damages_requires_human`, `missing_purchase_evidence_requires_human` |
| The `$500` refund cap is a range check, not a prompt | `src/kaaval_assurance/contracts/support.py` (`refund_amount_usd` FieldSpec `max_value=500`) | **[LIVE]** double-failure run failed with `range:refund_amount_usd` |
| No model judges another model inline | `verifier.py` (pure code, zero provider calls) | **[CODE]** verifier imports no provider |

## Contracts registry

| Claim | Code | Evidence |
|---|---|---|
| 6 contracts across 2 domains (telecom + support), versioned | `src/kaaval_assurance/contracts/__init__.py` | **[CODE]** `ALL_CONTRACTS` = telecom (4) + support (2); `get_contract` resolves latest version |

## Layer 2 — EWMA drift + adaptive routing

| Claim | Code | Evidence |
|---|---|---|
| Per-category EWMA drift over verifier outcomes (alpha 0.3) | `src/kaaval_assurance/router.py`, `routing_policy.py` | **[LIVE]** eval CLI prints per-category EWMA; **[TEST]** `test_online_routing`, `test_router` |
| Deterministic policy maps drift bands → routing (tighten / pre-route remote) | `routing_policy.py` | **[TEST]** covered; **[CODE]** bands at 0.20 / 0.50 |
| Remote outcomes never feed local drift | `router.py` `record_signal` | **[TEST]** `test_remote_failure_never_feeds_local_drift` |
| Forced-remote recovery gap is honestly documented, not silently broken | `README.md` Limitations | **[CODE]** stated: recovery = session reset / 15-min expiry; half-open probes are roadmap |

## Fail-closed boundary

| Claim | Code | Evidence |
|---|---|---|
| Provider transport errors are recorded, routed, typed — never escaped exceptions | `src/kaaval_assurance/pipeline.py` `_attempt` | **[TEST]** `test_fail_closed.py` (local outage, remote outage, total outage) |
| Double failure returns `no_safe_answer`, unsafe output withheld | `pipeline.py`, `apps/api/server.py` | **[LIVE]** double-failure run returned `status: no_safe_answer`, `answer: null`, `unverified_output_withheld: true` |
| Transport failures feed drift like verification failures (deliberate) | `pipeline.py` | **[TEST]** `test_local_outage_feeds_drift_like_a_failure` |

## Layer 3 — sampled offline audit

| Claim | Code | Evidence |
|---|---|---|
| Sampled (default 10%), offline, never gates the live response | `src/kaaval_assurance/audit/runner.py` | **[LIVE]** audit CLI: "display only, no routing input" |
| FP calibration gate: over-eager critic → untrusted | `audit/calibration.py` | **[TEST]** `test_overflagging_challenger_fails_calibration` |
| Zero-gold calibration never reads "passed" | `audit/calibration.py` (`total > 0` guard) | **[TEST]** `test_zero_gold_cases_never_pass_calibration` |
| Zero-sample audit never reads "trusted" | `audit/runner.py` (`len(results) > 0`) | **[TEST]** `test_zero_sampled_answers_are_never_trusted` |
| Honest scope: display-only; two-sided calibration + audit-to-routing are roadmap | telemetry `routing_integration="display_only"`; README | **[LIVE]** CLI states it; **[CODE]** confirmed no routing coupling (grep) |

## Multi-step agent workflow

| Claim | Code | Evidence |
|---|---|---|
| 4 chained contract-gated steps; each verified finding feeds the next | `src/kaaval_assurance/agent.py` `run_agent_workflow` | **[LIVE]** `/api/agent-runs` returned `status: completed`, 4 steps each `accepted` |
| `no_safe_answer` step halts the chain (no downstream on unverified finding) | `agent.py` | **[TEST]** `test_agent.py::TestHonestHardStop` |
| CLI + HTTP surfaces | `agent_cli.py`, `apps/api/server.py:584` | **[LIVE]** endpoint exercised; **[TEST]** `test_cli_runs_complete_mock_workflow` |
| Scope honesty: contract-gated workflow, NOT autonomous planning / tool execution | `README.md` | **[CODE]** stated explicitly |

## Trajectory store

| Claim | Code | Evidence |
|---|---|---|
| Every attempt stored verbatim as a replayable row (provider, model, cost, tokens, latency, checks, routing reason) | `src/kaaval_assurance/trajectory.py` | **[TEST]** `test_trajectory`; **[ARTIFACT]** `artifacts/demo-live-trajectory.json` |

## Telemetry truth layer + runtime probe

| Claim | Code | Evidence |
|---|---|---|
| Every judge-facing claim maps to a stored field with a source tag | `src/kaaval_assurance/telemetry.py` | **[LIVE]** `/api/dashboard` claims each carry `measured`/`configured`/`not_available` |
| Runtime probe turns configured → measured; redacts secrets | `src/kaaval_assurance/runtime_probe.py` | **[ARTIFACT]** `artifacts/runtime-probe.json` (gfx1100, vLLM, served model) |
| "Verified" renamed to Layer-1 contract-conformance everywhere judge-facing | telemetry, eval CLI, README, Flight Deck | **[LIVE]** dashboard + CLI use conformance wording |

## Evaluation runner

| Claim | Code | Evidence |
|---|---|---|
| Reports Layer-1 conformance AND gold critical-field accuracy separately | `src/kaaval_assurance/eval/runner.py`, `cli.py` | **[LIVE]** CLI: "conformance 100.0% … gold critical-field accuracy 12.5% (2/16) \| false accepts 14 (87.5%)" |
| The honest gap: conformance ≠ semantic correctness, stated in the number itself | `cli.py` | **[LIVE]** CLI annotates "(deterministic contract checks, not semantic correctness)" |

## API + operator gates + sessions

| Claim | Code | Evidence |
|---|---|---|
| Endpoints: health, capabilities, runtime-connections, dashboard, telemetry, trajectory, runtime-probe, live-sessions reset, runs, agent-runs | `apps/api/server.py` | **[LIVE]** health/runs/agent-runs/dashboard exercised |
| Paid remote requires server env (client `confirm_spend` is acknowledgment, not authorization) | `server.py` `paid_remote_allowed` | **[TEST]** `test_server_gates.py::TestPaidRemoteGate` |
| Artifact export requires server env; live exports isolated from curated bundle | `server.py` `artifact_export_allowed` + `export_root` | **[TEST]** `test_authorized_exports_cannot_clobber_curated_evidence` |
| BYOK: keys stay in backend memory, ephemeral (15-min), never in storage/logs/telemetry | `server.py` `SessionManager`, `runtime-connections` | **[CODE]** session TTL 900s; **[TEST]** `test_api_server` session suite |
| Health surfaces all operator capabilities | `server.py` `/api/health` | **[LIVE]** returns `paid_remote_allowed`, `artifact_export_allowed`, `diagnostic_raw_allowed`, `byok_allowed`, `custom_endpoints_allowed` |

## Flight Deck (React)

| Claim | Code | Evidence |
|---|---|---|
| Two modes: Evidence Baseline (immutable, no creds) + Live Session (BYOK / Ollama / vLLM) | `apps/flight-deck/src/` | **[LIVE]** verified in browser this session; **[TEST]** `test_flightdeck_hygiene.py` |
| Progressive disclosure; AMD story front-and-center; guardrail-vs-assurance distinction | `ProofStrip.tsx`, `SummaryDashboard.tsx` | **[LIVE]** rendered + screenshotted this session |

## Delivery

| Claim | Code | Evidence |
|---|---|---|
| One public container, linux/amd64, clean-smoke verified, non-root UID 10001 | `Dockerfile`, `scripts/container_smoke.sh` | **[LIVE]** container smoke passed this session (health, fail-closed, agent, gates closed, non-root) |
| Published to GHCR at pinned digest | `ghcr.io/kaaval-ai/kaaval-assurance:act-ii` | **[LIVE]** `docker manifest inspect` — amd64 present |
| Hugging Face Space deploy files, gates closed by default | `deploy/huggingface/Dockerfile` (pinned digest, PORT 7860, BYOK on, paid/export/diagnostic closed) | **[CODE]** confirmed |
| GitHub Release | tag `act-ii-submission` | **[LIVE]** `gh release view` — published |

## Cost comparison (economics)

| Claim | Code | Evidence |
|---|---|---|
| Local-first vs always-remote: 14/16 remote calls avoided (87.5%), $0.0333 configured cost avoided (88.7%) | `scripts/write_fireworks_comparison.sh`, artifact | **[LIVE]** `/api/dashboard` `remote_calls_avoided: 14`; **[ARTIFACT]** `fireworks-cost-comparison-*.json` |
| Cost is a CONFIGURED price estimate from token counts, not a MEASURED invoice — tagged as such | telemetry source tags | **[LIVE]** dashboard tags cost `configured`, conformance `measured` |

---

## The three claims we deliberately do NOT make

1. Schema conformance proves semantic correctness. (It does not — the eval's own 12.5% gold accuracy vs 100% conformance is the honest gap, shown in the same output.)
2. Layer 3 audit currently gates or routes. (Display-only; roadmap.)
3. Autonomous agentic planning / arbitrary tool use. (The workflow is contract-gated multi-step, nothing more.)
