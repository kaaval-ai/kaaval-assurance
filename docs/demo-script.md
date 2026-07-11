# Demo Video Runbook (AI Voiceover + Cursor Choreography)

Target length: 3:45-4:00 at normal speaking speed.

Primary surface: Flight Deck Summary view, then Telemetry view.

Recording rule: use **Captured Evidence** mode for the submitted video. Say this
as an engineering choice, not a limitation: it lets judges replay the measured
AMD/Gemma evidence without API keys, GPU access, or paid calls.

Cursor rule: the pointer is the guide. Move slowly, hover deliberately, and
pause on each proof element while the narration names it. Avoid fast circles,
random mouse movement, and scrolling while the voiceover is explaining a
specific number.

## Setup Before Recording

1. Start the API and Flight Deck locally.
2. Open `http://127.0.0.1:5173`.
3. Select **Captured Evidence** and **Summary**.
4. Scroll to the very top of the Summary page.
5. Use 125-150% browser zoom only if text is too small in the recording.
6. Keep browser chrome minimal; no terminal needed unless recording a quick
   appendix shot.

## 0:00-0:25 — Opening / Product Identity

Voiceover:

"Kaaval Assurance is an inference assurance plane built by Hari Krishna
Govindaraj and Milind Gunjan for the AMD Developer Hackathon ACT II. It is a
guardian layer for enterprise open-weight inference: a control plane that helps
teams decide when a local model answer can be trusted, when to escalate, and how
to prove that decision afterward."

Cursor:

- Hover over the header title **Kaaval Assurance**.
- Move to the top badge **MEASURED AMD RUN**.
- Pause for one second.

Screen must show:

- Header title.
- `MEASURED AMD RUN`.
- Captured Evidence mode selected.

## 0:25-0:55 — Why It Exists

Voiceover:

"Enterprises want the economics and control of local inference, especially with
open-weight models like Gemma. But they still need governance: quality gates,
routing policy, runtime evidence, cost visibility, and an audit trail. Kaaval
sits between the task and the model response. It verifies every answer against
an explicit task contract, captures the full trajectory, and gives operators
assurance and visibility across the inference lifecycle."

Cursor:

- Hover over **Captured Evidence**.
- Move across the hosted replay banner: **No API key required**, **No hosted
  spend path**, **Artifacts are the source of truth**.
- Pause briefly on each small proof chip.

Screen must show:

- Hosted replay evidence banner.
- No secrets / no spend path language.

## 0:55-1:20 — Two Modes

Voiceover:

"The Flight Deck has two modes. Live Run mode can execute the real assurance
pipeline server-side, with local providers like Ollama or vLLM and optional
Fireworks escalation behind explicit spend confirmation. For this submission
video, we use Captured Evidence mode. That makes the demo reproducible and
judge-safe: the measured AMD run can be replayed without live GPU access,
without API keys, and without spending model credits."

Cursor:

- Hover over **Live Run** without clicking.
- Move back to **Captured Evidence**.
- Hover over **Summary**.

Screen must show:

- Captured Evidence and Live Run controls.
- Summary tab selected.

## 1:20-2:05 — Summary Proof Strip

Voiceover:

"The proof strip is the fastest way to understand the run. This bundle is
labeled MEASURED AMD RUN because the runtime probe, telemetry, trajectory, and
manifest agree. Gemma 3 1B was served through vLLM on a ROCm-enabled AMD GPU
environment. The run captured model identity, provider, latency, tokens,
verifier outcome, and runtime settings. Kaaval also compares local-first
routing against an always-remote Fireworks baseline: fourteen remote calls were
avoided, configured remote cost dropped by 88.7 percent, and the final verified
rate stayed at 100 percent."

Cursor:

- Hover over **AMD proof**.
- Hover over **Gemma runtime**.
- Hover over **Remote calls avoided**.
- Hover over **Cost avoided**.
- Hover over **Final verified**.
- Pause a beat on the `14` and `$0.0333` values.

Screen must show:

- Proof strip cards.
- `14` remote calls avoided.
- `$0.0333` cost avoided.
- `100.0%` final verified.

## 2:05-2:35 — Demo Rail / Guardian Flow

Voiceover:

"The demo rail shows the guardian loop. First, local models can struggle.
Second, Layer 1 catches failures with deterministic contract checks. Third,
only failed responses escalate. Fourth, EWMA drift tracking can tighten routing
when a category keeps failing. Fifth, every decision becomes a receipt. The goal
is not to replace the model. The goal is to make model use accountable."

Cursor:

- Move left to right across the five demo rail cards.
- Pause on each title: **Struggle**, **Catch**, **Rescue**, **Adapt**, **Prove**.
- End on **Prove**.

Screen must show:

- Two-minute demo rail.
- Five-step guardian flow.

## 2:35-3:05 — Cost Avoidance Receipt

Voiceover:

"The Cost Avoidance Receipt turns the routing strategy into enterprise
economics. It compares local-first routing to an always-remote baseline using
recorded trajectory databases. The green bars are the local-first path. The
yellow bars are the always-remote path. This makes the value concrete: fewer
remote calls, lower configured spend, and a higher verified rate in the
captured comparison."

Cursor:

- Hover over the **Cost Avoidance Receipt** title.
- Trace down the three rows: **Remote calls**, **Configured remote cost**,
  **Final verified rate**.
- Hover over the right-side **Judge Readout** panel.

Screen must show:

- Green and yellow comparison bars.
- `87.5%` judge readout.
- Caveat text below the chart.

## 3:05-3:35 — Switch To Telemetry View

Action:

- Click **Telemetry** in the top navigation.

Voiceover:

"Now we switch to Telemetry view. Telemetry is not a dashboard extra here. It is
the assurance layer. Kaaval captures provider, model ID, local or remote tier,
latency, tokens, cost, verifier pass or fail, failed check IDs, routing reason,
drift category, runtime profile, and source tags for every claim."

Cursor:

- Hover over **Provider Switchboard**.
- Hover over **Contract Gate**.
- Hover over **Telemetry Truth**.

Screen must show:

- Telemetry view.
- Provider switchboard.
- Contract gate.
- Telemetry truth panel.

## 3:35-3:55 — Kaaval Receipt + AMD Evidence

Voiceover:

"The Kaaval Receipt is the audit trail for a single answer. It shows the task
input, provider, model ID, tier, raw output, verifier result, latency, tokens,
and cost. The AMD Runtime Evidence panel connects that software trace back to
the hardware and serving stack: ROCm, vLLM, served Gemma model, endpoint
reachability, GFX target, and VRAM. If evidence is missing, Kaaval says not
available. It does not invent proof."

Cursor:

- Hover over **Kaaval Receipt**.
- Hover over the local attempt row.
- Hover over **AMD Runtime Evidence**.
- Pause on served model / ROCm / vLLM / VRAM facts.

Screen must show:

- Kaaval Receipt.
- AMD Runtime Evidence.
- Source tags.

## 3:55-4:00 — Close

Voiceover:

"Kaaval Assurance is a guardian layer for open-weight AI in the enterprise:
local-first when the answer is verified, escalation when it is not, and
telemetry receipts for every decision."

Cursor:

- Return to the header badge **MEASURED AMD RUN** or leave the pointer on
  **Kaaval Receipt**.

## Recording Notes

- Use a calm technical voice, not a hype voice.
- Keep cursor motion slow and intentional.
- Do not say "time constraints." Say "reproducible" and "judge-safe."
- If the recording is running long, cut the detailed Provider Switchboard line,
  not the guardian framing or the receipt explanation.
- Best closing line: "Kaaval does not just claim lower cost or reliable
  routing. It shows the receipt."
