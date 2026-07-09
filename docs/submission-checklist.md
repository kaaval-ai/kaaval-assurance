# Track 3 Submission Checklist (Unicorn / Open Innovation)

Per the participant guide: Track 3 does **not** require a Docker image.
Automated pre-screening inspects the GitHub repo, the slide deck PDF, and the
live/hosted URL if provided — it does **not** process the demo video. AMD
compute usage is mandatory; projects without demonstrated AMD resource usage
can be disqualified.

## Required assets

- [ ] **GitHub repository URL** — public, MIT LICENSE, README current, no
      secrets (`.env` untracked), sample demo data present so the repo runs
      standalone.
- [ ] **Demo video (~2 min)** — follow [demo-script.md](demo-script.md);
      both honesty lines spoken (synthetic shift data; Layer 3 is a sampled
      offline audit signal, not a judge of record).
- [ ] **Slide deck PDF (~5 slides)** — pre-screening reads this: include the
      architecture flow, the telemetry truth table with source tags, and the
      AMD proof artifacts. Export as PDF, keep text machine-readable (no
      screenshots of text).

## Optional but recommended

- [ ] **Hosted URL** — demo console (`apps/demo_console/`) on Streamlit
      Community Cloud or Hugging Face Spaces. It replays captured AMD
      telemetry; no live model endpoint is required or implied.

## AMD proof artifacts (mandatory usage evidence)

- [ ] `artifacts/runtime-probe.json` from the AMD pod — rocm-smi product
      name + VRAM, vLLM version, served Gemma model (source: measured).
- [ ] `artifacts/telemetry-vllm.md` / trajectory DB from the pod eval run —
      local Gemma tier verified rates, runtime profile recorded.
- [ ] Telemetry summary lines in deck/video sourced from these artifacts
      only; anything not yet measured stays labeled configured/planned.

## Final pass

- [ ] `pytest` green.
- [ ] Forbidden-string and secrets grep clean.
- [ ] Deck, video, README, and console all tell the same numbers — every
      claim maps to a stored telemetry field.
