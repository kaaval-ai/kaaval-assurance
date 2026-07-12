---
marp: true
theme: default
class: invert
style: |
  section {
    background-color: #0B0F19;
    color: #F3F4F6;
    font-family: 'Inter', sans-serif;
  }
  h1, h2, h3 {
    color: #F3F4F6;
  }
  strong {
    color: #10B981;
  }
---

# Kaaval Assurance

<div style="display: grid; grid-template-columns: 1.2fr 1fr; gap: 30px; align-items: center;">
  <div>
    <h2 style="color: #10B981; margin-top: 0;">Routers predict. Kaaval verifies.</h2>
    <p style="font-size: 18px; line-height: 1.6; margin-bottom: 20px;">An inference assurance plane for open-weight models on AMD compute.</p>
    <em style="color: #ffd166; font-size: 14px; font-family: monospace;">Verify, not predict. Receipts, not promises.</em>
  </div>
  <div>
    <img src="assets/slide1-hero.png" style="width: 100%; max-height: 380px; object-fit: contain; border-radius: 12px; border: 1px solid #10B981; box-shadow: 0 0 15px rgba(16,185,129,0.2);" />
  </div>
</div>

---

## The Problem: Accountability Gap

<div style="display: grid; grid-template-columns: 1.2fr 1fr; gap: 30px; align-items: center;">
  <div style="font-size: 16px; line-height: 1.5;">
    <p><strong>The Accountability Gap:</strong> If an AI agent makes the wrong transaction, the enterprise still owns the customer outcome and liability.</p>
    <p><strong>The Fluent Failure Mode:</strong> Unsafe AI answers are fluent and grammatically correct—but factually or legally wrong. Standard guardrails check syntax; they cannot verify business logic.</p>
    <p><strong>The Business Risk:</strong> As agents handle refunds, claims, and quotes, quality drift translates directly into financial exposure.</p>
  </div>
  <div>
    <img src="assets/slide2-problem.png" style="width: 100%; max-height: 380px; object-fit: contain; border-radius: 12px; border: 1px solid #FF8C42; box-shadow: 0 0 15px rgba(255,140,66,0.25);" />
  </div>
</div>

---

## The Solution: Kaaval Product

<div style="display: grid; grid-template-columns: 1.2fr 1fr; gap: 30px; align-items: center;">
  <div style="font-size: 15px; line-height: 1.5;">
    <ol>
      <li><strong>Local First:</strong> Run task on cheap, local open-weight models (Gemma) on owned hardware.</li>
      <li><strong>Real-time Gate:</strong> Intercept response and test against a strict code contract <em>before</em> it ships.</li>
      <li><strong>Fail-Safe Escalation:</strong> Automatically route to a remote backup tier only when local verification fails.</li>
      <li><strong>Decision Receipts:</strong> Store every transaction, latency, cost, and verifier check in an auditable database.</li>
    </ol>
  </div>
  <div>
    <img src="assets/slide3-solution.png" style="width: 100%; max-height: 380px; object-fit: contain; border-radius: 12px; border: 1px solid #10B981; box-shadow: 0 0 15px rgba(16,185,129,0.25);" />
  </div>
</div>

---

## Three-Layer Assurance Architecture

<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; align-items: center;">
  <div style="font-size: 14px; line-height: 1.4;">
    <p><strong>Layer 1: Contract Conformance</strong><br/>
    Structured JSON schema, enums, range checks, and grounding rules. Deterministic, code-only checks (no LLM judging LLM).</p>
    <p><strong>Layer 2: Adaptive Drift Routing</strong><br/>
    EWMA failure tracking. Automatically tightens routing thresholds when local quality degrades.</p>
    <p><strong>Layer 3: Sampled Offline Audit</strong><br/>
    Calibration-gated adversarial auditing. Critic model challenges a 10% sample of accepted answers.</p>
  </div>
  <div>
    <img src="assets/kaaval-architecture-flow.svg" style="width: 100%; max-height: 350px; object-fit: contain; border-radius: 8px; background-color: #060a11; border: 1px solid #172233; padding: 10px;" />
  </div>
</div>

---

## The Telemetry Truth (Evidence)

No claim without a stored field. No field without a source tag.

| Metric | Captured Value | Source Tag |
|---|---|---|
| **Local Conformance Rate** | `100.0%` | `measured` |
| **Final Verified Rate** | `100.0%` | `measured` |
| **Escalation Rate** | `0.0%` | `measured` |
| **Latency p50 / p95** | `324.6 / 479.6 ms` | `measured` |
| **Inference Cost** | `$0.0000 (Local-First)` | `measured` |
| **Active Run ID** | `live-5be3acfa-amd-gemma-proof` | `measured` |

---

## AMD Proof & Hardware Stack

- **Hardware Stack:** AMD Radeon gfx1100 target, 47.98 GiB VRAM.
- **Software Stack:** vLLM served via ROCm 7.2 + PyTorch 2.9.
- **Measured Proof Bundle:** Locked to source commit `aa8b5b2` with SHA-256 integrity hashes (`SHA256SUMS-amd-aa8b5b2.txt`).

---

## Market Positioning

**Traditional Routers (Guess & Hope):** 
Focus on *predicting* model quality before generation. Useful for text completion, but fails when business contracts cannot tolerate errors.

**Kaaval Assurance (Verify & Adapt):** 
Focus on *measuring* output conformance after generation. Perfect for policy-bound decisions, API spend governance, and auditable automation.

