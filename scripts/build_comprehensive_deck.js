// Kaaval — comprehensive pitch deck (fundraising).
// Separate from build_pitch_deck.js (the hackathon deck). This one tells the
// full story: narrow, real wedge + honest vision ceiling. Every claim traces
// to docs/feature-verification.md or verified market research; platform beyond
// Assurance is staged as shipped / building / roadmap, never claimed built.

const pptxgen = require("pptxgenjs");

const C = {
  bg: "FFFFFF", ink: "111827", body: "4B5563", faint: "6B7280",
  accent: "FF6600",
  cardBg: "F9FAFB", cardBorder: "E5E7EB",
  measured: "15803D", measuredBg: "F0FDF4", measuredBorder: "BBF7D0",
  configured: "B45309", configuredBg: "FFFBEB", configuredBorder: "FDE68A",
  planned: "1D4ED8", plannedBg: "EFF6FF", plannedBorder: "BFDBFE",
  danger: "C53030", dangerBg: "FFF5F5", dangerBorder: "FED7D7",
  navy: "0B1220", navySoft: "1E2761",
};
const FONT = "Arial";
const MONO = "Courier New";

const deck = new pptxgen();
deck.layout = "LAYOUT_WIDE"; // 13.3 x 7.5
deck.defineSlideMaster({ title: "BASE", background: { color: C.bg } });

const S = () => deck.addSlide({ masterName: "BASE" });
let PAGE = 0;
function kicker(s, t){ s.addText(t.toUpperCase(), {x:0.6,y:0.4,w:11,h:0.35,fontFace:FONT,fontSize:12,bold:true,color:C.accent,charSpacing:2,margin:0}); }
function title(s, t, y=0.75){ s.addText(t, {x:0.6,y,w:12.1,h:0.95,fontFace:FONT,fontSize:31,bold:true,color:C.ink,margin:0}); }
function sub(s, t, y=1.7){ s.addText(t, {x:0.6,y,w:12.1,h:0.55,fontFace:FONT,fontSize:14.5,color:C.body,lineSpacingMultiple:1.25,margin:0}); }
// Auto-incrementing page number; any legacy numeric arg is ignored so
// inserting slides never requires renumbering the rest.
function pageno(s){ PAGE++; s.addText(String(PAGE).padStart(2,"0"), {x:12.4,y:7.06,w:0.5,h:0.3,fontFace:FONT,fontSize:10,color:C.faint,align:"right",margin:0}); }
function footer(s, t){ s.addShape("line",{x:0.6,y:7.0,w:12.1,h:0,line:{color:C.cardBorder,width:0.75}}); s.addText(t,{x:0.6,y:7.06,w:11,h:0.3,fontFace:FONT,fontSize:9.5,italic:true,color:C.faint,margin:0}); }
function statusTag(s,x,y,kind){
  const m={measured:[C.measuredBg,C.measuredBorder,C.measured,"MEASURED"],configured:[C.configuredBg,C.configuredBorder,C.configured,"CONFIGURED"],
           shipped:[C.measuredBg,C.measuredBorder,C.measured,"SHIPPED"],building:[C.plannedBg,C.plannedBorder,C.planned,"BUILDING"],roadmap:[C.configuredBg,C.configuredBorder,C.configured,"ROADMAP"]};
  const [bg,bd,fg,label]=m[kind];
  s.addShape("roundRect",{x,y,w:1.05,h:0.26,rectRadius:0.06,fill:{color:bg},line:{color:bd,width:0.75}});
  s.addText(label,{x,y,w:1.05,h:0.26,fontFace:FONT,fontSize:7.5,bold:true,color:fg,align:"center",valign:"middle",charSpacing:0.5,margin:0});
}

/* ── 1 · Title ── */
{
  const s=S();
  s.addShape("roundRect",{x:0.6,y:0.55,w:32/32*24/24*0,h:0}); // no-op keep pptxgen happy
  // mark
  s.addText("KAAVAL",{x:0.6,y:0.55,w:4,h:0.4,fontFace:FONT,fontSize:15,bold:true,color:C.ink,charSpacing:3,margin:0});
  s.addShape("roundRect",{x:9.9,y:0.55,w:3.0,h:0.4,rectRadius:0.08,fill:{color:C.bg},line:{color:C.accent,width:1.25}});
  s.addText("SYSTEM OF RECORD",{x:9.9,y:0.55,w:3.0,h:0.4,fontFace:FONT,fontSize:9,bold:true,color:C.accent,align:"center",valign:"middle",charSpacing:1,margin:0});

  s.addText("The accountability layer\nfor AI decisions.",{x:0.6,y:2.15,w:9,h:1.9,fontFace:FONT,fontSize:44,bold:true,color:C.ink,lineSpacingMultiple:1.08,margin:0});
  s.addText([
    {text:"When AI stops writing text and starts ",options:{}},
    {text:"taking actions",options:{bold:true,color:C.ink}},
    {text:" — refunds, approvals, claims — every action needs a record of whether it was allowed. Kaaval is that record.",options:{}},
  ],{x:0.6,y:4.15,w:9.6,h:1.2,fontFace:FONT,fontSize:16,color:C.body,lineSpacingMultiple:1.35,margin:0});
  s.addText("VERIFY, DON'T PREDICT.  ·  RECEIPTS, NOT PROMISES.",{x:0.6,y:5.5,w:11,h:0.4,fontFace:MONO,fontSize:12,bold:true,color:C.accent,charSpacing:1,margin:0});
  footer(s,"KaavalAI · Milind Gunjan & Hari Krishna Govindarajan · github.com/kaaval-ai · kaaval.ai");
  pageno(s);
}

/* ── Mission (aspiration up front) ── */
{
  const s=S();
  kicker(s,"Our mission");
  s.addText("Make every AI decision\naccountable.",{x:0.6,y:1.75,w:12.1,h:1.8,fontFace:FONT,fontSize:42,bold:true,color:C.ink,lineSpacingMultiple:1.08,margin:0});
  s.addText([
    {text:"Autonomous AI will run more of the economy every year — approving, deciding, and acting with no human in the loop. It can only be trusted with that power if every decision it makes is ",options:{}},
    {text:"provable, recoverable, and on the record.",options:{bold:true,color:C.ink}},
    {text:"  We are building that record. Kaaval is the trust layer for the agentic economy.",options:{}},
  ],{x:0.6,y:3.85,w:11.6,h:1.5,fontFace:FONT,fontSize:16.5,color:C.body,lineSpacingMultiple:1.4,margin:0});
  s.addShape("roundRect",{x:0.6,y:5.5,w:12.1,h:0.85,rectRadius:0.08,fill:{color:C.cardBg},line:{color:C.cardBorder,width:1}});
  s.addText([
    {text:"Every system society learned to trust got an accountability primitive first — ",options:{color:C.body}},
    {text:"commerce got the ledger, the web got the certificate.",options:{bold:true,color:C.ink}},
    {text:"  Agentic AI gets the receipt.",options:{bold:true,color:C.accent}},
  ],{x:0.95,y:5.5,w:11.4,h:0.85,fontFace:FONT,fontSize:14,valign:"middle",lineSpacingMultiple:1.25,margin:0});
  pageno(s);
}

/* ── The shift ── */
{
  const s=S();
  kicker(s,"The shift");
  title(s,"AI is moving from writing text to taking actions.");
  sub(s,"The last wave answered questions. This wave makes decisions — and a decision, unlike a sentence, has consequences the moment it ships.");
  const cols=[
    {t:"YESTERDAY",c:C.faint,h:"AI wrote text",d:"Summaries, drafts, chat. A wrong answer was an inconvenience — a human read it first."},
    {t:"TODAY",c:C.accent,h:"AI makes decisions",d:"Approve a refund, route a claim, classify an incident, execute a tool call. The output IS the action."},
    {t:"THE GAP",c:C.danger,h:"No one is watching the decision",d:"Monitoring shows latency and tokens. It cannot answer: did this decision cross the policy it was allowed to make?"},
  ];
  const w=3.9,y=2.5,h=3.6;
  cols.forEach((col,i)=>{
    const x=0.6+i*(w+0.18);
    s.addShape("roundRect",{x,y,w,h,rectRadius:0.1,fill:{color:i===2?C.dangerBg:C.cardBg},line:{color:i===2?C.dangerBorder:C.cardBorder,width:1}});
    s.addText(col.t,{x:x+0.3,y:y+0.3,w:w-0.6,h:0.3,fontFace:FONT,fontSize:10.5,bold:true,color:col.c,charSpacing:1,margin:0});
    s.addText(col.h,{x:x+0.3,y:y+0.72,w:w-0.6,h:0.5,fontFace:FONT,fontSize:18,bold:true,color:C.ink,margin:0});
    s.addText(col.d,{x:x+0.3,y:y+1.55,w:w-0.6,h:1.8,fontFace:FONT,fontSize:13,color:C.body,lineSpacingMultiple:1.35,valign:"top",margin:0});
    if(i<2) s.addText("→",{x:x+w-0.02,y:y+h/2-0.3,w:0.2,h:0.6,fontFace:FONT,fontSize:20,bold:true,color:C.accent,align:"center",margin:0});
  });
  pageno(s,"02");
}

/* ── 3 · The problem (Air Canada) ── */
{
  const s=S();
  kicker(s,"The problem is already litigated");
  title(s,"A tribunal held a company liable for its AI's decision.");
  sub(s,"Moffatt v. Air Canada, 2024 — the chatbot invented a refund policy. The airline argued the AI was a separate entity. The tribunal rejected that.");
  s.addShape("roundRect",{x:0.6,y:2.5,w:6.0,h:3.7,rectRadius:0.1,fill:{color:C.dangerBg},line:{color:C.dangerBorder,width:1}});
  s.addText("WHAT HAPPENED",{x:0.95,y:2.75,w:5.3,h:0.3,fontFace:FONT,fontSize:11,bold:true,color:C.danger,charSpacing:1,margin:0});
  s.addText("A fluent, confident, wrong answer triggered a real financial obligation before anyone checked it against policy. The company owned the outcome — and could not reconstruct why the decision was made.",{x:0.95,y:3.15,w:5.3,h:2.8,fontFace:FONT,fontSize:14,color:"742A2A",lineSpacingMultiple:1.4,valign:"top",margin:0});
  s.addShape("roundRect",{x:6.9,y:2.5,w:5.8,h:3.7,rectRadius:0.1,fill:{color:C.measuredBg},line:{color:C.measuredBorder,width:1}});
  s.addText("THE PATTERN, EVERYWHERE",{x:7.25,y:2.75,w:5.1,h:0.3,fontFace:FONT,fontSize:11,bold:true,color:C.measured,charSpacing:1,margin:0});
  s.addText([
    {text:"This is not an edge case — it is the default risk of every AI decision that acts before it is checked. ",options:{}},
    {text:"The correct answer was knowable; the model produced the wrong one and it shipped.\n\n",options:{}},
    {text:"That is the gap Kaaval closes: not “is this text safe,” but “did this decision match the policy on file — and can you prove it later.”",options:{bold:true}},
  ],{x:7.25,y:3.15,w:5.1,h:2.8,fontFace:FONT,fontSize:14,color:"166534",lineSpacingMultiple:1.35,valign:"top",margin:0});
  footer(s,"Source: BC Civil Resolution Tribunal, Moffatt v. Air Canada (Feb 2024) · publicly reported");
  pageno(s,"03");
}

/* ── 4 · Why now ── */
{
  const s=S();
  kicker(s,"Why now");
  title(s,"Three forces are converging on this exact moment.");
  const items=[
    {n:"01",h:"Agents are taking real actions",d:"Frameworks now let AI execute tools, move money, and change records autonomously. The blast radius of a wrong decision just went up."},
    {n:"02",h:"Regulation makes it mandatory",d:"The EU AI Act's high-risk record-keeping obligations take effect Aug 2, 2026. Penalties reach €15M or 3% of global turnover. Deployers stay liable even for vendor AI."},
    {n:"03",h:"Adoption raced ahead of trust",d:"88% of contact centers already run AI; only ~25% trust it unattended. Everyone deployed. Almost no one governs."},
  ];
  let y=2.1;
  items.forEach((it)=>{
    s.addText(it.n,{x:0.6,y,w:0.9,h:0.7,fontFace:MONO,fontSize:26,bold:true,color:C.accent,margin:0});
    s.addText(it.h,{x:1.7,y:y+0.02,w:10.9,h:0.4,fontFace:FONT,fontSize:17,bold:true,color:C.ink,margin:0});
    s.addText(it.d,{x:1.7,y:y+0.46,w:10.9,h:0.75,fontFace:FONT,fontSize:13,color:C.body,lineSpacingMultiple:1.25,valign:"top",margin:0});
    y+=1.28;
  });
  // Category confirmation band — Gartner named the category in Feb 2026.
  s.addShape("roundRect",{x:0.6,y:6.05,w:12.1,h:0.72,rectRadius:0.08,fill:{color:C.measuredBg},line:{color:C.measuredBorder,width:1}});
  s.addText([
    {text:"Gartner named the category: ",options:{color:C.body}},
    {text:"“Guardian Agents” — runtime enforcement for agentic AI (Feb 2026). ",options:{bold:true,color:C.measured}},
    {text:"AI TRiSM: $3.1B → $13.8B by 2030 · 95% of C-suites report AI incidents · ungoverned incidents average $4.4M.",options:{bold:true,color:C.ink}},
  ],{x:0.95,y:6.05,w:11.4,h:0.72,fontFace:FONT,fontSize:11.5,valign:"middle",lineSpacingMultiple:1.2,margin:0});
  footer(s,"Sources: EU AI Act Art. 12/19 (artificialintelligenceact.eu) · Gartner AI TRiSM Market Guide + Guardian Agents Market Guide (Feb 2026) · market reports 2026");
  pageno(s,"04");
}

/* ── 5 · What Kaaval is ── */
{
  const s=S();
  kicker(s,"What Kaaval is");
  title(s,"The acceptance layer between a model answer and a real action.");
  sub(s,"Every consequential AI decision gets three things it does not have today: a contract, a recovery path, and a replayable receipt.");
  // three things
  const three=[
    {h:"A contract",d:"An explicit, versioned rule for the task — checked in code, not asked in a prompt. The $500 cap is a range check, not a suggestion."},
    {h:"A recovery path",d:"A failed decision escalates once to a stronger model on the identical contract, or fails closed. It never ships nonconformant."},
    {h:"A receipt",d:"Every decision is a redacted, replayable record — contract, checks, cost, provenance. Reconstructable later with zero model calls."},
  ];
  const w=3.9,y=2.55,h=2.5;
  three.forEach((t,i)=>{const x=0.6+i*(w+0.18);
    s.addShape("roundRect",{x,y,w,h,rectRadius:0.1,fill:{color:C.cardBg},line:{color:C.cardBorder,width:1}});
    s.addText(t.h,{x:x+0.28,y:y+0.28,w:w-0.56,h:0.4,fontFace:FONT,fontSize:16,bold:true,color:C.accent,margin:0});
    s.addText(t.d,{x:x+0.28,y:y+0.85,w:w-0.56,h:1.5,fontFace:FONT,fontSize:12.5,color:C.body,lineSpacingMultiple:1.3,valign:"top",margin:0});
  });
  // what it is NOT — the positioning band
  s.addShape("roundRect",{x:0.6,y:5.35,w:12.1,h:1.0,rectRadius:0.08,fill:{color:C.navy}});
  s.addText([
    {text:"Not a content filter",options:{bold:true,color:"FFFFFF"}},
    {text:" (that screens words).  ",options:{color:"CBD5E1"}},
    {text:"Not a gateway",options:{bold:true,color:"FFFFFF"}},
    {text:" (that routes traffic).  ",options:{color:"CBD5E1"}},
    {text:"Not an eval tool",options:{bold:true,color:"FFFFFF"}},
    {text:" (that tests offline). Kaaval governs the live decision and proves it.",options:{color:"CBD5E1"}},
  ],{x:0.95,y:5.35,w:11.4,h:1.0,fontFace:FONT,fontSize:13.5,valign:"middle",lineSpacingMultiple:1.25,margin:0});
  pageno(s,"05");
}

/* ── 6 · How it works ── */
{
  const s=S();
  kicker(s,"How it works");
  title(s,"Any model in. One governed decision out.");
  sub(s,"The request path is deterministic. No model is ever asked to judge another model.");
  const nodes=[
    {x:0.6,t:"ANY MODEL",sub:"GPT-5.6 · Gemma · Claude · local",c:C.faint},
    {x:3.75,t:"CONTRACT CHECK",sub:"deterministic, in code · fails closed",c:C.accent,hero:true},
    {x:6.9,t:"FOUR OUTCOMES",sub:"conform · recover · withhold · provider-fail",c:C.ink},
    {x:10.05,t:"RECEIPT",sub:"replayable · redacted · audit-ready",c:C.measured},
  ];
  const y=2.6,h=2.0,w=2.65;
  nodes.forEach((n,i)=>{
    s.addShape("roundRect",{x:n.x,y,w,h,rectRadius:0.1,fill:{color:n.hero?C.configuredBg:C.cardBg},line:{color:n.hero?C.accent:C.cardBorder,width:n.hero?1.5:1}});
    s.addText(n.t,{x:n.x,y:y+0.45,w,h:0.4,fontFace:FONT,fontSize:14,bold:true,color:C.ink,align:"center",margin:0});
    s.addText(n.sub,{x:n.x+0.15,y:y+0.95,w:w-0.3,h:0.7,fontFace:FONT,fontSize:10.5,color:C.body,align:"center",lineSpacingMultiple:1.2,valign:"top",margin:0});
    if(i<3) s.addText("→",{x:n.x+w,y:y+h/2-0.3,w:0.5,h:0.6,fontFace:FONT,fontSize:22,bold:true,color:C.accent,align:"center",margin:0});
  });
  // outcome legend
  s.addText([
    {text:"✓ conformant ",options:{color:C.measured,bold:true}},{text:"ships   ",options:{color:C.body}},
    {text:"↻ recovered ",options:{color:C.accent,bold:true}},{text:"re-checked, ships   ",options:{color:C.body}},
    {text:"⊘ no safe answer ",options:{color:C.configured,bold:true}},{text:"withheld   ",options:{color:C.body}},
    {text:"⚡ provider failure ",options:{color:C.danger,bold:true}},{text:"not the model's fault",options:{color:C.body}},
  ],{x:0.6,y:5.0,w:12.1,h:0.4,fontFace:FONT,fontSize:12.5,align:"center",margin:0});
  s.addText("Implemented path: AssurancePipeline → Router → Verifier → TrajectoryStore.  Layer-2 drift routing and a sampled, display-only Layer-3 audit sit around it.",
    {x:0.6,y:5.55,w:12.1,h:0.45,fontFace:FONT,fontSize:12,italic:true,color:C.faint,align:"center",lineSpacingMultiple:1.25,margin:0});
  s.addText([
    {text:"A 50-year-old engineering pattern, applied to AI decisions: ",options:{color:C.body,italic:true}},
    {text:"the Simplex runtime-assurance architecture — unverified controller, verified safety monitor, deterministic fallback.",options:{bold:true,color:C.ink,italic:true}},
  ],{x:0.6,y:6.15,w:12.1,h:0.5,fontFace:FONT,fontSize:12,align:"center",lineSpacingMultiple:1.25,margin:0});
  pageno(s);
}

/* ── 7 · Proof (traction) ── */
{
  const s=S();
  kicker(s,"This is built, not a deck");
  title(s,"Shipped, tested, and measured on real silicon.");
  const stats=[
    {v:"16 / 16",l:"contract-conformant on measured AMD run",k:"measured"},
    {v:"88.7%",l:"fewer premium model calls (local-first)",k:"configured"},
    {v:"400+",l:"tests · network-free · CI-clean",k:"measured"},
    {v:"1",l:"public container · SDK · terminal cockpit",k:"measured"},
  ];
  const w=2.9,y=2.5,gap=0.13;
  stats.forEach((st,i)=>{const x=0.6+i*(w+gap);
    s.addShape("roundRect",{x,y,w,h:2.0,rectRadius:0.1,fill:{color:C.cardBg},line:{color:C.cardBorder,width:1}});
    s.addText(st.v,{x,y:y+0.28,w,h:0.65,fontFace:FONT,fontSize:27,bold:true,color:C.accent,align:"center",margin:0});
    statusTag(s,x+(w-1.05)/2,y+1.0,st.k);
    s.addText(st.l,{x:x+0.2,y:y+1.38,w:w-0.4,h:0.55,fontFace:FONT,fontSize:11,bold:true,color:C.ink,align:"center",lineSpacingMultiple:1.15,margin:0});
  });
  s.addShape("roundRect",{x:0.6,y:4.75,w:12.1,h:1.55,rectRadius:0.1,fill:{color:C.cardBg},line:{color:C.cardBorder,width:1}});
  s.addText([
    {text:"Gemma 3 on AMD ROCm + vLLM, gfx1100 · checksummed evidence bundle.  ",options:{bold:true,color:C.ink}},
    {text:"Cost is a configured-price estimate from measured token counts — labeled configured, never presented as an invoice. ",options:{color:C.body}},
    {text:"We never blend measured and configured into one number. Every claim on this page maps to a stored field.",options:{color:C.body}},
  ],{x:0.95,y:5.0,w:11.4,h:1.1,fontFace:FONT,fontSize:13,lineSpacingMultiple:1.35,valign:"top",margin:0});
  footer(s,"Evidence: docs/feature-verification.md · artifacts/demo-live-* · fireworks-cost-comparison-*.json");
  pageno(s,"07");
}

/* ── 8 · Adoption ── */
{
  const s=S();
  kicker(s,"How you adopt it");
  title(s,"Zero-friction in. Never rip-and-replace.");
  sub(s,"Kaaval rides whatever you already run. Start in-process in twenty minutes; earn the request path.");
  const tiers=[
    {t:"TIER 0 · SDK",h:"@kaaval.assure",d:"One decorator on your decision function. No new infra, no network hop. Shadow or enforce. Ships today.",tag:"shipped"},
    {t:"TIER 1 · SHADOW",h:"Free diagnosis",d:"Mirror your traffic. Two weeks later: how many decisions broke your own rules, and what local-first would save. Zero risk.",tag:"shipped"},
    {t:"TIER 2 · FILTER",h:"On your gateway",d:"An assurance filter on agentgateway / Envoy / LiteLLM — not a replacement. We govern the decision; they move the packets.",tag:"building"},
  ];
  const w=3.9,y=2.6,h=3.4;
  tiers.forEach((ti,i)=>{const x=0.6+i*(w+0.18);
    s.addShape("roundRect",{x,y,w,h,rectRadius:0.1,fill:{color:C.cardBg},line:{color:C.cardBorder,width:1}});
    s.addText(ti.t,{x:x+0.28,y:y+0.28,w:w-0.56,h:0.3,fontFace:FONT,fontSize:10.5,bold:true,color:C.accent,charSpacing:1,margin:0});
    s.addText(ti.h,{x:x+0.28,y:y+0.68,w:w-0.56,h:0.4,fontFace:MONO,fontSize:16,bold:true,color:C.ink,margin:0});
    s.addText(ti.d,{x:x+0.28,y:y+1.3,w:w-0.56,h:1.6,fontFace:FONT,fontSize:12.5,color:C.body,lineSpacingMultiple:1.3,valign:"top",margin:0});
    statusTag(s,x+0.28,y+h-0.5,ti.tag);
  });
  pageno(s,"08");
}

/* ── 9 · Platform vision (the ceiling) ── */
{
  const s=S();
  kicker(s,"Where this goes");
  title(s,"Assurance is the wedge. The record is the company.");
  sub(s,"Every guardian shares one join key — the model, the version, the decision. Together they become the accountability layer for all of agentic AI.");
  const arc=[
    {h:"Assurance",d:"Governs each decision at runtime. The wedge.",tag:"shipped"},
    {h:"NanoCanary",d:"Measures how a model drifts under pressure, before release.",tag:"building"},
    {h:"Substrate",d:"Governed memory — what the agent knew, and what it ignored.",tag:"building"},
    {h:"System of record",d:"One replayable evidence chain for every AI action.",tag:"roadmap"},
  ];
  const w=2.9,y=2.6,gap=0.13,h=2.7;
  arc.forEach((a,i)=>{const x=0.6+i*(w+gap);
    const dest=i===3;
    s.addShape("roundRect",{x,y,w,h,rectRadius:0.1,fill:{color:dest?C.configuredBg:C.cardBg},line:{color:dest?C.accent:C.cardBorder,width:dest?1.5:1}});
    s.addText(a.h,{x:x+0.25,y:y+0.3,w:w-0.5,h:0.5,fontFace:FONT,fontSize:16,bold:true,color:C.ink,margin:0});
    s.addText(a.d,{x:x+0.25,y:y+0.95,w:w-0.5,h:1.2,fontFace:FONT,fontSize:12,color:C.body,lineSpacingMultiple:1.3,valign:"top",margin:0});
    statusTag(s,x+0.25,y+h-0.5,a.tag);
    if(i<3) s.addText("→",{x:x+w-0.02,y:y+h/2-0.3,w:gap+0.04,h:0.6,fontFace:FONT,fontSize:18,bold:true,color:C.accent,align:"center",margin:0});
  });
  s.addText("We claim only what ships. The platform is staged and honestly labeled — the vision is the destination, not a feature list we pretend is built.",
    {x:0.6,y:5.7,w:12.1,h:0.5,fontFace:FONT,fontSize:12,italic:true,color:C.faint,align:"center",margin:0});
  pageno(s,"09");
}

/* ── 10 · Moat ── */
{
  const s=S();
  kicker(s,"Why this is a company, not a feature");
  title(s,"The engine is copyable. What compounds is not.");
  sub(s,"A competitor can rebuild the verifier in a quarter. They cannot rebuild what only exists after you are in the decision path at volume.");
  const moats=[
    {h:"The contract library",d:"Validated, versioned rules per vertical — refunds, triage, claims, approvals. Fifty battle-tested contracts require fifty engagements to copy."},
    {h:"The evidence corpus",d:"Cross-customer false-accept / false-reject rates per contract, per model, per version. “Which models can be trusted with refund decisions” only exists if you run at scale."},
    {h:"Audit system-of-record",d:"When Kaaval receipts become a company's Article-12 evidence trail, ripping them out breaks audit continuity. Compliance formats are the stickiest lock-in in enterprise."},
    {h:"Provider-neutral by design",d:"We ride every gateway and model; we're owned by none. As the connectivity layer commoditizes, the assurance layer on top is where the value concentrates."},
  ];
  const w=5.95,y=2.55,h=1.75;
  moats.forEach((m,i)=>{const x=0.6+(i%2)*(w+0.2); const yy=y+Math.floor(i/2)*(h+0.18);
    s.addShape("roundRect",{x,y:yy,w,h,rectRadius:0.1,fill:{color:C.cardBg},line:{color:C.cardBorder,width:1}});
    s.addText(m.h,{x:x+0.28,y:yy+0.24,w:w-0.56,h:0.35,fontFace:FONT,fontSize:14.5,bold:true,color:C.accent,margin:0});
    s.addText(m.d,{x:x+0.28,y:yy+0.66,w:w-0.56,h:1.0,fontFace:FONT,fontSize:12,color:C.body,lineSpacingMultiple:1.3,valign:"top",margin:0});
  });
  pageno(s,"10");
}

/* ── 11 · Business model ── */
{
  const s=S();
  kicker(s,"Business model");
  title(s,"Open-source adoption. Metered on assured decisions.");
  sub(s,"Land free and local; monetize when local receipts must become shared organizational memory.");
  const tiers=[
    {t:"OPEN SOURCE",c:C.measured,h:"Developer",items:["Local assurance SDK + contract authoring","Local Kaaval Top cockpit","Single-node receipts and replay"],price:"Free"},
    {t:"TEAM",c:C.planned,h:"Hosted control plane",items:["Shared contracts, review queue, history","Scheduled evidence + dashboards","Metered per assured decision"],price:"Usage-based"},
    {t:"ENTERPRISE",c:C.accent,h:"Self-hosted / VPC",items:["SSO, RBAC, retention, SIEM export","Signed Article-12 evidence bundles","Validated domain contract packs"],price:"Committed"},
  ];
  const w=3.9,y=2.6,h=3.4;
  tiers.forEach((ti,i)=>{const x=0.6+i*(w+0.18);
    s.addShape("roundRect",{x,y,w,h,rectRadius:0.1,fill:{color:C.cardBg},line:{color:C.cardBorder,width:1}});
    s.addText(ti.t,{x:x+0.28,y:y+0.26,w:w-0.56,h:0.3,fontFace:FONT,fontSize:10.5,bold:true,color:ti.c,charSpacing:1,margin:0});
    s.addText(ti.h,{x:x+0.28,y:y+0.62,w:w-0.56,h:0.35,fontFace:FONT,fontSize:15,bold:true,color:C.ink,margin:0});
    let iy=y+1.15;
    ti.items.forEach(it=>{ s.addText("•",{x:x+0.28,y:iy,w:0.2,h:0.3,fontFace:FONT,fontSize:12,color:ti.c,margin:0});
      s.addText(it,{x:x+0.5,y:iy,w:w-0.75,h:0.55,fontFace:FONT,fontSize:11.5,color:C.body,lineSpacingMultiple:1.15,valign:"top",margin:0}); iy+=0.62; });
    s.addText(ti.price,{x:x+0.28,y:y+h-0.55,w:w-0.56,h:0.35,fontFace:FONT,fontSize:13,bold:true,color:ti.c,margin:0});
  });
  s.addText("Pricing is a hypothesis until design partners commit. The novel unit — price per assured decision — aligns cost with the value delivered.",
    {x:0.6,y:6.25,w:12.1,h:0.5,fontFace:FONT,fontSize:11.5,italic:true,color:C.faint,align:"center",margin:0});
  pageno(s,"11");
}

/* ── 12 · Competition / positioning ── */
{
  const s=S();
  kicker(s,"Positioning");
  title(s,"Everyone else answers a different question.");
  const rows=[
    {who:"Guardrails / Bedrock",q:"Is this content safe?",gap:"One call. Screens words, not business rules. Can't prove a decision."},
    {who:"Patronus / evals",q:"Is the model good in general?",gap:"Offline, pre-deployment. Doesn't govern the live decision that ships."},
    {who:"agentgateway (LF)",q:"Can these agents connect?",gap:"Connectivity, routing, auth. No notion of whether a decision was allowed."},
    {who:"Datadog / Langfuse",q:"What happened?",gap:"Observability after the fact. A trace, not an acceptance record."},
  ];
  let y=2.35;
  rows.forEach((r)=>{
    s.addText(r.who,{x:0.6,y,w:3.1,h:0.6,fontFace:FONT,fontSize:13.5,bold:true,color:C.ink,valign:"top",margin:0});
    s.addText("“"+r.q+"”",{x:3.8,y,w:3.2,h:0.6,fontFace:FONT,fontSize:13,italic:true,color:C.body,valign:"top",margin:0});
    s.addText(r.gap,{x:7.1,y,w:5.6,h:0.6,fontFace:FONT,fontSize:12,color:C.faint,lineSpacingMultiple:1.2,valign:"top",margin:0});
    y+=0.72;
  });
  s.addShape("roundRect",{x:0.6,y:5.5,w:12.1,h:1.15,rectRadius:0.1,fill:{color:C.navy}});
  s.addText([
    {text:"Kaaval:  ",options:{bold:true,color:C.accent}},
    {text:"“Was this decision allowed — and can you prove it?”   ",options:{bold:true,color:"FFFFFF"}},
    {text:"If you can't audit it, it's not governance. It's hope.",options:{italic:true,color:"CBD5E1"}},
  ],{x:0.95,y:5.5,w:11.4,h:1.15,fontFace:FONT,fontSize:15,valign:"middle",lineSpacingMultiple:1.25,margin:0});
  pageno(s,"12");
}

/* ── The world we're building (aspiration) ── */
{
  const s=S();
  kicker(s,"The world we're building");
  title(s,"When AI can be trusted with decisions, it can run real things.");
  sub(s,"Five years out, the accountability we're building isn't a product a few teams buy — it's the default every consequential AI action carries.");
  const fut=[
    {h:"Billions of decisions a day",d:"Every consequential AI action — a refund, a diagnosis, a trade, a dispatch — carries a verifiable record of what it was allowed to do and why."},
    {h:"The standard evidence format",d:"Regulators, auditors, and insurers read Kaaval receipts the way finance reads a ledger. Proving an AI decision becomes a query, not an archaeology dig."},
    {h:"AI safe enough to run the economy",d:"Autonomous agents operate money, healthcare, and infrastructure — because their decisions are accountable by default, not trusted by hope."},
  ];
  const w=3.9,y=2.55,h=3.1;
  fut.forEach((f,i)=>{const x=0.6+i*(w+0.18);
    s.addShape("roundRect",{x,y,w,h,rectRadius:0.1,fill:{color:C.cardBg},line:{color:C.cardBorder,width:1}});
    s.addText(f.h,{x:x+0.28,y:y+0.3,w:w-0.56,h:0.7,fontFace:FONT,fontSize:16,bold:true,color:C.accent,lineSpacingMultiple:1.1,margin:0});
    s.addText(f.d,{x:x+0.28,y:y+1.15,w:w-0.56,h:1.8,fontFace:FONT,fontSize:12.5,color:C.body,lineSpacingMultiple:1.35,valign:"top",margin:0});
  });
  s.addShape("roundRect",{x:0.6,y:5.9,w:12.1,h:0.7,rectRadius:0.08,fill:{color:C.navy}});
  s.addText([
    {text:"The agentic economy needs a trust layer. We intend to be it.",options:{bold:true,color:"FFFFFF"}},
    {text:"    Stated as vision — the destination we build toward, not shipped features.",options:{italic:true,color:"8A97A6"}},
  ],{x:0.95,y:5.9,w:11.4,h:0.7,fontFace:FONT,fontSize:14,valign:"middle",margin:0});
  pageno(s);
}

/* ── Team + close ── */
{
  const s=S();
  kicker(s,"Team & vision");
  title(s,"Built by two engineers who refuse to overclaim.");
  const team=[
    {n:"Milind Gunjan",r:"Product, systems, go-to-market"},
    {n:"Hari Krishna Govindarajan",r:"Architecture, assurance engine, platform"},
  ];
  team.forEach((t,i)=>{const x=0.6+i*6.05;
    s.addShape("roundRect",{x,y:2.35,w:5.85,h:1.15,rectRadius:0.1,fill:{color:C.cardBg},line:{color:C.cardBorder,width:1}});
    s.addText(t.n,{x:x+0.3,y:2.55,w:5.3,h:0.4,fontFace:FONT,fontSize:16,bold:true,color:C.ink,margin:0});
    s.addText(t.r,{x:x+0.3,y:2.98,w:5.3,h:0.35,fontFace:FONT,fontSize:12,color:C.body,margin:0});
  });
  s.addText("The vision is simple:",{x:0.6,y:4.0,w:12,h:0.4,fontFace:FONT,fontSize:15,color:C.body,margin:0});
  s.addText("Every enterprise AI action should carry an acceptance receipt.",{x:0.6,y:4.5,w:12.1,h:1.0,fontFace:FONT,fontSize:30,bold:true,color:C.ink,lineSpacingMultiple:1.1,margin:0});
  s.addText("VERIFY, DON'T PREDICT.  ·  RECEIPTS, NOT PROMISES.",{x:0.6,y:5.85,w:11,h:0.4,fontFace:MONO,fontSize:13,bold:true,color:C.accent,charSpacing:1,margin:0});
  footer(s,"github.com/kaaval-ai · kaaval.ai · Kaaval — the accountability layer for AI decisions");
  pageno(s,"13");
}

deck.writeFile({ fileName: "Kaaval-Comprehensive-Deck.pptx" }).then(()=>console.log("written"));
