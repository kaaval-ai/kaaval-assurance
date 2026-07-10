# Telemetry truth summary

Run `9900471e` — 16 requests, 16 attempts, latency p50 324.6ms / p95 479.6ms.

| Claim | Value | Source |
|---|---|---|
| Local verified rate | 100.0% | measured |
| Final verified rate | 100.0% | measured |
| Escalation rate | 0.0% | measured |
| Preroute remote rate | 0.0% | measured |
| High-drift categories | none | measured |
| Layer 3 audit trusted | no audit in this run | not_available |
| Cost per verified answer | $0.0000 | measured |
| Remote calls avoided vs always-remote | n/a (no always-remote baseline) | not_available |
| Runtime | gemma 'gemma-3-1b-it' via vLLM, target amd-hackathon-gpu; dtype bfloat16, kv-cache auto, tp 1; ROCm 7.2, vLLM 0.16.1.dev0+g89a77b108.d20260318.rocm721 | configured |

Sources: measured = derived from stored trajectory rows; configured = recorded runtime settings, not measurements; not_available = the provider or run did not produce this value; planned = intended deployment not yet executed.
