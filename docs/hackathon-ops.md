# Hackathon Ops Pack

Operational runbook for running kaaval-assurance during the AMD Developer
Hackathon ACT II. Everything here follows the telemetry truth rules: `planned`
(intended, not executed), `configured` (recorded settings), `measured`
(probe/eval results). Model id and family are telemetry fields, not marketing
claims.

## AMD hackathon GPU pod

- Access: https://notebooks.amd.com/hackathon
- Persistent storage: `/workspace` (25 GB) — keep the repo, venv, and model
  cache decisions inside it; everything else may not survive pod restarts.
- GPU memory: about 48 GB. Describe the pod only by this FAQ figure — never
  by data-center GPU specs that were not probed on this pod.
- vLLM runs from the Jupyter pod terminal.
- No live endpoint is required for judging. The submission needs the GitHub
  URL, a demo video, and a ~5-slide deck — demo artifacts can all be produced
  from recorded runs.

## Serving the local tier (Gemma-first)

The local tier is Gemma-first via vLLM on the AMD hackathon GPU. Pick a Gemma
model that fits the ~48 GB GPU; decide the exact size only after probing the
pod. Serve it with the same shape the FAQ uses:

```bash
vllm serve <chosen-gemma-model> --port 8000 --gpu-memory-utilization 0.3
```

Then set `VLLM_MODEL` to the served id (the runtime probe lists it) and keep
`VLLM_MODEL_FAMILY=gemma`.

**Fallback policy:** if Gemma does not serve reliably on the pod, the FAQ's
example model is the operational fallback:

```bash
vllm serve Qwen/Qwen2-7B-Instruct --port 8000 --gpu-memory-utilization 0.3
```

If you fall back, update `VLLM_MODEL` and set `VLLM_MODEL_FAMILY=qwen` — the
fallback local model is recorded truthfully in telemetry, never papered over.

## Environment setup

```bash
cp .env.example .env      # fill in; .env is never committed
set -a; source .env; set +a
```

## Runtime probe (turns "configured" into "measured")

```bash
python -m kaaval_assurance.runtime_probe
python -m kaaval_assurance.runtime_probe --output artifacts/runtime-probe.json
```

Reports endpoint reachability, served models, whether `VLLM_MODEL` is actually
served, vLLM version when exposed, and a family-consistency check. Env output
is redacted — secrets never print. Exit code 0 = reachable, 1 = not.

## Smoke sequence (run in this order)

| Step | Script | Network | Spend |
|---|---|---|---|
| 1. Mock truth run | `scripts/run_mock_truth.sh` | none | none |
| 2. Runtime probe + vLLM smoke | `scripts/smoke_vllm.sh` | pod only | none |
| 3. Fireworks smoke | `scripts/smoke_fireworks.sh` | Fireworks | **credits** |
| 4. Demo artifact export | `scripts/export_demo_artifacts.sh` | none | none |

## Fireworks budget guardrails

- `scripts/smoke_fireworks.sh` refuses to run unless `KAAVAL_CONFIRM_SPEND=1`.
- Credit-pool discipline: Pool 1 (one key) for development churn; Pool 2
  preserved for eval runs, Layer 3 audit calls, proof runs, and demo recording.
- The always-remote baseline runs **once** and its trajectory DB is cached;
  reuse it via `--always-remote-baseline-db` — never re-run the baseline
  during polish.
- Layer 3 audit is sampled (default 10%) and calibrates against the 16 gold
  answers first; a full mock rehearsal costs nothing, so rehearse in mock
  before any live audit run.
- Set `FIREWORKS_MODEL` to a model from the event credit allocation (the FAQ
  mentions Kimi and MiniMax endpoints).

## Demo artifact export

```bash
scripts/export_demo_artifacts.sh
```

Writes to `artifacts/` (git-ignored): eval output text, telemetry truth
markdown, closed-loop demo transcript, and trajectory DBs — everything the
video and deck need without a live endpoint.

## Submission checklist

- [ ] GitHub URL (public repo, MIT LICENSE, README current)
- [ ] Demo video (honesty lines included: synthetic shift data; Layer 3 is a
      sampled offline audit signal, not a judge of record)
- [ ] ~5-slide deck
- [ ] Telemetry truth block in the demo maps every claim to a source tag
- [ ] Runtime claims match reality: measured only after the pod probe/runs
