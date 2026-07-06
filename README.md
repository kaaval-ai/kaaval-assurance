# Kaaval-AI: kaaval-assurance

The Kaaval **inference assurance plane**: task contracts, deterministic verification, per-category drift tracking, and sampled adversarial audit for AMD + Gemma agent workloads.

*Route efficiently. Verify continuously. Escalate intelligently.*

Built for the AMD Developer Hackathon ACT II (Track 3). Product wrapper: **KaavalAI**.

## What it does

Every request runs against an explicit **task contract**. The router sends it to the cheap local tier first (Gemma on AMD Instinct MI300X via ROCm + vLLM); **Layer 1** verifies the response deterministically against the contract (schema, required fields, enums, ranges); failures escalate to the remote tier (Fireworks). Every attempt writes a replayable row to the SQLite **trajectory store**.

Coming layers:

- **Layer 2** — per-category EWMA trend detection over verification signals.
- **Layer 3** — sampled, offline adversarial audit of accepted answers (5–10%). An LLM challenger produces structured violations JSON; deterministic code validates, aggregates, and thresholds it. It is a statistical sensor feeding trend statistics, never a per-response gate.

## Quickstart (mock mode, zero cloud access)

```bash
pip install -e ".[dev]"
pytest
```

```python
from kaaval_assurance.pipeline import AssurancePipeline
from kaaval_assurance.providers import MockProvider
from kaaval_assurance.router import Router
from kaaval_assurance.trajectory import TrajectoryStore

pipeline = AssurancePipeline(
    router=Router(),
    local_provider=MockProvider(tier="local"),
    remote_provider=MockProvider(tier="remote", model_id="mock-remote-strong"),
    store=TrajectoryStore("trajectory.db"),
)

result = pipeline.handle_request(
    "Core router CR-04 dropped all BGP sessions; region south offline.",
    "telecom.severity_classification",
)
print(result.verification.passed, result.routing.reason)
```

## Task contracts (initial set)

Four telecom incident-triage contracts, versioned:

| Contract | Category |
|---|---|
| `telecom.severity_classification` | Severity tier (P1–P4) with confidence + rationale |
| `telecom.component_extraction` | Involved components + root-cause component |
| `telecom.incident_summary` | NOC handover summary, impact, affected services |
| `telecom.next_action_recommendation` | Next action with urgency + justification |

## Layout

```
src/kaaval_assurance/
├── models.py        # ModelResponse, VerificationResult, TrajectoryRow, ...
├── contracts/       # TaskContract model + telecom contract definitions
├── providers/       # Provider interface + MockProvider (vLLM/Fireworks later)
├── router.py        # per-category tier choice; Layer 2 tightening seam
├── verifier.py      # Layer 1 deterministic contract checks
├── trajectory.py    # SQLite store, replayable rows, audit columns reserved
└── pipeline.py      # end-to-end request path
```

## AMD deployment (target)

- Local tier: `gemma-3-12b-it` served via **ROCm + vLLM** on **AMD Instinct MI300X** (192 GB HBM3), deployed on **AMD Developer Cloud**. Model ID, ROCm version, and GPU details will be recorded here once deployed.
- Remote escalation/audit tier: Fireworks AI.

## License

MIT — see [LICENSE](LICENSE).
