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
- The local model must fit in GPU memory together with the vLLM runtime and
  KV cache overhead — size the model choice against the ~48 GB figure, not
  against the model weights alone.
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
python -m kaaval_assurance.runtime_probe                                  # JSON
python -m kaaval_assurance.runtime_probe --text                           # human
python -m kaaval_assurance.runtime_probe --output artifacts/runtime-probe.json
```

Collects, without ever failing on missing host tools: working directory and
whether it is under `/workspace`, Python version, import checks for `vllm` /
`torch` / `requests` / `pydantic`, `rocm-smi --showproductname` and
`--showmeminfo vram` when available, `vllm --version` when available, plus the
vLLM endpoint probe (served models, whether `VLLM_MODEL` is actually served,
vLLM server version, family-consistency check). Every section carries a
source tag — measured, configured, or not_available — and env output is
redacted so secrets never print. `--require-endpoint` makes the exit code 1
when the endpoint is down (used by the vLLM smoke script); otherwise the
probe always exits 0.

## Smoke sequence (run in this order)

| Step | Script | Network | Spend |
|---|---|---|---|
| 1. Mock truth run | `scripts/mock_truth_run.sh` | none | none |
| 2. Runtime probe + vLLM smoke | `scripts/vllm_smoke_run.sh` | pod only | none |
| 3. Fireworks smoke | `scripts/fireworks_smoke_run.sh` | Fireworks | **credits** |
| 4. Demo artifact export | `scripts/write_demo_artifacts.sh` | none | none |

## Fireworks budget guardrails

- `scripts/fireworks_smoke_run.sh` refuses to run unless
  `KAAVAL_CONFIRM_SPEND=1`.
- Credits are for escalation, challenger audit, and the baseline — never for
  wasteful full-grid runs.
- The always-remote baseline runs **once** and its trajectory DB is cached;
  reuse it via `--always-remote-baseline-db` — never re-run the baseline
  during polish.
- Prefer the mock audit challenger for repeated dashboard/demo iteration; a
  full mock rehearsal costs nothing.
- Plan for **one** final live remote-escalation run and **one** final
  challenger audit sample with Fireworks — not repeated live runs.
- Avoid repeated `--audit-sample-rate 1.0` with `--audit-provider fireworks`
  unless intentionally spending credits (see optional full audit below).
- Credit-pool discipline: Pool 1 (one key) for development churn; Pool 2
  preserved for eval runs, Layer 3 audit calls, proof runs, and demo recording.
- Set `FIREWORKS_MODEL` to a model from the event credit allocation (the FAQ
  mentions Kimi and MiniMax endpoints).
- Prove the economics with telemetry fields, not assertions: cost per
  contract-conformant answer and remote-calls-avoided come from
  `--telemetry-summary` with the cached baseline DB.

### Optional: full Fireworks challenger audit (intentional spend)

The default audit path samples 10% and the smoke script uses failure
injection with no audit at all. A 100% Fireworks audit is a deliberate,
one-off spend for the final proof run only:

```bash
KAAVAL_CONFIRM_SPEND=1  # your explicit decision, not a default
set -a; source .env; set +a
kaaval-eval --dataset data/eval/telecom_gold.jsonl \
  --audit-provider fireworks --audit-sample-rate 1.0 \
  --telemetry-summary --db artifacts/trajectory-final-audit.db
```

Calibration against the 16 gold answers runs first and also costs credits —
16 challenger calls before sampling starts. Budget for it.

## Demo artifact export

```bash
scripts/write_demo_artifacts.sh
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
