---
marp: true
theme: default
class: y-combinator
style: |
  section {
    background-color: #FFFFFF;
    color: #111827;
    font-family: 'Inter', -apple-system, sans-serif;
    padding: 60px;
  }
  h1 {
    color: #111827;
    font-size: 52px;
    font-weight: 800;
    margin-bottom: 10px;
    letter-spacing: -1.5px;
  }
  h2 {
    color: #FF6600; /* YC Orange */
    font-size: 38px;
    margin-top: 0;
    margin-bottom: 20px;
    font-weight: 800;
    letter-spacing: -1px;
  }
  h3 {
    color: #111827;
    font-size: 22px;
    font-weight: 700;
    margin-top: 0;
  }
  p {
    font-size: 20px;
    color: #4B5563;
    line-height: 1.6;
  }
  strong {
    color: #111827;
  }
  .highlight {
    color: #FF6600;
  }
  .big-num {
    font-size: 72px;
    font-weight: 800;
    color: #FF6600;
    line-height: 1;
    margin-bottom: 5px;
  }
  .stat-card {
    background: #F9FAFB;
    border: 1px solid #E5E7EB;
    border-radius: 12px;
    padding: 24px;
    text-align: center;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
  }
---

# Kaaval Assurance

<div style="display: grid; grid-template-columns: 1.2fr 1fr; gap: 40px; align-items: center; height: 80%;">
  <div>
    <h2>Routers predict.<br/>Kaaval verifies.</h2>
    <p>An inference assurance plane for open-weight models on AMD compute.</p>
    <div style="margin-top: 30px; font-size: 16px; font-family: monospace; color: #FF6600; font-weight: bold;">
      Verify, not predict. Receipts, not promises.
    </div>
  </div>
  <div>
    <img src="assets/slide1-hero.png" style="width: 100%; max-height: 380px; object-fit: contain; border-radius: 12px; border: 1px solid #E5E7EB; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);" />
  </div>
</div>

---

## AI Decisions are Liabilities.

<div style="display: grid; grid-template-columns: 1.2fr 1fr; gap: 40px; align-items: center; height: 80%;">
  <div>
    <p style="font-size: 24px; color: #111827; font-weight: 600; line-height: 1.4;">
      Unverified local models approve unauthorized refunds, create exposure, and fail silently.
    </p>
    <p style="margin-top: 20px;">
      Standard guardrails check syntax; they cannot verify business logic. As agents handle transactions, quality drift translates directly into financial risk.
    </p>
  </div>
  <div>
    <img src="assets/slide2-problem.png" style="width: 100%; max-height: 380px; object-fit: contain; border-radius: 12px; border: 1px solid #E5E7EB; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);" />
  </div>
</div>

---

## Gate. Verify. Escalate.

<div style="display: grid; grid-template-columns: 1.2fr 1fr; gap: 40px; align-items: center; height: 80%;">
  <div>
    <p style="font-size: 24px; color: #111827; font-weight: 600; line-height: 1.4;">
      Local open-weight inference checked by code contracts in &lt;1ms. Only fails safe.
    </p>
    <p style="margin-top: 20px;">
      Kaaval intercepts response structures locally. If checks fail, it routes to a remote backup, saving <strong style="color: #FF6600;">88%</strong> of API costs while guaranteeing compliance.
    </p>
  </div>
  <div>
    <img src="assets/slide3-solution.png" style="width: 100%; max-height: 380px; object-fit: contain; border-radius: 12px; border: 1px solid #E5E7EB; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);" />
  </div>
</div>

---

## 3-Layer Assurance Engine

<div style="display: grid; grid-template-columns: 1fr 1.2fr; gap: 30px; align-items: center; height: 80%;">
  <div style="font-size: 16px; line-height: 1.6;">
    <div style="margin-bottom: 20px;">
      <h3 style="color: #FF6600; margin: 0; font-size: 20px;">1. Conformance Gate</h3>
      <span style="color: #4B5563;">Deterministic JSON shape, enums, & grounding checks in &lt;1ms.</span>
    </div>
    <div style="margin-bottom: 20px;">
      <h3 style="color: #111827; margin: 0; font-size: 20px;">2. Adaptive EWMA Routing</h3>
      <span style="color: #4B5563;">Tracks category failures in real-time. Pre-routes directly to remote on drift.</span>
    </div>
    <div>
      <h3 style="color: #4B5563; margin: 0; font-size: 20px;">3. Sampled Offline Audit</h3>
      <span style="color: #4B5563;">Adversarial critic challenges accepted answers with FP-calibration.</span>
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
      <div style="font-size: 11px; font-family: monospace; color: #4B5563; margin-bottom: 5px; font-weight: bold;">[ MEASURED ]</div>
      <span style="color: #111827; font-size: 15px; font-weight: 600;">Contract Conformance</span>
    </div>
    <div class="stat-card">
      <div class="big-num">88%</div>
      <div style="font-size: 11px; font-family: monospace; color: #4B5563; margin-bottom: 5px; font-weight: bold;">[ MEASURED ]</div>
      <span style="color: #111827; font-size: 15px; font-weight: 600;">API Costs Saved</span>
    </div>
    <div class="stat-card">
      <div class="big-num">0%</div>
      <div style="font-size: 11px; font-family: monospace; color: #4B5563; margin-bottom: 5px; font-weight: bold;">[ MEASURED ]</div>
      <span style="color: #111827; font-size: 15px; font-weight: 600;">Escalation Rate (Proof Run)</span>
    </div>
  </div>
  <div style="margin-top: 40px; text-align: center; font-family: monospace; font-size: 14px; color: #4B5563;">
    Hardware: <strong style="color: #111827;">AMD Radeon gfx1100 target (48GB VRAM)</strong> served via <strong style="color: #111827;">vLLM (ROCm 7.2)</strong>. <br/>
    Commit <span style="color: #111827; font-weight: bold;">aa8b5b2</span> verified with SHA-256 integrity checks.
  </div>
</div>

---

## Verify, Don't Predict.

<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 40px; align-items: start; height: 80%; margin-top: 30px;">
  <div style="background: #FFF5F5; border: 1px solid #FED7D7; border-radius: 12px; padding: 25px;">
    <h3 style="color: #C53030; margin-top: 0; font-size: 22px;">Traditional Routers</h3>
    <p style="font-size: 16px; margin-bottom: 0; color: #742A2A;">
      Focus on <strong>guessing</strong> model quality <em>before</em> generation. Works for content writing, but fails when business contracts cannot tolerate errors.
    </p>
  </div>
  <div style="background: #F0FDF4; border: 1px solid #DCFCE7; border-radius: 12px; padding: 25px;">
    <h3 style="color: #15803D; margin-top: 0; font-size: 22px;">Kaaval Assurance</h3>
    <p style="font-size: 16px; margin-bottom: 0; color: #166534;">
      Focus on <strong>measuring</strong> contract conformance <em>after</em> generation. Built for transactional, policy-bound AI decisions and automated compliance.
    </p>
  </div>
</div>
