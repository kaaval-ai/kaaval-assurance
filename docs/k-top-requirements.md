# K Top v0.1 product requirements and architecture

**Status:** first requirements draft plus runnable quick-MVP checkpoint

**Date:** July 13, 2026

**Product name:** K Top

**Command:** `kaaval top`

**Owner:** Kaaval Platform

**Runtime authority:** Kaaval Assurance

### July 13 quick-MVP checkpoint

This repository now contains a deliberately smaller implementation slice than
the complete v0.1 specified below:

- `kaaval top --demo` renders a deterministic, content-free `SAMPLE` fixture
  with `DISPLAY ONLY` authority; it never claims the fixture affected a runtime;
- `kaaval top --endpoint http://127.0.0.1:8000` polls a real redacted
  `/api/ops/snapshot` built from current process-local live-session stores;
- the first screen, decision selection, redacted receipt inspector, filtering,
  pause/resume, help, plain-text `--once`, and JSON output are runnable;
- terminal rendering uses the Python standard library for this dependency-free
  validation slice; Textual remains the target for the complete interactive
  v0.1 described in section 11;
- the adapter is bounded and process-local. It has no durable history, SSE,
  reconnect cursor, authentication, tenant isolation, or cross-worker view.
- each active session contributes at most 100 complete recent decisions to a
  poll. Truncated windows are explicit, calls-per-minute becomes unavailable,
  and the latency field is labeled as the recorded model-call latency sum rather
  than end-to-end request duration.

The demo fixture validates information design, not the engine. Live attach is
the proof that K Top reads real Assurance receipts. The quick MVP is not the
complete v0.1 and must not be presented as satisfying the SSE, persistence,
NanoCanary, export, or enterprise acceptance criteria in section 14.

## 1. Decision

K Top is feasible and is a strong developer entry point for Kaaval, provided it
is built as a terminal client for the same decision and receipt protocol used by
the web console. It must not become a second assurance engine or a generic LLM
token monitor.

The v0.1 promise is deliberately narrow:

> Watch consequential model decisions as they happen, see which contract was
> applied, understand why Kaaval allowed, escalated, or stopped the result, and
> inspect the receipt without leaving the terminal.

K Top is the product name in prose. `kaaval top` is the canonical command. A
single-letter `k` executable is not part of v0.1 because it is collision-prone
and would create a second command namespace.

## 2. Product boundary

K Top is:

- a local-first, read-only terminal operations surface;
- a thin client over versioned Kaaval HTTP and event APIs;
- useful without an account, network connection, model credential, or cloud
  control plane in demo/local mode;
- a developer path into the same contracts, decisions, receipts, evidence, and
  authority model used by Kaaval Platform;
- usable against local, self-hosted, and future managed Kaaval runtimes.

K Top is not:

- a model or agent orchestrator;
- a replacement for `top`, `btop`, GPU monitors, or an LLM trace viewer;
- a terminal implementation of verification, routing, or evidence policy;
- a place to turn production enforcement on with a keystroke;
- a direct reader of Kaaval's private SQLite schema;
- proof that a contract-conformant response is semantically correct;
- a reason to put every Kaaval research module into the live request path.

The unit shown by K Top is an **assured decision**, not a raw model call. One
decision may contain multiple model attempts, an escalation, or a terminal
`no_safe_answer` outcome.

## 3. Target users and jobs

### Primary: individual model or agent developer

When developing or debugging a model-backed application, I want to see which
calls are consequential and whether they met an explicit contract, so I can
find unsafe integration behavior before I add an enterprise dashboard.

Key jobs:

- see the first assured decision within five minutes of installation;
- distinguish assured decisions from calls with no contract;
- inspect stable failed check IDs and the attempted recovery path;
- understand provider/model, latency, token, and configured-cost impact;
- reproduce or export a receipt for a bug report without searching logs.

### Secondary: platform and applied-AI engineer

When operating a shared model runtime, I want a continuously updating terminal
view of contract outcomes and failure patterns, so I can diagnose a deployment
without opening a browser or receiving raw customer content by default.

Key jobs:

- filter by environment, contract, model, outcome, and failure ID;
- identify spikes in provider errors, contract failures, escalations, or
  `no_safe_answer` results;
- inspect EWMA as a plainly labeled trend over verifier failures;
- see whether model evidence is current, stale, partial, or unavailable;
- connect the same CLI to a local runtime and an enterprise environment.

### Enterprise beneficiary, not v0.1 primary user

Risk, audit, support operations, and policy owners consume shared receipts,
review queues, approvals, retention, and exports in Kaaval Console. K Top may
display their outcomes later, but it does not replace those collaborative
workflows in v0.1.

## 4. First-run experience

### 4.1 Showcase mode

The first shippable experience must be fully local and deterministic after the
package has been installed:

```bash
uv run kaaval top --demo
```

Expected behavior:

1. Start or connect to a temporary local Kaaval demo runtime.
2. Run a bounded repeating scenario through the existing mock providers and
   `AssurancePipeline`.
3. Display at least one locally accepted decision, one escalation and rescue,
   and one `no_safe_answer` or provider-error decision.
4. Store receipts in a temporary directory and delete them on exit unless
   `--keep-demo-receipts` is set.
5. Require no credentials and make no provider or cloud-service network calls.

`--demo` proves the product journey. It is not represented as customer traffic,
live model performance, or measured infrastructure evidence.

### 4.2 Attach mode

The real developer experience is:

```bash
kaaval top --endpoint http://127.0.0.1:8000
```

The TUI connects to a Kaaval runtime, retrieves a bounded history, then follows
the decision event stream. It does not inspect the application's process,
monkey-patch provider SDKs, or tail arbitrary logs.

Configuration precedence:

1. command flags;
2. environment variables such as `KAAVAL_ENDPOINT` and `KAAVAL_API_KEY`;
3. the selected profile in `~/.config/kaaval/config.toml`;
4. local endpoint default `http://127.0.0.1:8000`.

Secrets must be accepted through environment variables, OS credential storage,
or a hidden prompt. They must never be accepted as a visible command-line
argument, printed in diagnostics, stored in receipts, or included in exports.

### 4.3 What is usable in the repository today

From the Kaaval Assurance repository, run the offline terminal mock-up:

```bash
uv sync --group dev
uv run kaaval top --demo
uv run kaaval top --demo --once --width 120
```

For a real local attach, start Assurance:

```bash
uv sync --group dev
KAAVAL_LIVE_RUNS_ENABLED=1 uv run uvicorn apps.api.server:app --port 8000
```

In another terminal, a mock decision can be submitted without credentials:

```bash
curl -s -X POST http://127.0.0.1:8000/api/runs \
  -H 'Content-Type: application/json' \
  -d '{
    "task_input": "Customer was charged twice for a $120 order.",
    "contract_id": "support.refund_decision",
    "local_provider": "mock",
    "remote_provider": "mock"
  }'
```

The existing API response already contains the decision status, check results,
attempt trajectory, routing reason, session EWMA, runtime profile, and telemetry
needed for the prototype. The new experimental `/api/ops/snapshot` exposes a
bounded content-free view over real live sessions, so the current terminal can
poll it:

```bash
uv run kaaval top --endpoint http://127.0.0.1:8000
```

This proves live attach but not production streaming. Continuous attach with
durable history, cursor recovery, and at-least-once delivery still needs the
versioned v0.1 API and SSE protocol in section 9.

## 5. Command UX

### Required in v0.1

```text
kaaval top [--endpoint URL] [--profile NAME] [--demo]
           [--environment NAME] [--contract ID] [--model ID]
           [--outcome OUTCOME] [--refresh SECONDS]
           [--no-raw-content] [--keep-demo-receipts]

kaaval status [--endpoint URL]
kaaval inspect DECISION_ID [--json]
kaaval export DECISION_ID [--output PATH] [--redacted]
kaaval doctor
```

Rules:

- `--no-raw-content` is the default and exists as an explicit documentation
  cue; raw content requires both runtime authorization and an affirmative
  local configuration outside v0.1 demo defaults.
- `kaaval inspect` and `kaaval export` use the same API models as the TUI.
- `kaaval doctor` reports endpoint reachability, API compatibility, terminal
  capabilities, active profile, and redaction policy without revealing secrets.
- unsupported API versions fail with a clear upgrade/downgrade instruction.
- commands support stable JSON output where automation is plausible; the TUI
  itself is an interactive human surface.

### Deferred command ideas

The following may appear in the wider CLI but are not K Top v0.1 dependencies:

```text
kaaval init
kaaval serve
kaaval proxy
kaaval contracts validate|test|promote
kaaval models qualify|compare
kaaval replay
kaaval login
```

`kaaval replay` is deferred because replay can spend money, repeat model calls,
or duplicate a consequential action. The v0.1 TUI may copy a safe replay
command, but it must not execute replay from a single keypress.

## 6. TUI information architecture

### 6.1 Global header

Always visible:

- product and version;
- endpoint profile and environment;
- connection state: `LIVE`, `RECONNECTING`, `OFFLINE`, or `DEMO`;
- execution mode from the runtime: `SHADOW`, `ENFORCE`, or `MIXED`;
- provenance for the current dataset: `LIVE`, `CAPTURED`, `SAMPLE`, or
  `UNAVAILABLE`;
- redaction state.

Never infer mode from outcome rows. If the runtime cannot report it, display
`MODE UNAVAILABLE`.

### 6.2 Overview/live feed

The default screen contains:

- calls per minute;
- final contract-conformance rate;
- escalation rate;
- `no_safe_answer` count;
- provider-error count;
- p95 end-to-end latency;
- observed or configured cost, with the provenance visible;
- a scrollable decision table.

Decision table columns at 120 columns or wider:

```text
TIME      DECISION      CONTRACT              MODEL          PATH   OUTCOME       LATENCY
10:42:08  01JQ…         support.refund.v1     llama-3.2      L>R    NO_SAFE        391ms
10:42:07  01JP…         support.refund.v1     gpt-4.1-mini   R      CONFORMANT     212ms
10:42:06  01JN…         unassigned            gemma-3        L      UNASSURED       73ms
10:42:04  01JM…         support.triage.v2     llama-3.2      L>R    RECOVERED      108ms
```

Outcome vocabulary:

- `CONFORMANT`: the final attempt passed deterministic contract checks;
- `RECOVERED`: an earlier attempt failed and a later attempt passed;
- `NO_SAFE`: all configured attempts failed or no accepted response exists;
- `PROVIDER_ERROR`: the terminal attempt failed at the provider boundary;
- `UNASSURED`: the observed call has no Kaaval contract;
- `SHADOW_FAIL`: shadow evaluation failed but Kaaval did not alter delivery;
- `UNKNOWN`: the runtime record is incomplete or from an unsupported producer.

`UNASSURED` is rendered only when an SDK/proxy adapter explicitly reports an
observed call with no contract. The current `/api/runs` endpoint requires a
contract and cannot produce this state; K Top must not synthesize it.

The UI must never use `correct`, `safe`, `trusted`, or `verified` as synonyms
for contract conformance.

### 6.3 Decision inspector

Pressing `Enter` opens an inspector for the selected decision:

```text
 K TOP / DECISION 01JQ…                                      ENFORCED | LIVE

 Final outcome    NO_SAFE_ANSWER          Duration       391 ms
 Contract         support.refund.v1       Contract ver   1.0
 Contract hash    unavailable             Environment    local

 ATTEMPT 1  local / llama-3.2                     91 ms   REJECTED
   failed  range:refund_amount_usd
   route   Layer-1 failure triggered configured escalation

 ATTEMPT 2  remote / gpt-4.1-mini                300 ms   REJECTED
   failed  grounding:consequential_damages_requires_human

 RECEIPT
   provider/model recorded       yes
   contract version recorded     yes
   raw content                   withheld
   replay support                not available
```

The inspector shows:

- final disposition and whether it affected delivery;
- contract ID, version, and hash when available;
- attempt timeline in stored order;
- exact stable check IDs;
- routing reason and escalation state;
- provider/model identity, tokens, latency, configured/measured cost;
- audit result with `DISPLAY ONLY` authority when present;
- receipt completeness and redaction status;
- NanoCanary evidence summary when the model join key matches.

Missing fields must say `unavailable`; they must not be derived from nearby
rows, captured artifacts, environment assumptions, or marketing copy.

### 6.4 Contracts view

Read-only in v0.1:

- contract ID, version, category, and description;
- deterministic field checks and grounding-rule IDs;
- observed decision volume and recent failure counts;
- lifecycle state only when the server supplies it;
- warning that the current built-in contract registry is static Python and
  does not yet provide externally managed draft/shadow/enforced lifecycle.

### 6.5 Models and evidence view

The view combines serving identity with explicitly advisory evidence:

- provider, exact model ID, endpoint identity, and runtime profile;
- NanoCanary evidence ID, observation time, probe coverage, validation tier,
  caveats, effective advisory actions, and downgrade reasons;
- evidence states: `CURRENT`, `STALE`, `PARTIAL`, `RETEST REQUIRED`, or
  `UNAVAILABLE`;
- runtime/configured/measured provenance displayed independently.

The `BehavioralEvidenceRecord.evaluate()` result may authorize display of
`retest_required`, `shadow_only`, or `drift_alert`. It may not mark a live
decision conformant, bypass a contract, or silently route a model.

### 6.6 Trends view

The view contains:

- failure EWMA by contract category;
- conformance, escalation, provider-error, and `no_safe_answer` rates;
- top failed check IDs;
- latency and configured/measured cost trends;
- audit sampling and calibration status.

The label must read **Verifier failure EWMA**, with a one-line explanation:

> Recent local contract failures weighted more heavily than older failures;
> higher means the category is failing more often. It is not model accuracy.

If the active runtime uses EWMA to alter routing, that policy action and reason
must appear beside the trend. Layer 3 remains `DISPLAY ONLY` until a separate
validated integration changes that contract.

### 6.7 Help/status view

Show keyboard controls, endpoint/API version, reconnect status, data age,
redaction policy, terminal limitations, and links to local documentation. Do
not place roadmap-only modules in the operational navigation.

## 7. Keyboard behavior

Required:

| Key | Action |
|---|---|
| `j` / `k` or arrows | Move selection |
| `Enter` | Inspect selected decision |
| `Esc` | Return to previous view |
| `/` | Filter decisions |
| `1` | Overview/live feed |
| `2` | Contracts |
| `3` | Models and evidence |
| `4` | Trends |
| `e` | Export a redacted receipt after confirmation |
| `c` | Copy decision ID or safe inspect command |
| `p` | Pause/resume viewport updates without pausing collection |
| `?` | Help |
| `q` | Quit; confirm only when a local demo runtime would also stop |

No v0.1 key may change enforcement mode, promote a contract/model, retry a
paid call, approve a human-review item, or expose raw content.

## 8. Truth and authority labels

K Top must separate three concepts that are easy to conflate.

### Provenance: where did the displayed data come from?

- `LIVE`
- `CAPTURED`
- `SAMPLE`
- `UNAVAILABLE`

### Authority: what is this signal allowed to do?

- `ENFORCED`: affected the runtime disposition under the named contract;
- `SHADOW`: evaluated and receipted but did not alter delivery;
- `ADVISORY`: may inform a human or policy author;
- `DISPLAY ONLY`: telemetry/audit with no control authority.

### Outcome: what happened?

- `CONFORMANT`
- `REJECTED`
- `RECOVERED`
- `NO_SAFE_ANSWER`
- `PROVIDER_ERROR`
- `UNASSURED`
- `UNKNOWN`

One badge must never substitute for another. For example, a `LIVE` NanoCanary
record remains `ADVISORY`, and a `CAPTURED` decision may accurately report an
historical `ENFORCED` outcome.

## 9. Integration protocol

### 9.1 Ownership

- Kaaval Assurance owns verification, routing, attempt persistence, and final
  runtime disposition.
- Kaaval Platform owns cross-product evidence semantics, profiles, the K Top
  client, and the future web console.
- NanoCanary owns probe execution, scoring, criteria, and evidence provenance.
- K Top owns presentation and local user interaction only.

K Top must not import verifier, router, or provider implementations. It consumes
versioned public records.

### 9.2 Required v0.1 HTTP API

The current `/api/*` Flight Deck endpoints are a useful adapter but are not a
stable product protocol. Add a versioned surface:

```text
GET /v1/status
GET /v1/decisions?after_cursor=&limit=&contract=&model=&outcome=
GET /v1/decisions/{decision_id}
GET /v1/decisions/{decision_id}/receipt
GET /v1/metrics?window=5m
GET /v1/contracts
GET /v1/models
GET /v1/models/{model_identity}/evidence
GET /v1/events?after_cursor=          # Server-Sent Events
```

Server-Sent Events are sufficient for v0.1: the stream is server-to-client,
works over ordinary HTTP, and permits cursor-based reconnect. WebSockets are
not required.

Every response includes `schema_version`; `/v1/status` additionally includes
`api_version`, `runtime_version`, `execution_mode`, `environment`, and privacy
capabilities.

### 9.3 Decision event envelope

The minimum completed-decision event is:

```json
{
  "schema_version": "1.0",
  "event_id": "immutable-event-id",
  "cursor": "monotonic-opaque-cursor",
  "event_type": "decision.completed",
  "emitted_at": "RFC-3339 timestamp",
  "provenance": "live",
  "authority": "enforced",
  "decision": {
    "decision_id": "immutable-decision-id",
    "environment": "local",
    "mode": "enforce",
    "contract": {
      "id": "support.refund_decision",
      "version": "1.0",
      "hash": null
    },
    "final_outcome": "no_safe_answer",
    "attempts": [
      {
        "ordinal": 1,
        "provider": "mock-local",
        "model_id": "mock-local-v1",
        "tier": "local",
        "attempt_status": "completed",
        "contract_conformant": false,
        "failed_check_ids": ["range:refund_amount_usd"],
        "latency_ms": 12.4,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "cost_usd": 0.0,
        "cost_source": "configured"
      }
    ],
    "routing": {
      "escalated": false,
      "reason": "no escalation provider configured"
    },
    "content": {
      "input_available": false,
      "output_available": false,
      "redaction": "withheld"
    },
    "receipt": {
      "receipt_id": "immutable-receipt-id",
      "complete": true
    }
  }
}
```

Unknown fields are ignored. Unknown major schema versions are rejected. Missing
required identity, authority, or outcome fields produce an `UNKNOWN` row with a
visible compatibility error rather than a guessed display.

### 9.4 Delivery semantics

- Persist a completed decision before publishing `decision.completed`.
- Cursors are opaque, monotonic within one environment, and resumable.
- Events are at-least-once; clients deduplicate by `event_id`.
- On reconnect, K Top requests history after the last committed cursor.
- The TUI holds a bounded in-memory window, default 1,000 decisions.
- API pagination, not the TUI process, owns unbounded history.
- Client clock is never used to reorder server events with equal or missing
  timestamps.

### 9.5 Privacy defaults

- Summary and event endpoints exclude task input and raw model output.
- The receipt endpoint returns redacted content by default.
- Raw content requires server authorization and a separate explicit request.
- Provider exception bodies remain sanitized.
- API keys, provider credentials, full endpoint query strings, and local file
  paths never appear in events.
- Demo receipts are labeled `SAMPLE` and isolated from customer receipt stores.

## 10. Current capability reuse

| Current capability | Source | K Top use | Gap before v0.1 |
|---|---|---|---|
| Deterministic check results and stable failure IDs | `verifier.py` | Decision outcome and inspector | None for built-in contracts |
| Fail-closed model-call path | `pipeline.py` | Accepted, recovered, provider-error, and no-safe states | Add explicit runtime mode/authority |
| Per-attempt receipts | `models.py`, `trajectory.py` | Attempt timeline and decision details | Add decision/receipt IDs, privacy mode, contract hash, cursor, and incremental queries |
| Provider/model/runtime identity | `models.py`, runtime providers, `/api/capabilities` | Models view and row identity | Normalize immutable model/deployment identity |
| EWMA and routing policy | `router.py`, `metrics.py`, `routing_policy.py` | Trends and route explanation | Persist/serve time-windowed state; label as verifier failure EWMA |
| Telemetry truth layer | `telemetry.py` | Summary metrics and source labels | Provide live incremental metrics outside eval-report assembly |
| Layer 3 audit | `audit/*`, trajectory audit fields | Display-only audit detail | No authority change; two-sided calibration remains future work |
| Captured/sample provenance | `apps/api/artifacts.py`, Flight Deck types | Honest demo/captured labels | Move provenance into versioned records |
| Runtime connections and operator gates | `apps/api/runtime_connections.py`, `server.py` | Endpoint status and runtime identity | Product authentication and stable `/v1` API |
| Platform behavioral evidence validation | `kaaval-platform/src/kaaval_platform/evidence.py` | Models/evidence view | Expose records through an API; maintain advisory authority |
| Flight Deck TypeScript types | `apps/flight-deck/src/types.ts` | Input for shared schema design | Generate clients from public schema rather than copy types by hand |
| Tier-0 decorator PR | `task/sdk-tier0` | Potential future source of local decisions | Do not depend on it until async, argument binding, isolation, concurrency, and privacy are hardened |
| True shadow mode | Roadmap only on current main | Observe failures without changing delivery | Implement runtime semantics and persist explicit authority before K Top displays `SHADOW` |

The current `kaaval-agent` command and `/api/agent-runs` endpoint are not K Top
dependencies. K Top may observe model calls made by an agent application, but
Kaaval does not own that application's planning or tool orchestration.

## 11. Implementation form

### 11.1 Code ownership

The clean target is:

```text
kaaval-platform/
  src/kaaval_platform/cli/        # root `kaaval` command
  src/kaaval_platform/tui/        # Textual views and state
  src/kaaval_platform/client/     # versioned HTTP/SSE client
  src/kaaval_platform/schemas/    # generated/shared public records

kaaval-assurance/
  apps/api/v1/                    # product API and event adapter
  src/kaaval_assurance/...        # existing runtime authority
```

K Top belongs to Platform because it joins decisions, contracts, runtime
identity, and NanoCanary evidence. Assurance exposes the runtime API but does
not acquire terminal presentation logic.

### 11.2 Technology choice

Use Python Textual for v0.1 because both current products are Python, it can be
distributed through `uvx`/`pipx`, supports terminal resizing and keyboard
navigation, and provides an automated headless `Pilot` test surface. Keep all
domain models and transport code outside Textual widgets so a future Rust or Go
standalone client can replace the UI without changing the protocol.

Minimum dependencies for the TUI distribution:

- Textual for rendering and interaction;
- `httpx` for HTTP and SSE transport;
- a standards-based TOML reader for profiles;
- no provider SDKs in the K Top client.

The July 13 quick MVP uses standard-library terminal control plus the existing
`requests` dependency so it runs immediately in this package and can validate
the product interaction before adding a UI framework. That is an implementation
checkpoint, not a reversal of the target architecture: the domain/transport
seam is kept outside the renderer so the complete v0.1 can move to Textual and
headless Pilot tests without changing assurance semantics.

### 11.3 Internal component model

```text
Kaaval API -> HTTP/SSE client -> event reducer -> bounded local view state
                                              -> Overview
                                              -> Decision inspector
                                              -> Contracts
                                              -> Models/evidence
                                              -> Trends
```

Widgets receive immutable view models. They do not fetch network data, query a
database, evaluate contracts, or reinterpret evidence authority.

## 12. Delivery sequence

### Slice A: honest showcase

- define decision/event schemas and fixture set;
- implement the API client and TUI shell;
- implement `kaaval top --demo` using deterministic events produced from the
  existing mock Assurance pipeline;
- ship overview, inspector, truth labels, filtering, and help;
- add headless TUI and snapshot tests.

This is demo-ready but not yet a general developer integration.

### Slice B: live local attach

- add `/v1/status`, decision history, receipt, metrics, and SSE endpoints to
  Assurance;
- persist before publish and support cursor reconnect/deduplication;
- add runtime profiles, contracts, and incremental metrics;
- make `kaaval top --endpoint ...` work against a real local Assurance runtime.

### Slice C: integrated Platform showcase

- serve validated `BehavioralEvidenceRecord` objects through Platform;
- join evidence using provider, exact model/version, endpoint, and observation
  time;
- add Models/evidence and Trends views;
- package the same runtime and API for the web console;
- demonstrate local, captured, and advisory evidence without mixing them.

The product demo should not wait for transparent interception of every provider
SDK. A hardened explicit SDK or OpenAI-compatible proxy can generate real
decision events once it is ready.

### Feasibility estimate

For one engineer already familiar with these repositories, the planning ranges
are:

| Result | Scope | Working estimate |
|---|---|---:|
| Clickable/static terminal mock-up | Fixed fixture, no runtime integration | 1-2 days |
| Honest showcase | Slice A, pipeline-produced demo receipts, headless tests | 4-6 days |
| Useful local developer preview | Slices A+B, versioned history/receipt/SSE API | 10-15 days total |
| Integrated evidence showcase | Slices A-C, exact-identity NanoCanary evidence view | 13-20 days total |

These are engineering estimates, not production-readiness estimates. Durable
multi-user storage, authentication, authorization, retention, supportable
packaging, and enterprise deployment hardening remain outside v0.1.

## 13. Non-goals for v0.1

- contract authoring, promotion, or retirement from the TUI;
- human-review approvals from the TUI;
- automatic provider discovery or SDK monkey-patching;
- raw prompt/output browsing by default;
- generic agent traces, tool-call trees, or chain-of-thought display;
- model ranking or a single trust score;
- routing from raw NanoCanary dimensions;
- Layer 3 audit as an enforcement signal;
- Substrate memory browsing;
- ShadowDeploy promotion/rollback controls;
- enterprise multi-tenancy, RBAC administration, SSO, SCIM, retention policy
  editing, or billing;
- GPU process monitoring already served by `rocm-smi`, `nvtop`, or `btop`;
- a separately branded Chakra feature.

## 14. Acceptance criteria

### Installation and first value

- **KT-001:** On a clean supported machine, the documented installation and
  `kaaval top --demo` command work without credentials or access to any model,
  provider, or Kaaval cloud service after package installation.
- **KT-002:** The first populated screen appears within 60 seconds of command
  invocation and within 2 seconds after the local runtime reports healthy.
- **KT-003:** The demo deterministically displays conformant, recovered, and
  no-safe/provider-error decisions backed by stored pipeline receipts.
- **KT-004:** No demo row or metric is labeled `LIVE` or `MEASURED`.

### Runtime truth

- **KT-010:** Every displayed outcome maps to the stored final disposition and
  ordered attempts for that decision.
- **KT-011:** Every failed check ID shown by the TUI exactly matches the runtime
  record; the client does not rerun verification.
- **KT-012:** Contract conformance is never labeled correctness, truth, trust,
  or generic verification.
- **KT-013:** Provenance, authority, and outcome are displayed as separate
  concepts in overview and inspector views.
- **KT-014:** Missing metrics and evidence render as `unavailable`, not zero or
  a plausible default.
- **KT-015:** Audit and NanoCanary signals are visibly `DISPLAY ONLY` or
  `ADVISORY` and cannot affect K Top's decision outcome calculation.

### Streaming and resilience

- **KT-020:** The client renders 1,000 decision events without crashing or
  unbounded memory growth.
- **KT-021:** Disconnecting and reconnecting recovers all committed events after
  the last cursor with no duplicate rows.
- **KT-022:** Duplicate event delivery does not duplicate a decision.
- **KT-023:** A malformed or unsupported event produces a visible compatibility
  error and `UNKNOWN` row without terminating the session.
- **KT-024:** Pausing the viewport does not stop event ingestion.

### Privacy and safety

- **KT-030:** A default event capture contains no task input, raw model output,
  API key, credential, provider exception body, local filesystem path, or full
  endpoint query string.
- **KT-031:** `e` exports a redacted receipt only after confirmation and never
  overwrites an existing file silently.
- **KT-032:** No keyboard shortcut changes runtime policy, retries a call,
  promotes a model/contract, or executes a business action.
- **KT-033:** `kaaval doctor` output is secret-safe under an automated redaction
  test.

### Terminal usability

- **KT-040:** Core overview and inspector workflows are usable at 80x24 and
  120x36 terminal sizes.
- **KT-041:** The interface remains intelligible without color and exposes
  textual status labels, not color-only meaning.
- **KT-042:** Keyboard navigation, filtering, pause, inspect, help, copy,
  redacted export, and quit are covered by headless Textual tests.
- **KT-043:** A decision can be filtered by contract, model, outcome, and failed
  check ID.

### Architecture

- **KT-050:** K Top consumes only versioned public APIs/schemas and does not
  import verifier, router, provider, or trajectory-store internals.
- **KT-051:** K Top and the web console can render the same fixture decision
  record without semantic differences in outcome or authority.
- **KT-052:** Server persistence precedes completed-decision event publication.
- **KT-053:** NanoCanary evidence joins only on exact model/deployment identity;
  an ambiguous join renders evidence unavailable.

## 15. Adoption instrumentation

Telemetry must be local and opt-in until a user explicitly connects a managed
workspace. Do not upload model content or receipt payloads for product analytics.

### Activation funnel

- install-to-first-populated-screen time;
- install-to-first non-demo decision time;
- percentage of installs that return within seven days;
- percentage of active users who inspect at least one decision;
- percentage who filter on a failed check;
- percentage who connect a second environment or shared workspace;
- percentage who move from `UNASSURED` observations to a named contract.

### Utility and reliability

- weekly active local runtimes and K Top sessions;
- assured decisions observed per active project;
- inspector opens per 100 decisions;
- reconnect success and schema-compatibility error rate;
- p50/p95 event-to-screen latency;
- redacted exports and shared-receipt opens;
- terminal crash-free session rate.

### Enterprise-conversion signals

- requests for shared receipt history;
- requests for contract collaboration or approval workflow;
- requests for longer retention, RBAC, SSO, signed exports, or fleet views;
- number of teams that connect a local K Top profile to a shared Kaaval
  environment;
- number of pilot teams that progress from shadow observation to one approved
  enforced contract.

Initial experiment gates for ten external developers:

- at least eight reach a populated demo screen without help;
- at least five attach K Top to their own non-demo decision stream;
- at least five return for a second session within seven days;
- at least three inspect failures repeatedly;
- at least two ask to share receipts, contracts, or review state with a team.

If users repeatedly inspect tokens and latency but do not care about contracts,
failed checks, recovery, or receipts, K Top is pulling Kaaval toward commodity
observability and should not become the primary roadmap investment.

## 16. Definition of demo-ready v0.1

K Top v0.1 is demo-ready only when a stranger can:

1. run one documented offline command;
2. understand in the first screen that Kaaval is observing assured decisions,
   not generic processes;
3. watch a deterministic contract failure trigger recovery and a stored final
   outcome;
4. inspect the exact failed check IDs and attempt path;
5. distinguish `SAMPLE`, `ENFORCED`, `ADVISORY`, and `DISPLAY ONLY` evidence;
6. view an exact-model NanoCanary advisory record with its caveats or an honest
   unavailable state;
7. export a redacted receipt;
8. quit without leaving a credential, model process, or persistent demo service
   behind.

The showcase may then use the same protocol in Kaaval Console. Building a web
screen that looks similar but reads different data is not completion.
