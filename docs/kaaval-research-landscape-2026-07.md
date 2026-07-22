# Research landscape — what's built, what labs are researching, and how it strengthens Kaaval

Compiled 2026-07 from live web research (sources inline) plus items verified
earlier in this workspace (AWS Bedrock docs, Patronus funding, agentgateway/LF,
EU AI Act Articles 12/19, adoption statistics). Purpose: position Kaaval
against the real state of the field and extract concrete strengthenings.

---

## 1. What's built (commercial landscape)

| Layer | Who | What they do | What they don't do |
|---|---|---|---|
| Content guardrails | AWS Bedrock Guardrails (+ Automated Reasoning checks), Guardrails AI | Filter harm categories, denied topics, PII; AR checks validate against encoded logic | No business contracts, no receipts, no economics, AWS-bound |
| Agent security | Meta **LlamaFirewall** (open source) | Prompt-injection / goal-hijack / insecure-code defense; attack success 17.6%→1.7% on AgentDojo | Security risks, not business conformance; no decision records |
| Agent SDK guardrails | OpenAI **AgentKit / Agents SDK** | Input/output/tool guardrails run at the point of real-world action; human-in-the-loop approvals | Content/PII/jailbreak + allow-lists; no versioned business contracts, no replayable receipts, no cost governance |
| Offline eval / stress test | **Patronus AI** ($50M Series B, Jun 2026; $70M total) | "Digital worlds" simulation stress-testing of agents pre-deployment | Offline; does not govern or record the live decision that ships |
| Connectivity | **agentgateway** (Linux Foundation, Aug 2025) | MCP/A2A/LLM routing, budgets, failover, authn | Transport layer; no notion of whether a decision was allowed |
| Observability | Langfuse, Arize, Datadog | Traces, tokens, latency after the fact | A trace is not an acceptance record |
| **Decision audit (emerging!)** | **DeepInspect** (stateless proxy, signed per-decision audit records), **Compliora** (structured AI decision records) | Compliance-driven logging of identity/role/policy per decision | Passive recording — no enforcement, no contract check, no recovery, no fail-closed. **Closest neighbors; validates the receipt category** |

**Market framing (Gartner):** AI TRiSM market $3.1B (2025) → **$13.8B by 2030**
(35% CAGR). 95% of C-suite leaders report AI incidents in the past two years;
average loss without governance frameworks: **$4.4M per incident** (2025). In
**February 2026 Gartner published its first Market Guide for _Guardian
Agents_** — defined as the runtime-enforcement mechanism of AI TRiSM for
agentic systems. Kaaval's parent positioning ("Guardian intelligence for
agentic AI") predates and matches the category Gartner just named.

## 2. What frontier labs are researching

- **Anthropic** — SHADE-Arena (agents doing benign + sabotage tasks while a
  *monitor model* rates suspicion), sabotage evaluations, agentic-misalignment
  studies, and SLEIGHT-Bench (evasion attacks against agent monitors). Net
  finding: **LLM monitors watching LLM agents are useful and evadable** —
  monitors were shown to be manipulable and evadable in the labs' own
  benchmarks.
- **OpenAI** — AgentKit guardrails place validation "right at the point where
  the agent is about to take a real-world action," paired with human-approval
  flows. This **validates Kaaval's gate placement architecturally** while
  stopping at content-safety semantics.
- **Meta** — LlamaFirewall: defense-in-depth for agent *security* threats;
  explicitly the "final layer of defense" framing, open source.
- **DeepMind** — Frontier Safety Framework: capability-threshold evaluations
  (CBRN, cyber, ML R&D, deceptive alignment) applied at the *model lifecycle*
  level, not per-decision runtime.
- **Academia (2025–26)** — runtime enforcement for LLM agents is now an active
  field: **SafeAgent** (runtime protection over trajectories), **AgentSpec**
  (ICSE'26, customizable runtime enforcement rules), **ProbGuard**
  (probabilistic violation prediction). All descend from the **Simplex /
  Runtime Assurance (RTA) architecture** — the decades-old control-theory
  pattern: an unverified high-performance controller runs under a verified
  baseline controller plus deterministic switching logic.

## 3. The synthesis — where Kaaval sits

**The field has converged on Kaaval's problem and validated its architecture,
while leaving its exact slice unoccupied:**

1. **The gate location is now consensus** (OpenAI puts checks at the action
   point; Gartner names runtime enforcement as the mechanism; academia builds
   runtime enforcers). Kaaval is not contrarian — it is early in the
   consensus direction.
2. **The labs' own evidence argues for deterministic gates on bounded
   decisions.** Their monitors are LLMs watching LLMs — and their own
   benchmarks (SLEIGHT-Bench) show those monitors can be evaded. For
   *open-ended agent behavior*, probabilistic monitors are the only option.
   For *bounded business decisions with explicit rules* — refunds, approvals,
   claims — a deterministic contract gate is strictly more trustworthy, and
   nobody at the labs is building that slice. This is Kaaval's founding filter
   ("a governance system must be more trustworthy than what it governs")
   independently corroborated.
3. **Nobody combines the three things Kaaval combines.** Guardrails enforce
   but don't record or economize. Audit startups record but don't enforce.
   Gateways route but don't judge. Kaaval's unit — **enforce the business
   contract + recover-or-fail-closed + emit the replayable receipt + feed the
   economics back into routing** — has no direct occupant. DeepInspect and
   Compliora prove the receipt category is real and imminent; neither
   enforces.
4. **Simplex/RTA is the honest lineage claim.** "Fifty years of control theory
   says: run the unverified controller under a verified baseline with
   deterministic switching. Kaaval is the Simplex architecture for business
   decisions — the LLM is the advanced controller, the contract is the safety
   monitor, no-safe-answer is the baseline fallback." This grounds the design
   in established engineering rather than novelty claims, and belongs in the
   patent's background section.

## 4. Concrete strengthenings (actioned / to action)

| # | Strengthening | Where it lands |
|---|---|---|
| 1 | Adopt Gartner's **Guardian Agents** category language + AI TRiSM sizing ($3.1B→$13.8B, 95% incidents, $4.4M/incident) | Comprehensive deck why-now/market slides; YC application |
| 2 | Add the **Simplex/RTA lineage** line | Deck how-it-works footer; patent background; judge Q&A |
| 3 | Sharpen lab differentiation: "probabilistic monitors for open-ended behavior (labs) vs deterministic enforcement for bounded decisions (Kaaval)" — cite SLEIGHT-Bench evasion | Positioning slide; investor narrative |
| 4 | **OpenAI Agents SDK guardrail adapter** — Kaaval contract check as a tool-guardrail implementation; their guardrail interface is a distribution channel, not a competitor | Post-Build-Week task; pairs with existing PR-03 work |
| 5 | Treat **DeepInspect/Compliora as category validators and closest neighbors**; differentiation = enforcement-generated receipts vs passive logging. Raises urgency on Article-12 mapping (#27) and design partners (#18) | Competition slide row; sales narrative |
| 6 | Cite LlamaFirewall's AgentDojo numbers as proof guardrails work *for security* — and that no equivalent exists for business conformance | Problem/positioning narrative |
| 7 | EU AI Act enforcement now citable at **€30M/6%** for some violations mid-2026 + 10-year retention for high-risk documentation | Article-12 one-pager; deck why-now |

## 5. Threats this research surfaces (honest register)

- **OpenAI could extend AgentKit guardrails toward business contracts.** The
  interface exists; the semantics don't yet. Mitigation: be the best
  implementation *on* their interface (strengthening #4), own the receipt +
  economics layer they have no incentive to build.
- **The audit-log startups could add enforcement** faster than we add their
  compliance polish. Mitigation: our enforcement is already built and tested;
  ship the Article-12 mapping and signed-export before they ship a verifier.
- **Academic enforcers (AgentSpec et al.) could open-source the contract-rule
  layer.** Mitigation: the moat was never the rule engine — it's the contract
  library, the evidence corpus, and receipts-as-system-of-record.

---

*Sources: Gartner AI TRiSM Market Guide coverage (gartner.com, f5.com,
mindgard.ai, trussed.ai); Anthropic research pages (sabotage-evaluations,
shade-arena) and alignment blog; arXiv 2505.03574 (LlamaFirewall), 2604.17562
(SafeAgent), AgentSpec ICSE'26, ProbGuard 2508.00500; OpenAI AgentKit +
Agents SDK guardrails docs; DeepMind Frontier Safety Framework; deepinspect.ai,
Compliora coverage; Stony Brook black-box Simplex; EU AI Act coverage
(aigovernancedesk.com, superblocks.com). Session-verified: Bedrock Guardrails
docs, Patronus $50M (TechCrunch), agentgateway (linuxfoundation.org), EU AI
Act Articles 12/19 (artificialintelligenceact.eu).*
