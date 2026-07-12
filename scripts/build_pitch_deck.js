// Kaaval Assurance pitch deck — regenerated from verified content only.
// No stock/generated imagery; every number traces to something checked
// this session (pytest, docker manifest inspect, WebSearch on Moffatt v.
// Air Canada, or the committed telemetry artifacts). Native vector shapes
// throughout so nothing can render cut off.

const pptxgen = require("pptxgenjs");

const C = {
  bg: "FFFFFF",
  ink: "111827",
  body: "4B5563",
  accent: "FF6600",
  cardBg: "F9FAFB",
  cardBorder: "E5E7EB",
  measured: "15803D",
  measuredBg: "F0FDF4",
  measuredBorder: "BBF7D0",
  configured: "B45309",
  configuredBg: "FFFBEB",
  configuredBorder: "FDE68A",
  danger: "C53030",
  dangerBg: "FFF5F5",
  dangerBorder: "FED7D7",
  navy: "1E2761",
};

const FONT = "Arial";

function newDeck() {
  const p = new pptxgen();
  p.layout = "LAYOUT_WIDE"; // 13.3" x 7.5"
  p.defineSlideMaster({
    title: "BASE",
    background: { color: C.bg },
  });
  return p;
}

function addKicker(slide, text) {
  slide.addText(text.toUpperCase(), {
    x: 0.5, y: 0.35, w: 8, h: 0.35,
    fontFace: FONT, fontSize: 12, bold: true, color: C.accent,
    charSpacing: 2, margin: 0,
  });
}

function addTitle(slide, text, y = 0.7) {
  slide.addText(text, {
    x: 0.5, y, w: 12.3, h: 0.9,
    fontFace: FONT, fontSize: 32, bold: true, color: C.ink,
    margin: 0,
  });
}

function tag(slide, x, y, label, kind) {
  const map = {
    measured: [C.measuredBg, C.measuredBorder, C.measured],
    configured: [C.configuredBg, C.configuredBorder, C.configured],
  };
  const [bg, border, fg] = map[kind];
  slide.addShape("roundRect", {
    x, y, w: 1.15, h: 0.28, rectRadius: 0.06,
    fill: { color: bg }, line: { color: border, width: 0.75 },
  });
  slide.addText(label, {
    x, y, w: 1.15, h: 0.28,
    fontFace: FONT, fontSize: 8, bold: true, color: fg,
    align: "center", valign: "middle", charSpacing: 1, margin: 0,
  });
}

const deck = newDeck();

// ---------- Slide 1: Title ----------
{
  const s = deck.addSlide({ masterName: "BASE" });
  s.addShape("roundRect", {
    x: 0.5, y: 0.5, w: 2.6, h: 0.4, rectRadius: 0.08,
    fill: { color: C.bg }, line: { color: C.accent, width: 1.25 },
  });
  s.addText("AMD ACT II · TRACK 3", {
    x: 0.5, y: 0.5, w: 2.6, h: 0.4,
    fontFace: FONT, fontSize: 10, bold: true, color: C.accent,
    align: "center", valign: "middle", charSpacing: 1, margin: 0,
  });

  s.addText("Kaaval Assurance", {
    x: 0.5, y: 1.5, w: 8, h: 1,
    fontFace: FONT, fontSize: 44, bold: true, color: C.ink, margin: 0,
  });
  s.addText([
    { text: "Routers predict.\n", options: { color: C.accent, bold: true, fontSize: 28 } },
    { text: "Kaaval verifies.", options: { color: C.accent, bold: true, fontSize: 28 } },
  ], { x: 0.5, y: 2.6, w: 7, h: 1.1, fontFace: FONT, lineSpacingMultiple: 1.1, margin: 0 });
  s.addText("An assurance layer for AI decisions — checked locally on AMD compute\nbefore anyone downstream sees the answer.", {
    x: 0.5, y: 3.85, w: 7.2, h: 0.9,
    fontFace: FONT, fontSize: 15, color: C.body, lineSpacingMultiple: 1.3, margin: 0,
  });
  s.addText("VERIFY, NOT PREDICT. RECEIPTS, NOT PROMISES.", {
    x: 0.5, y: 4.85, w: 7, h: 0.4,
    fontFace: "Courier New", fontSize: 12, bold: true, color: C.accent, charSpacing: 1, margin: 0,
  });

  // Right panel: real product facts, native — replaces generic stock hero.
  const px = 8.3, pw = 4.5;
  s.addShape("roundRect", {
    x: px, y: 1.5, w: pw, h: 4.3, rectRadius: 0.12,
    fill: { color: C.navy }, line: { color: C.navy, width: 1 },
    shadow: { type: "outer", color: "000000", opacity: 0.15, blur: 12, offset: 4, angle: 90 },
  });
  s.addText("ONE PUBLIC CONTAINER", {
    x: px, y: 1.75, w: pw, h: 0.35,
    fontFace: FONT, fontSize: 11, bold: true, color: "7DD3FC",
    align: "center", charSpacing: 1.5, margin: 0,
  });
  s.addText("AMD\n+ Gemma\n+ ROCm / vLLM", {
    x: px, y: 2.3, w: pw, h: 1.5,
    fontFace: FONT, fontSize: 24, bold: true, color: "FFFFFF",
    align: "center", lineSpacingMultiple: 1.25, margin: 0,
  });
  s.addShape("line", {
    x: px + 0.6, y: 3.9, w: pw - 1.2, h: 0,
    line: { color: "FFFFFF", width: 0.5, transparency: 75 },
  });
  s.addText("Evidence Baseline — no credentials\nLive Session — BYOK when needed", {
    x: px + 0.3, y: 4.1, w: pw - 0.6, h: 0.7,
    fontFace: FONT, fontSize: 12, color: "CBD5E1",
    align: "center", lineSpacingMultiple: 1.3, margin: 0,
  });
  s.addShape("roundRect", {
    x: px + 0.6, y: 5.0, w: pw - 1.2, h: 0.5, rectRadius: 0.25,
    fill: { color: "064E3B" }, line: { color: "34D399", width: 1 },
  });
  s.addText("RECEIPTS, NOT PROMISES", {
    x: px + 0.6, y: 5.0, w: pw - 1.2, h: 0.5,
    fontFace: FONT, fontSize: 10, bold: true, color: "6EE7B7",
    align: "center", valign: "middle", charSpacing: 1, margin: 0,
  });

  s.addText("KaavalAI · AMD GPU · Gemma 3 · Fireworks AI", {
    x: 0.5, y: 6.7, w: 8, h: 0.3,
    fontFace: FONT, fontSize: 11, bold: true, color: C.ink, margin: 0,
  });
  s.addShape("line", { x: 0.5, y: 7.05, w: 12.3, h: 0, line: { color: C.cardBorder, width: 0.75 } });
  s.addText("github.com/kaaval-ai/kaaval-assurance", {
    x: 0.5, y: 7.1, w: 6, h: 0.3, fontFace: FONT, fontSize: 10, color: C.body, margin: 0,
  });
  s.addText("01", { x: 12.3, y: 7.1, w: 0.5, h: 0.3, fontFace: FONT, fontSize: 10, color: C.body, align: "right", margin: 0 });
}

// ---------- Slide 2: The problem — a real, litigated case, not stock art ----------
{
  const s = deck.addSlide({ masterName: "BASE" });
  addKicker(s, "The accountability gap is not hypothetical");
  addTitle(s, "A tribunal already rejected “the AI is separate.”");
  s.addText("Moffatt v. Air Canada, BC Civil Resolution Tribunal, Feb 2024 — a real ruling, not a projection.", {
    x: 0.5, y: 1.55, w: 12, h: 0.4, fontFace: FONT, fontSize: 14, color: C.body, margin: 0,
  });

  // Two-column: the case (left), the mapped lesson (right)
  s.addShape("roundRect", {
    x: 0.5, y: 2.15, w: 6.0, h: 4.5, rectRadius: 0.1,
    fill: { color: C.dangerBg }, line: { color: C.dangerBorder, width: 1 },
  });
  s.addText("WHAT HAPPENED", { x: 0.85, y: 2.4, w: 5.3, h: 0.3, fontFace: FONT, fontSize: 11, bold: true, color: C.danger, charSpacing: 1, margin: 0 });
  s.addText([
    { text: "Air Canada's chatbot told a customer he could book at full fare and claim a bereavement discount ", options: {} },
    { text: "after", options: { italic: true } },
    { text: " travel. The real policy required the request ", options: {} },
    { text: "before", options: { italic: true } },
    { text: " travel — the chatbot's answer was fluent, confident, and wrong.\n\n", options: {} },
    { text: "Air Canada argued the chatbot was “a separate legal entity responsible for its own actions.” The tribunal rejected that outright and held the airline liable: $812 CAD.", options: {} },
  ], { x: 0.85, y: 2.8, w: 5.3, h: 3.6, fontFace: FONT, fontSize: 13.5, color: "742A2A", lineSpacingMultiple: 1.35, valign: "top", margin: 0 });

  s.addShape("roundRect", {
    x: 6.8, y: 2.15, w: 6.0, h: 4.5, rectRadius: 0.1,
    fill: { color: C.measuredBg }, line: { color: C.measuredBorder, width: 1 },
  });
  s.addText("THE PATTERN KAAVAL GATES", { x: 7.15, y: 2.4, w: 5.3, h: 0.3, fontFace: FONT, fontSize: 11, bold: true, color: C.measured, charSpacing: 1, margin: 0 });
  s.addText([
    { text: "The correct answer wasn't unknowable — it was sitting in a linked policy page in the same conversation. A fluent model still produced the wrong one.\n\n", options: {} },
    { text: "This is exactly the shape of failure a deterministic contract check catches: not “is this text safe,” but ", options: {} },
    { text: "“does this claim match the policy on file.”", options: { bold: true } },
  ], { x: 7.15, y: 2.8, w: 5.3, h: 3.6, fontFace: FONT, fontSize: 13.5, color: "166534", lineSpacingMultiple: 1.35, valign: "top", margin: 0 });

  s.addText("Source: BC Civil Resolution Tribunal ruling, Moffatt v. Air Canada (Feb 2024) · publicly reported", {
    x: 0.5, y: 6.95, w: 12, h: 0.3, fontFace: FONT, fontSize: 10, italic: true, color: C.body, margin: 0,
  });
  s.addText("02", { x: 12.3, y: 7.1, w: 0.5, h: 0.3, fontFace: FONT, fontSize: 10, color: C.body, align: "right", margin: 0 });
}

// ---------- Slide 3: The solution — concrete walkthrough, real check ID ----------
{
  const s = deck.addSlide({ masterName: "BASE" });
  addKicker(s, "The product");
  addTitle(s, "Same shape of failure, caught before it ships.");
  s.addText("A real contract from this repo: support.refund_decision — the $500 cap is a range check, not a prompt.", {
    x: 0.5, y: 1.55, w: 12, h: 0.4, fontFace: FONT, fontSize: 14, color: C.body, margin: 0,
  });

  const cols = [
    { x: 0.5, tagText: "STRUGGLE", tagFg: C.danger, tagBg: C.dangerBg, tagBorder: C.dangerBorder,
      h3: "Local candidate", stat: "Refund approved", statColor: C.danger,
      body: "The output is valid JSON and sounds helpful — but the purchase was 11 months ago, outside the 30-day window." },
    { x: 4.53, tagText: "CATCH", tagFg: C.configured, tagBg: C.configuredBg, tagBorder: C.configuredBorder,
      h3: "Deterministic rule", stat: "outside_refund_window\n_requires_denial", statColor: C.configured, mono: true,
      body: "Layer 1 rejects with a stable check ID. No model is asked to judge another model inline." },
    { x: 8.56, tagText: "RESCUE", tagFg: C.measured, tagBg: C.measuredBg, tagBorder: C.measuredBorder,
      h3: "Same gate, next tier", stat: "Escalate or deny", statColor: C.measured,
      body: "Every attempt is retained as a replayable receipt: provider, cost, latency, route, and which checks ran." },
  ];
  const cw = 3.85, cy = 2.2, ch = 3.9;
  cols.forEach((col) => {
    s.addShape("roundRect", {
      x: col.x, y: cy, w: cw, h: ch, rectRadius: 0.1,
      fill: { color: C.cardBg }, line: { color: C.cardBorder, width: 1 },
    });
    s.addShape("roundRect", {
      x: col.x + 0.3, y: cy + 0.3, w: 1.5, h: 0.35, rectRadius: 0.17,
      fill: { color: col.tagBg }, line: { color: col.tagBorder, width: 1 },
    });
    s.addText(col.tagText, {
      x: col.x + 0.3, y: cy + 0.3, w: 1.5, h: 0.35,
      fontFace: FONT, fontSize: 10, bold: true, color: col.tagFg,
      align: "center", valign: "middle", charSpacing: 1, margin: 0,
    });
    s.addText(col.h3, {
      x: col.x + 0.3, y: cy + 0.85, w: cw - 0.6, h: 0.35,
      fontFace: FONT, fontSize: 14, bold: true, color: C.ink, margin: 0,
    });
    s.addText(col.stat, {
      x: col.x + 0.3, y: cy + 1.25, w: cw - 0.6, h: col.mono ? 0.85 : 0.5,
      fontFace: col.mono ? "Courier New" : FONT, fontSize: col.mono ? 15 : 19, bold: true,
      color: col.statColor, lineSpacingMultiple: 1.15, margin: 0,
    });
    s.addText(col.body, {
      x: col.x + 0.3, y: cy + (col.mono ? 2.2 : 1.9), w: cw - 0.6, h: ch - (col.mono ? 2.2 : 1.9) - 0.25,
      fontFace: FONT, fontSize: 12, color: C.body, lineSpacingMultiple: 1.3, valign: "top", margin: 0,
    });
  });
  // Arrows between cards
  s.addText("→", { x: 4.15, y: 3.9, w: 0.4, h: 0.5, fontFace: FONT, fontSize: 22, bold: true, color: C.accent, align: "center", margin: 0 });
  s.addText("→", { x: 8.18, y: 3.9, w: 0.4, h: 0.5, fontFace: FONT, fontSize: 22, bold: true, color: C.accent, align: "center", margin: 0 });

  // The distinction a technical judge will actually be checking for:
  // this reads as a content filter unless stated plainly that it isn't.
  s.addShape("roundRect", {
    x: 0.5, y: 6.28, w: 12.3, h: 0.55, rectRadius: 0.08,
    fill: { color: C.navy }, line: { color: C.navy, width: 0 },
  });
  s.addText([
    { text: "Not a content filter.  ", options: { bold: true, color: "FFFFFF" } },
    { text: "A guardrail blocks bad text. Kaaval decides which model answers — and proves what it cost.", options: { color: "CBD5E1" } },
  ], {
    x: 0.8, y: 6.28, w: 11.7, h: 0.55, fontFace: FONT, fontSize: 12.5,
    valign: "middle", lineSpacingMultiple: 1.15, margin: 0, wrap: false,
  });

  s.addText("Synthetic hard case · support.refund_decision · deterministic grounding rule (src/kaaval_assurance/contracts/support.py)", {
    x: 0.5, y: 6.95, w: 12, h: 0.3, fontFace: FONT, fontSize: 10, italic: true, color: C.body, margin: 0,
  });
  s.addText("03", { x: 12.3, y: 7.1, w: 0.5, h: 0.3, fontFace: FONT, fontSize: 10, color: C.body, align: "right", margin: 0 });
}

// ---------- Slide 4: 3-layer engine, native architecture diagram ----------
{
  const s = deck.addSlide({ masterName: "BASE" });
  addKicker(s, "The product");
  addTitle(s, "One gate turns model traffic into governed decisions.");
  s.addText("The request path stays deterministic; deeper audit remains sampled and offline.", {
    x: 0.5, y: 1.55, w: 12, h: 0.4, fontFace: FONT, fontSize: 14, color: C.body, margin: 0,
  });

  const layers = [
    { n: "1", t: "Conformance Gate", d: "Deterministic JSON shape, enums, ranges, and grounding checks. Pure code — no model judges another model inline.", c: C.accent },
    { n: "2", t: "Adaptive EWMA Routing", d: "Tracks per-category contract-failure drift in real time; tightens or pre-routes to remote when a category keeps failing.", c: C.ink },
    { n: "3", t: "Sampled Offline Audit", d: "FP-calibrated challenger samples accepted answers. Display-only — two-sided calibration and audit-to-routing are roadmap work, not shipped.", c: C.body },
  ];
  let ly = 2.15;
  layers.forEach((l) => {
    s.addShape("roundRect", {
      x: 0.5, y: ly, w: 0.5, h: 0.5, rectRadius: 0.25,
      fill: { color: l.c }, line: { color: l.c, width: 0 },
    });
    s.addText(l.n, { x: 0.5, y: ly, w: 0.5, h: 0.5, fontFace: FONT, fontSize: 16, bold: true, color: "FFFFFF", align: "center", valign: "middle", margin: 0 });
    s.addText(l.t, { x: 1.15, y: ly - 0.03, w: 5, h: 0.4, fontFace: FONT, fontSize: 15, bold: true, color: C.ink, margin: 0 });
    s.addText(l.d, { x: 1.15, y: ly + 0.38, w: 5.15, h: 0.75, fontFace: FONT, fontSize: 11.5, color: C.body, lineSpacingMultiple: 1.25, valign: "top", margin: 0 });
    ly += 1.28;
  });

  // Native pipeline diagram, right side — fixed box, cannot overflow.
  const dx = 6.7, dy = 2.15, dw = 6.1, dh = 4.5;
  s.addShape("roundRect", {
    x: dx, y: dy, w: dw, h: dh, rectRadius: 0.1,
    fill: { color: "0B1220" }, line: { color: "1F2937", width: 1 },
  });
  s.addText("INFERENCE ASSURANCE FLOW", {
    x: dx, y: dy + 0.25, w: dw, h: 0.35, fontFace: FONT, fontSize: 13, bold: true, color: "FBBF24",
    align: "center", charSpacing: 1, margin: 0,
  });

  // Linear row (Task Input -> Provider Router -> Layer 1 Verifier) plus one
  // escalation branch directly below Layer 1 Verifier. Every arrow is
  // axis-aligned between two node edges - no diagonals, nothing can cross
  // through a box.
  const rowY = dy + 1.1, rowH = 0.85, rowMidY = rowY + rowH / 2;
  const nodes = [
    { x: dx + 0.35, y: rowY, w: 1.5, h: rowH, t: "Task Input", sub: "refund request", c: "38BDF8" },
    { x: dx + 2.15, y: rowY, w: 1.7, h: rowH, t: "Provider Router", sub: "tier policy", c: "38BDF8" },
    { x: dx + 4.15, y: rowY, w: 1.7, h: rowH, t: "Layer 1 Verifier", sub: "contract checks", c: "38BDF8" },
    { x: dx + 4.15, y: rowY + 1.5, w: 1.7, h: rowH, t: "Fireworks Tier", sub: "escalation, re-verified", c: "FBBF24" },
  ];
  nodes.forEach((n) => {
    s.addShape("roundRect", {
      x: n.x, y: n.y, w: n.w, h: n.h, rectRadius: 0.08,
      fill: { color: "111827" }, line: { color: n.c, width: 1.25 },
    });
    s.addText(n.t, { x: n.x, y: n.y + 0.14, w: n.w, h: 0.35, fontFace: FONT, fontSize: 11, bold: true, color: "FFFFFF", align: "center", lineSpacingMultiple: 1, margin: 0 });
    s.addText(n.sub, { x: n.x + 0.08, y: n.y + 0.52, w: n.w - 0.16, h: 0.28, fontFace: FONT, fontSize: 8, color: "9CA3AF", align: "center", margin: 0 });
  });
  const arrow = (x1, y1, x2, y2, color) => s.addShape("line", {
    x: Math.min(x1, x2), y: Math.min(y1, y2), w: Math.abs(x2 - x1), h: Math.abs(y2 - y1),
    line: { color, width: 1.5, endArrowType: "triangle" },
    flipV: y2 < y1,
  });
  // Task Input -> Provider Router (edge to edge)
  arrow(dx + 1.85, rowMidY, dx + 2.15, rowMidY, "38BDF8");
  // Provider Router -> Layer 1 Verifier (edge to edge)
  arrow(dx + 3.85, rowMidY, dx + 4.15, rowMidY, "38BDF8");
  // Layer 1 Verifier -> Fireworks Tier (down, left side of the shared column)
  arrow(dx + 4.55, rowY + rowH, dx + 4.55, rowY + 1.5, "FBBF24");
  // Fireworks Tier -> Layer 1 Verifier (up, right side - offset so arrows never touch)
  arrow(dx + 5.4, rowY + 1.5, dx + 5.4, rowY + rowH, "FBBF24");
  s.addText("fail →", { x: dx + 4.15, y: rowY + rowH + 0.08, w: 0.65, h: 0.22, fontFace: FONT, fontSize: 7.5, color: "FBBF24", align: "center", margin: 0 });
  s.addText("re-verified", { x: dx + 4.95, y: rowY + rowH + 0.08, w: 0.9, h: 0.22, fontFace: FONT, fontSize: 7.5, color: "FBBF24", align: "center", margin: 0 });

  s.addText("Only Layer 1 gates acceptance. Provider errors and double failure return NO SAFE ANSWER.", {
    x: dx + 0.35, y: dy + 3.55, w: dw - 0.7, h: 0.65,
    fontFace: FONT, fontSize: 10, color: "D1D5DB", lineSpacingMultiple: 1.3, margin: 0,
  });

  s.addText("Implemented path: AssurancePipeline → Router → Verifier → TrajectoryStore", {
    x: 0.5, y: 6.95, w: 12, h: 0.3, fontFace: FONT, fontSize: 10, italic: true, color: C.body, margin: 0,
  });
  s.addText("04", { x: 12.3, y: 7.1, w: 0.5, h: 0.3, fontFace: FONT, fontSize: 10, color: C.body, align: "right", margin: 0 });
}

// ---------- Slide 5: Measured proof, correctly source-tagged ----------
{
  const s = deck.addSlide({ masterName: "BASE" });
  addKicker(s, "Evidence, separated honestly");
  addTitle(s, "AMD proves execution. Fireworks proves selective economics.");
  s.addText("Two artifacts, two claims — never blended into one result.", {
    x: 0.5, y: 1.55, w: 12, h: 0.4, fontFace: FONT, fontSize: 14, color: C.body, margin: 0,
  });

  const stats = [
    { v: "16 / 16", l: "Local Contract-Conformance", sub: "Layer 1 · 16-case eval", kind: "measured" },
    { v: "324.6 / 479.6ms", l: "Latency P50 / P95", sub: "16-case eval", kind: "measured" },
    { v: "14 / 16", l: "Remote Calls Avoided", sub: "87.5% reduction", kind: "measured" },
    { v: "$0.0333", l: "Configured Cost Avoided", sub: "88.7% reduction", kind: "configured" },
  ];
  const sw = 2.9, sx0 = 0.5, sy = 2.2, gap = 0.15;
  stats.forEach((st, i) => {
    const x = sx0 + i * (sw + gap);
    s.addShape("roundRect", {
      x, y: sy, w: sw, h: 2.0, rectRadius: 0.1,
      fill: { color: C.cardBg }, line: { color: C.cardBorder, width: 1 },
    });
    s.addText(st.v, { x, y: sy + 0.25, w: sw, h: 0.65, fontFace: FONT, fontSize: 26, bold: true, color: C.accent, align: "center", margin: 0 });
    tag(s, x + (sw - 1.15) / 2, sy + 0.95, st.kind.toUpperCase(), st.kind);
    s.addText(st.l, { x: x + 0.15, y: sy + 1.35, w: sw - 0.3, h: 0.35, fontFace: FONT, fontSize: 11, bold: true, color: C.ink, align: "center", margin: 0 });
    s.addText(st.sub, { x: x + 0.15, y: sy + 1.68, w: sw - 0.3, h: 0.28, fontFace: FONT, fontSize: 9.5, color: C.body, align: "center", margin: 0 });
  });

  s.addShape("roundRect", {
    x: 0.5, y: 4.5, w: 12.3, h: 1.9, rectRadius: 0.1,
    fill: { color: C.cardBg }, line: { color: C.cardBorder, width: 1 },
  });
  s.addText([
    { text: "AMD/ATI host · 47.98 GiB VRAM · gfx1100 target · gemma-3-1b-it via ROCm + vLLM\n", options: { bold: true, color: C.ink } },
    { text: "Exact GPU marketing name unavailable; none inferred.\n", options: { color: C.body } },
    { text: "Configured-cost figure is a price estimate from recorded token counts, not a provider invoice — tagged CONFIGURED, not MEASURED, on purpose.\n", options: { color: C.body } },
    { text: "bundle live-5be3acfa-amd-gemma-proof · checksummed", options: { bold: true, color: C.measured, fontFace: "Courier New" } },
  ], { x: 0.85, y: 4.75, w: 11.6, h: 1.4, fontFace: FONT, fontSize: 12.5, lineSpacingMultiple: 1.35, valign: "top", margin: 0 });

  s.addText("Sources: artifacts/demo-live-* · artifacts/fireworks-cost-comparison-20260711T054906Z.json", {
    x: 0.5, y: 6.95, w: 12, h: 0.3, fontFace: FONT, fontSize: 10, italic: true, color: C.body, margin: 0,
  });
  s.addText("05", { x: 12.3, y: 7.1, w: 0.5, h: 0.3, fontFace: FONT, fontSize: 10, color: C.body, align: "right", margin: 0 });
}

// ---------- Slide 6: Delivery + honest roadmap ----------
{
  const s = deck.addSlide({ masterName: "BASE" });
  addKicker(s, "Runnable delivery");
  addTitle(s, "Pull one public container. Evidence appears immediately.");
  s.addText("Connect a model endpoint only when you want live assurance.", {
    x: 0.5, y: 1.55, w: 12, h: 0.4, fontFace: FONT, fontSize: 14, color: C.body, margin: 0,
  });

  s.addShape("roundRect", { x: 0.5, y: 2.15, w: 7.3, h: 3.0, rectRadius: 0.1, fill: { color: C.cardBg }, line: { color: C.cardBorder, width: 1 } });
  s.addText("ghcr.io/kaaval-ai/kaaval-assurance:act-ii", { x: 0.85, y: 2.4, w: 6.6, h: 0.4, fontFace: "Courier New", fontSize: 15, bold: true, color: C.ink, margin: 0 });
  s.addText("linux/amd64 · publicly pullable · clean-smoke verified", { x: 0.85, y: 2.85, w: 6.6, h: 0.3, fontFace: FONT, fontSize: 11, color: C.body, margin: 0 });

  const checks = [
    "Evidence Baseline — measured AMD bundle, zero credentials",
    "Live Session — Fireworks BYOK or reachable Ollama / vLLM",
    "Safe defaults — no model download; paid remote and export closed",
    "Acceptance — 361 tests · linux/amd64 · UID 10001 (non-root)",
  ];
  let cy2 = 3.4;
  checks.forEach((c) => {
    s.addText("✓", { x: 0.85, y: cy2, w: 0.35, h: 0.35, fontFace: FONT, fontSize: 14, bold: true, color: C.measured, margin: 0 });
    s.addText(c, { x: 1.25, y: cy2, w: 6.35, h: 0.35, fontFace: FONT, fontSize: 12, color: C.ink, margin: 0 });
    cy2 += 0.42;
  });

  // Now / 30 days / Design partners
  const plan = [
    { t: "NOW", c: C.measured, bg: C.measuredBg, border: C.measuredBorder, h3: "Provider-neutral gateway", items: ["Observe decisions", "Evaluate contracts", "Produce receipts"] },
    { t: "30 DAYS", c: "1D4ED8", bg: "EFF6FF", border: "BFDBFE", h3: "Validation before expansion", items: ["Blind semantic benchmark", "Two-sided Layer 3 calibration", "TCO experiment"] },
    { t: "DESIGN PARTNERS", c: C.configured, bg: C.configuredBg, border: C.configuredBorder, h3: "Shadow-mode proof", items: ["Refunds and support", "False accept / reject rates", "Operational economics"] },
  ];
  const px2 = 8.15, pw2 = 4.65;
  const cardH = 1.25, cardStep = 1.35; // 3 cards must clear y=6.35 (closing band)
  let py = 2.15;
  plan.forEach((col) => {
    s.addShape("roundRect", { x: px2, y: py, w: pw2, h: cardH, rectRadius: 0.08, fill: { color: col.bg }, line: { color: col.border, width: 1 } });
    s.addText(col.t, { x: px2 + 0.25, y: py + 0.12, w: pw2 - 0.5, h: 0.26, fontFace: FONT, fontSize: 9.5, bold: true, color: col.c, charSpacing: 1, margin: 0 });
    s.addText(col.h3, { x: px2 + 0.25, y: py + 0.4, w: pw2 - 0.5, h: 0.28, fontFace: FONT, fontSize: 12, bold: true, color: C.ink, margin: 0 });
    s.addText(col.items.join("  ·  "), { x: px2 + 0.25, y: py + 0.7, w: pw2 - 0.5, h: 0.5, fontFace: FONT, fontSize: 9.5, color: C.body, lineSpacingMultiple: 1.2, valign: "top", margin: 0 });
    py += cardStep;
  });

  s.addShape("line", { x: 0.5, y: 6.35, w: 12.3, h: 0, line: { color: C.cardBorder, width: 0.75 } });
  s.addText("Pull one container. Inspect measured AMD evidence. Connect your endpoint when you want live assurance.", {
    x: 0.5, y: 6.45, w: 12.3, h: 0.35, fontFace: FONT, fontSize: 12.5, bold: true, color: C.ink, align: "center", margin: 0,
  });
  s.addText("Kaaval Assurance · Verify, don't predict. Receipts, not promises.", {
    x: 0.5, y: 6.78, w: 12.3, h: 0.3, fontFace: FONT, fontSize: 11, bold: true, color: C.accent, align: "center", margin: 0,
  });
  s.addText("github.com/kaaval-ai/kaaval-assurance · Track 3 — Unicorn / Open Innovation", {
    x: 0.5, y: 7.1, w: 8, h: 0.3, fontFace: FONT, fontSize: 10, color: C.body, margin: 0,
  });
  s.addText("06", { x: 12.3, y: 7.1, w: 0.5, h: 0.3, fontFace: FONT, fontSize: 10, color: C.body, align: "right", margin: 0 });
}

deck.writeFile({ fileName: "Kaaval-Assurance-Pitch-v2.pptx" }).then(() => {
  console.log("written");
});
