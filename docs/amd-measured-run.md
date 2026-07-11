# AMD + Gemma Measured Run

This report maps Kaaval Assurance's AMD execution claims to captured artifacts. It intentionally separates measured observations, configured serving settings, and values that were unavailable.

## Provenance

| Field | Captured value |
|---|---|
| Capture date | 2026-07-10 UTC |
| Source commit | `aa8b5b22b79fae47ea1c41327e72ddb311304e9b` |
| Coherent bundle ID | `live-5be3acfa-amd-gemma-proof` |
| Dashboard qualification | `MEASURED AMD RUN` |
| Local provider | `vllm-gemma` |
| Served model | `gemma-3-1b-it` |
| Runtime | vLLM ROCm build `0.16.1.dev0+g89a77b108.d20260318.rocm721` |
| PyTorch / HIP | `2.9.1+gitff65f5b` / `7.2.53211-e1a6bc5663` |
| Hardware facts | AMD/ATI vendor, `gfx1100`, 51,522,830,336 bytes VRAM |

The runtime could not resolve the GPU's marketing name because `libdrm` returned an error. No product name is inferred from the card identifier.

## Assurance Results

The full telecom gold evaluation passed locally through the Gemma/vLLM tier:

| Metric | Measured result |
|---|---:|
| Requests / attempts | 16 / 16 |
| Local Layer-1 contract-conformance rate | 100% |
| Final Layer-1 contract-conformance rate | 100% |
| Escalation rate | 0% |
| Verifier failures | 0 |
| Latency p50 | 324.6 ms |
| Latency p95 | 479.6 ms |
| Local inference cost recorded | $0.0000 |

The coherent one-request dashboard capture passed Layer 1 in 272.9 ms using 181 prompt tokens and 37 completion tokens. Its provider is `vllm-gemma`, its model matches the runtime probe's served-model list, and all three bundle run IDs match.

## Runtime Observations

These are observed peaks, not sustained-performance claims:

| Observation | Peak |
|---|---:|
| vLLM generation throughput logging window | 76.0 tokens/s |
| vLLM prompt throughput logging window | 62.7 tokens/s |
| Prefix-cache hit rate logged by vLLM | 74.4% |
| GPU use sampled by `rocm-smi` | 100% |
| Graphics package power sampled by `rocm-smi` | 175 W |
| Junction temperature sampled by `rocm-smi` | 44 C |

Configured serving settings were BF16, 8,192 maximum context tokens, 70% GPU-memory utilization, prefix caching enabled, and structured JSON output enabled. These settings are tagged `configured`; they are not represented as benchmark measurements.

## Evidence Map

| Artifact | What it proves |
|---|---|
| [`demo-live-manifest.json`](../artifacts/demo-live-manifest.json) | Atomic bundle membership and shared run ID |
| [`demo-live-telemetry.json`](../artifacts/demo-live-telemetry.json) | Provider, model, token, latency, verification, routing, and runtime-profile fields |
| [`demo-live-trajectory.json`](../artifacts/demo-live-trajectory.json) | Replayable input, raw Gemma output, and Layer-1 verdict |
| [`runtime-probe.json`](../artifacts/runtime-probe.json) | Reachable vLLM endpoint, served model, AMD/ROCm commands, and redacted configuration |
| [`runtime-probe-pre-serve.json`](../artifacts/runtime-probe-pre-serve.json) | Host/runtime facts captured before model serving |
| [`telemetry-vllm.md`](../artifacts/telemetry-vllm.md) | Human-readable 16-case assurance summary |
| [`vllm-gemma3-server.log`](../artifacts/vllm-gemma3-server.log) | Gemma architecture resolution, ROCm Triton backend, model load, server startup, and throughput windows |
| [`amd-runtime-samples.log`](../artifacts/amd-runtime-samples.log) | Time-series ROCm temperature, power, utilization, and VRAM observations |
| [`vllm-metrics-eval-16.prom`](../artifacts/vllm-metrics-eval-16.prom) | Prometheus counters after the 16-request evaluation |
| [`vllm-metrics-eval-32.prom`](../artifacts/vllm-metrics-eval-32.prom) | Later Prometheus snapshot with 32 cumulative chat-completion requests |
| [`SHA256SUMS-amd-aa8b5b2.txt`](../artifacts/SHA256SUMS-amd-aa8b5b2.txt) | Integrity hashes for the curated repository evidence |

The complete forensic archive, including the SQLite trajectory store, is retained separately as `kaaval-amd-evidence-aa8b5b2-clean.tgz` with its own SHA-256 checksum.
