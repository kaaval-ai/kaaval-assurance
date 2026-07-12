# Kaaval Assurance — Inference Flight Deck

The product surface for the Kaaval Assurance inference plane. Evidence
Baseline renders immutable telemetry, trajectories, and runtime-probe facts;
Live Session connects a user runtime and executes the real assurance pipeline.

This is **not** streaming telemetry: Captured Evidence mode re-reads artifacts
on a ~5 second cycle and on manual Refresh. Nothing on screen is invented —
missing values render as *not available*, sample data is labeled **SAMPLE**,
and AMD claims stay **pending** until a real runtime-probe artifact exists.

## Two modes

### Evidence Baseline (default; works everywhere)

- Loads telemetry, trajectory, and runtime-probe artifacts via the API.
- Needs no model endpoints and no secrets — safe to host publicly.
- Labels the data source: **SAMPLE**, **CAPTURED LOCAL RUN**,
  **CAPTURED FIREWORKS RUN**, or **MEASURED AMD RUN**, with artifact
  provenance (name, origin, timestamp) in the status bar.

### Live Session

- `POST /api/runtime-connections` tests and stores Fireworks BYOK, Ollama,
  vLLM, or an operator-enabled HTTPS endpoint in backend memory only.
- `POST /api/runs` resolves the ephemeral connection and drives the existing
  `AssurancePipeline`; the API never reimplements routing or verification.
- Fireworks requires the caller's per-run spend confirmation.
- Credentials expire after 15 idle minutes and never enter browser storage,
  SQLite, artifacts, telemetry, logs, or API responses.
- The live response feeds the pipeline graph, provider switchboard, contract
  gate, EWMA state, telemetry table, model comparison, and Kaaval Receipt.
- Requests are synchronous; the UI shows an honest pending state and then
  replays the returned trajectory. Export is operator-gated
  (`KAAVAL_ALLOW_ARTIFACT_EXPORT=1`) and writes each run to an isolated
  `artifacts/live-exports/<run-id>/` directory, never over the curated bundle.

## Running locally

Backend (from the **repo root**):

```bash
KAAVAL_LIVE_RUNS_ENABLED=1 KAAVAL_ALLOW_BYOK=1 \
  uv run uvicorn apps.api.server:app --port 8000

# private/local only: authorize paid remote calls and isolated API exports
KAAVAL_LIVE_RUNS_ENABLED=1 KAAVAL_ALLOW_PAID_REMOTE=1 \
  KAAVAL_ALLOW_ARTIFACT_EXPORT=1 \
  uv run uvicorn apps.api.server:app --port 8000
```

Frontend (from **apps/flight-deck**):

```bash
npm install
npm run dev        # http://localhost:5173 (proxies /api to :8000)
npm run build      # production build in dist/
```

## API

| Endpoint | Purpose |
|---|---|
| `GET /api/health` | liveness + live-run, paid-remote, and export gate states |
| `GET /api/capabilities` | deployment mode, runtime options, endpoint policy, and TTL |
| `POST/DELETE /api/runtime-connections` | test, create, and destroy ephemeral runtime connections |
| `GET /api/dashboard` | one typed payload: telemetry + trajectory + probe + provenance + labels |
| `GET /api/telemetry` · `/api/trajectory` · `/api/runtime-probe` | raw artifacts wrapped with provenance |
| `POST /api/runs` | gated live pipeline execution |

Artifact resolution order: real files under `artifacts/` → shipped sample
data under `demo_artifacts/sample/` → an explicit unavailable state.
Aliases are supported (`telemetry-truth.json` / `demo-live-telemetry.json`,
`trajectory-sample.json` / `demo-live-trajectory.json`). Malformed JSON is
skipped, never partially served. Provenance exposes artifact names and
origins only — no filesystem paths, no environment values.

## Source states

- `measured` — derived from stored trajectory rows, run results, or a
  runtime probe executed on the actual host
- `configured` — recorded settings (serving parameters, pricing), not
  measurements
- `sample` — shipped synthetic data so the UI runs anywhere; always labeled
- `planned` — intended deployment not yet executed
- `not_available` — the provider or run did not produce the value

## AMD evidence

AMD usage evidence comes from `python -m kaaval_assurance.runtime_probe`
run on the AMD machine — rocm-smi product name and VRAM, vLLM version, and
the served model — written to `artifacts/runtime-probe.json`. The AMD panel
shows **"AMD GPU measured run pending."** until that artifact exists. This
system does not implement hardware attestation and the UI claims none.
