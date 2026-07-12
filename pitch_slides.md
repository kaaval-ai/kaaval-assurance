---
marp: true
theme: default
class: invert
style: |
  section {
    background-color: #0B0F19;
    color: #F3F4F6;
    font-family: 'Inter', sans-serif;
    padding: 40px;
  }
  h1 {
    color: #F3F4F6;
    font-size: 56px;
    margin-bottom: 10px;
    letter-spacing: -1.5px;
  }
  h2 {
    color: #10B981;
    font-size: 36px;
    margin-top: 0;
    margin-bottom: 20px;
    font-weight: 700;
  }
  p {
    font-size: 20px;
    color: #9CA3AF;
    line-height: 1.6;
  }
  strong {
    color: #10B981;
  }
  .highlight {
    color: #ffd166;
  }
  .big-num {
    font-size: 80px;
    font-weight: 800;
    color: #10B981;
    line-height: 1;
    margin-bottom: 5px;
  }
  .stat-card {
    background: #111928;
    border: 1px solid #1f2a37;
    border-radius: 12px;
    padding: 20px;
    text-align: center;
  }
---

# Kaaval Assurance

<div style="display: grid; grid-template-columns: 1.2fr 1fr; gap: 40px; align-items: center; height: 80%;">
  <div>
    <h2>Routers predict.<br/>Kaaval verifies.</h2>
    <p>An inference assurance plane for open-weight models on AMD compute.</p>
    <div style="margin-top: 30px; font-size: 16px; font-family: monospace; color: #ffd166;">
      Verify, not predict. Receipts, not promises.
    </div>
  </div>
  <div>
    <img src="assets/slide1-hero.png" style="width: 100%; max-height: 380px; object-fit: contain; border-radius: 12px; border: 1px solid #10B981; box-shadow: 0 0 20px rgba(16,185,129,0.25);" />
  </div>
</div>

---

## AI Decisions are Liabilities.

<div style="display: grid; grid-template-columns: 1.2fr 1fr; gap: 40px; align-items: center; height: 80%;">
  <div>
    <p style="font-size: 24px; color: #F3F4F6; font-weight: 500;">
      Unverified local models approve unauthorized refunds, create exposure, and fail silently.
    </p>
    <p style="margin-top: 20px;">
      Standard guardrails check syntax; they cannot verify business logic. As agents handle transactions, quality drift translates directly into financial risk.
    </p>
  </div>
  <div>
    <img src="assets/slide2-problem.png" style="width: 100%; max-height: 380px; object-fit: contain; border-radius: 12px; border: 1px solid #FF8C42; box-shadow: 0 0 20px rgba(255,140,66,0.3);" />
  </div>
</div>

---

## Gate. Verify. Escalate.

<div style="display: grid; grid-template-columns: 1.2fr 1fr; gap: 40px; align-items: center; height: 80%;">
  <div>
    <p style="font-size: 24px; color: #F3F4F6; font-weight: 500;">
      Local open-weight inference checked by code contracts in &lt;1ms. Only fails safe.
    </p>
    <p style="margin-top: 20px;">
      Kaaval intercepts response structures locally. If checks fail, it routes to a remote backup, saving <strong>88%</strong> of API costs while guaranteeing compliance.
    </p>
  </div>
  <div>
    <img src="assets/slide3-solution.png" style="width: 100%; max-height: 380px; object-fit: contain; border-radius: 12px; border: 1px solid #10B981; box-shadow: 0 0 20px rgba(16,185,129,0.3);" />
  </div>
</div>

---

## 3-Layer Assurance Engine

<div style="display: grid; grid-template-columns: 1fr 1.2fr; gap: 30px; align-items: center; height: 80%;">
  <div style="font-size: 16px; line-height: 1.6;">
    <div style="margin-bottom: 20px;">
      <h3 style="color: #10B981; margin: 0; font-size: 20px;">1. Conformance Gate</h3>
      <span style="color: #9CA3AF;">Deterministic JSON shape, enums, & grounding checks in &lt;1ms.</span>
    </div>
    <div style="margin-bottom: 20px;">
      <h3 style="color: #ffd166; margin: 0; font-size: 20px;">2. Adaptive EWMA Routing</h3>
      <span style="color: #9CA3AF;">Tracks category failures in real-time. Pre-routes directly to remote on drift.</span>
    </div>
    <div>
      <h3 style="color: #ef4444; margin: 0; font-size: 20px;">3. Sampled Offline Audit</h3>
      <span style="color: #9CA3AF;">Adversarial critic challenges accepted answers with FP-calibration.</span>
    </div>
  </div>
  <div>
    <img src="assets/kaaval-architecture-flow.svg" style="width: 100%; max-height: 360px; object-fit: contain; border-radius: 8px; background-color: #060a11; border: 1px solid #172233; padding: 10px;" />
  </div>
</div>

---

## Measured Proof on AMD Silicon

<div style="grid-template-rows: auto 1fr; gap: 20px; height: 80%;">
  <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin-top: 20px;">
    <div class="stat-card">
      <div class="big-num">100%</div>
      <div style="font-size: 12px; font-family: monospace; color: #ffd166; margin-bottom: 5px;">[ MEASURED ]</div>
      <span style="color: #e6edf3; font-size: 15px; font-weight: 600;">Contract Conformance</span>
    </div>
    <div class="stat-card">
      <div class="big-num">88%</div>
      <div style="font-size: 12px; font-family: monospace; color: #ffd166; margin-bottom: 5px;">[ MEASURED ]</div>
      <span style="color: #e6edf3; font-size: 15px; font-weight: 600;">API Costs Saved</span>
    </div>
    <div class="stat-card">
      <div class="big-num">0%</div>
      <div style="font-size: 12px; font-family: monospace; color: #ffd166; margin-bottom: 5px;">[ MEASURED ]</div>
      <span style="color: #e6edf3; font-size: 15px; font-weight: 600;">Escalation Rate (Proof Run)</span>
    </div>
  </div>
  <div style="margin-top: 30px; text-align: center; font-family: monospace; font-size: 14px; color: #9CA3AF;">
    Hardware: <strong style="color: #ffd166;">AMD Radeon gfx1100 target (48GB VRAM)</strong> served via <strong style="color: #22d3ee;">vLLM (ROCm 7.2)</strong>. <br/>
    Commit <span style="color: #e6edf3;">aa8b5b2</span> verified with SHA-256 integrity checks.
  </div>
</div>

---

## Verify, Don't Predict.

<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 40px; align-items: start; height: 80%; margin-top: 30px;">
  <div style="background: rgba(239, 68, 68, 0.05); border: 1px solid rgba(239, 68, 68, 0.2); border-radius: 12px; padding: 25px;">
    <h3 style="color: #ef4444; margin-top: 0; font-size: 22px;">Traditional Routers</h3>
    <p style="font-size: 16px; margin-bottom: 0;">
      Focus on <strong>guessing</strong> model quality <em>before</em> generation. Works for content writing, but fails when business contracts cannot tolerate errors.
    </p>
  </div>
  <div style="background: rgba(16, 185, 129, 0.05); border: 1px solid rgba(16, 185, 129, 0.2); border-radius: 12px; padding: 25px;">
    <h3 style="color: #10B981; margin-top: 0; font-size: 22px;">Kaaval Assurance</h3>
    <p style="font-size: 16px; margin-bottom: 0;">
      Focus on <strong>measuring</strong> contract conformance <em>after</em> generation. Built for transactional, policy-bound AI decisions and automated compliance.
    </p>
  </div>
</div>
