# Track 3 Submission Checklist (Unicorn / Open Innovation)

Track 3 pre-screening centers on a clear implementation path, a genuinely
runnable project, original use of approved compute, and complete setup and
external-service documentation. AMD compute usage is mandatory. The release
path for this submission is the public repository, one public container, and
one hosted Flight Deck URL; the deck remains required by the AMD-specific
instructions.

## Required assets

- [ ] **GitHub repository URL** — public, MIT LICENSE, README current, no
      secrets (`.env` untracked), sample demo data present so the repo runs
      standalone.
- [ ] **Demo video (< 5 min)** — follow the `demo_video_script_narrative.md` in your artifacts;
      Our 3:30 planned video perfectly fits. Both honesty lines spoken (synthetic shift data; Layer 3 is a sampled
      offline audit signal, not a judge of record).
- [ ] **Slide deck PDF (~5 slides)** — pre-screening reads this: include the
      architecture flow, the telemetry truth table with source tags, and the
      AMD proof artifacts. Export as PDF, keep text machine-readable (no
      screenshots of text).
- [ ] **16:9 cover image** — final branded submission cover.
- [ ] **Paste-ready form copy** — title (max 50), short description (max 255),
      long description (100+ words), technologies, and additional information.

## Public delivery path

- [ ] **Public image** — `ghcr.io/kaaval-ai/kaaval-assurance:act-ii` plus an
      immutable `sha-<commit>` tag and recorded digest, all from final `main`.
- [ ] **Clean pull test** — pull the digest into a clean Finch VM with no
      repository files or secrets; verify Evidence Baseline, `/api/health`,
      Live Session onboarding, fail-closed rejection, and non-root UID.
- [ ] **Hosted URL** — deploy the same image digest. Evidence Baseline must
      load without credentials; public Fireworks use is BYOK and explicitly
      spend-confirmed.

## AMD proof artifacts (mandatory usage evidence)

- [x] `artifacts/runtime-probe.json` from the AMD pod — rocm-smi product
      name + VRAM, vLLM version, served Gemma model (source: measured).
- [x] `artifacts/telemetry-vllm.md` / trajectory evidence from the pod eval
      run — local Gemma tier contract-conformance rates and runtime profile
      recorded.
- [ ] Telemetry summary lines in deck/video sourced from these artifacts
      only; anything not yet measured stays labeled configured/planned.

## Final pass

- [x] Local acceptance: 361 tests, TypeScript, Vite build, dependency checks,
      AMD checksums, and `linux/amd64` container smoke are green.
- [ ] Forbidden-string and secrets grep clean.
- [ ] Public repository, image, hosted URL, deck, and video pass an incognito
      access/link audit.
- [ ] Deck, video, README, and console all tell the same numbers — every
      claim maps to a stored telemetry field.
