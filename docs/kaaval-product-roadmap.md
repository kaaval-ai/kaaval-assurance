# Kaaval product roadmap

**Working product thesis:** Kaaval is the accountability layer between enterprise AI models and consequential actions. **Kaaval Assurance** governs each model call at runtime. **NanoCanary** measures how a model's behavior changes under sustained pressure before and between releases. Together they turn model reliability from a benchmark slide into an enforceable, replayable operating process.

**Roadmap date:** July 12, 2026  
**Planning horizon:** 12 months  
**Primary wedge:** consequential model calls in customer support, operations, compliance, and approval workflows  
**Primary buyer:** AI platform or applied-AI lead; governance, risk, and audit are the internal beneficiaries

## 1. The light-bulb moment

Enterprises can observe model calls, run offline evaluations, or route to another provider. Those are separate activities today. The missing system is the one that can answer, for every consequential AI decision:

1. What was the model required to do?
2. Did this output satisfy those requirements?
3. Was the serving model behaving like the version we approved?
4. What happened when a check failed?
5. Can we replay the evidence later?

Kaaval's product loop is:

```text
NanoCanary qualifies and monitors model behavior
                         |
                         v
Kaaval Assurance enforces task contracts on each model call
                         |
                         v
Failure triggers escalation or human review, and every attempt leaves a receipt
                         |
                         v
Receipts and drift evidence improve release and routing policy
```

The durable category is **AI decision assurance**. The product is not an agent framework, a generic evaluation suite, or another cost-only model router.

## 2. Product boundaries

### Kaaval Assurance — runtime enforcement

Kaaval Assurance sits in the request path for consequential model calls. Its job is to:

- express a task's acceptable output as a versioned contract;
- verify each response with deterministic checks before downstream use;
- fail closed on malformed output and transport failures;
- escalate selectively to an alternate provider or human-review queue;
- adapt routing from measured operational failure patterns;
- emit a replayable receipt with contract, provider, checks, routing reason, latency, tokens, and cost.

It does **not** claim that schema conformance proves semantic truth. Semantic false-accept and false-reject measurement is a core roadmap gate.

### NanoCanary — behavioral qualification and drift sensing

NanoCanary runs controlled, multi-turn adversarial probes against a model/version. Its job is to:

- test calibrated integrity across factual, logical, opinion, and authority-pressure categories;
- preserve pre-registered criteria and evidence provenance;
- detect same-model behavioral changes between versions or runs;
- produce advisory evidence for model release, retest, shadow, or quarantine decisions.

It does **not** currently benchmark general model reliability, prove task competence, or support cross-model fingerprint ranking. Those uses remain gated by the NanoCanary claim map and decision semantics.

### Kaaval Control Plane — shared policy and evidence surface

The control plane is the product surface that joins both systems without collapsing their boundaries. It will manage:

- model and endpoint inventory;
- task-contract versions and deployment state;
- NanoCanary validation records and caveats;
- runtime assurance policies;
- receipts, review queues, replay, and evidence export;
- organization, environment, role, retention, and deployment settings.

The first control plane should be thin. It is not a new orchestration framework.

## 3. Current evidence baseline

| Surface | Built and currently defensible | Important limit |
|---|---|---|
| Kaaval Assurance | Provider-neutral model path; deterministic contracts; fail-closed behavior; selective escalation; EWMA routing adaptation; sampled audit; trajectory receipts; runtime probe; API and Flight Deck; measured AMD/ROCm/vLLM/Gemma artifact | Layer 1 establishes contract conformance, not semantic correctness. Layer 3 is display-only and FP-only calibrated. Shadow mode, durable distributed state, recovery probes, and a drop-in gateway are not complete. |
| NanoCanary | 32-probe definitions; provider clients; deterministic scoring; five-dimensional physics-inspired fingerprint; telemetry; redacted artifacts; evidence ledger; validation promotion workflow; advisory decision semantics | Full 32-probe scientific validation is not complete. Cross-model fingerprint comparison is unsupported. Known no-signal, negative-k, and restatement-detection limitations remain. Zero models currently meet the documented governance approval bar. |
| Integration | Shared conceptual model: observed evidence should drive explicit, inspectable policy decisions | No production Kaaval Assurance policy currently consumes NanoCanary evidence. This must begin as advisory/shadow integration. |

Local verification on July 12, 2026:

- Kaaval Assurance: **361 tests passed**.
- NanoCanary: **400 tests passed** when run from a writable temporary working directory; its `doctor` check intentionally verifies that the working `results/` directory is writable.

These test results establish implementation health, not market demand or scientific validity.

## 4. Product principles

1. **Receipts before dashboards.** If a claim cannot be traced to stored evidence, it does not belong in the product surface.
2. **Contracts before autonomous policy.** A customer must be able to inspect what is enforced and why.
3. **Shadow before gate.** New contracts and behavioral signals observe first, then warn, then gate only after measured acceptance criteria are met.
4. **Same evidence, every tier.** Local, cloud, escalated, and human-reviewed attempts share one receipt schema.
5. **Advisory signals stay advisory.** NanoCanary results cannot drive stronger actions than their validation status permits.
6. **Version everything consequential.** Model, prompt, contract, probe battery, scorer, policy, and receipt schema versions travel together.
7. **Local-first, provider-neutral.** Customers can keep traffic and evidence inside their boundary and replace providers without rewriting policy.
8. **No agent-platform drift.** Kaaval assures model calls and release decisions; it does not own arbitrary planning or tool orchestration.

## 5. Roadmap

### Phase 0 — product truth and integration contract (now to day 30)

**Outcome:** one honest, installable assurance gateway and one scientifically bounded behavioral-evidence interface.

#### Kaaval Assurance

- Publish a blind semantic evaluation set with separate contract-conformance, false-accept, false-reject, and critical-field accuracy metrics.
- Add two-sided Layer 3 calibration and keep audit-to-routing disabled until calibration gates pass.
- Implement a real shadow mode that mirrors decisions, evaluates contracts, and writes receipts without blocking customer traffic.
- Define externally managed, versioned contracts in JSON/YAML with a stable lifecycle: draft, shadow, enforced, retired.
- Ship a minimal OpenAI-compatible reverse-proxy surface plus Python and TypeScript interception examples.
- Add recovery probes, bounded retries, circuit-breaker state, idempotency keys, and durable receipt storage.
- Make human review a first-class terminal outcome alongside accept, escalate, and no-safe-answer.
- Measure end-to-end total cost per contract-conformant answer, including retries, escalation, review, and infrastructure.

#### NanoCanary

- Close or explicitly disposition the four documented scoring backlog items: no-signal classification, negative-k baseline semantics, L02 register coverage, and bare-restatement detection.
- Run the pre-registered full 32-probe battery on at least two available provider/model families.
- Report per-category detection quality, runtime-failure exclusions, rerun variability, and scorer blind spots; do not collapse these into one guardian score.
- Version the probe battery, pressure rubric, lexicons, scorer, criteria, and evidence ledger in every promoted record.
- Define a machine-readable `BehavioralEvidenceRecord` containing model/version identity, coverage, validation tier, caveats, drift status, criteria reference, and evidence hash.

#### Integration

- Add a read-only NanoCanary evidence panel to the Kaaval control surface.
- Map only three initial actions: `retest_required`, `shadow_only`, and `drift_alert`.
- Do not consume raw fingerprint dimensions for routing in this phase.
- Establish the join key across products: provider, immutable model/version identifier, deployment endpoint, and evaluation timestamp.

#### Exit gates

- One external application can proxy calls through Kaaval without changing its model SDK usage pattern.
- Shadow mode runs for seven days without affecting response delivery and produces replayable receipts.
- The semantic evaluation reports both sides of error, not only conformance.
- NanoCanary has criteria-gated full-battery evidence on at least two provider/model families.
- Every cross-product UI action is no stronger than the underlying NanoCanary validation tier.

### Phase 1 — design-partner shadow pilots (days 31 to 90)

**Outcome:** prove that a customer will integrate Kaaval, author contracts, and act on its evidence.

#### Customer scope

- Recruit two design partners with one narrow consequential workflow each.
- Prefer high-volume workflows with explicit business rules: refund eligibility, support escalation, incident classification, compliance triage, or approval routing.
- Establish a baseline before gating: current failure rate, manual review rate, incident reconstruction time, provider cost, and latency.

#### Product

- Provide a guided contract-authoring workflow with test cases, counterexamples, and shadow replay.
- Add a review queue showing the input, attempted outputs, failed check IDs, policy version, and recommended action.
- Run NanoCanary on each candidate model/version before deployment and on a schedule after deployment.
- Surface version changes and confirmed same-model drift inside the Assurance policy editor.
- Add environment separation, API keys, RBAC basics, retention controls, signed exports, and OpenTelemetry-compatible events.
- Deliver a weekly assurance report: calls observed, conformance, semantic errors from reviewed samples, escalations, recoveries, human reviews, cost, and unresolved drift.

#### Integration policy

- `retest_required`: block promotion in Kaaval's release workflow, not live inference.
- `shadow_only`: allow the model to receive mirrored traffic but not serve accepted production responses.
- confirmed `drift_alert`: tighten sampling and require review; quarantine only after a customer-approved policy and a confirmed rerun.
- No cross-model “safest model” routing until comparative validity is demonstrated.

#### Exit gates

- Two design partners complete installation and at least one reaches four continuous weeks in shadow mode.
- At least one partner chooses to enforce one contract based on measured shadow results.
- Receipts reduce incident reconstruction from manual log archaeology to a repeatable query/export.
- The team can identify at least one caught issue that the customer's existing observability or evaluation process missed.
- A buyer states a credible budget owner and renewal condition.

### Phase 2 — production assurance gateway (months 3 to 6)

**Outcome:** move from a promising control to a production system customers will pay to keep.

- Support high-availability gateway deployment, horizontal scaling, durable queues, encrypted storage, backup/restore, and defined SLOs.
- Offer self-hosted and managed control-plane deployment with customer-controlled data-plane options.
- Add policy approvals, separation of duties, immutable audit history, SSO/SAML, SCIM, and configurable retention.
- Add contract packs for the first validated vertical while keeping the core contract engine domain-neutral.
- Create model-release gates that combine task evaluation, NanoCanary evidence status, deployment metadata, and human approval without inventing a single opaque score.
- Introduce audit-to-routing only for signals that have passed prospective validation and customer-specific acceptance criteria.
- Add usage metering around assured decisions, not raw tokens alone.
- Publish a design-partner case study with measured operational outcomes and explicit limits.

#### Exit gates

- Three production workloads, including one customer outside the founding network.
- At least one paid annual or committed pilot contract.
- Demonstrated SLOs and recovery behavior under provider outage, malformed output, storage interruption, and policy-service degradation.
- Customer-validated improvement in at least one economic metric: manual reviews, incidents, escalation spend, or investigation time.
- No critical action is driven by an unversioned or validation-ineligible signal.

### Phase 3 — fleet intelligence and category leadership (months 6 to 12)

**Outcome:** make Kaaval the system of record for how enterprise AI decisions were tested, governed, and released.

- Build fleet views across models, versions, endpoints, contracts, and environments.
- Add domain-specific NanoCanary probe packs with independent criteria and validation records.
- Validate cross-model behavioral comparisons before introducing behavior-aware model selection.
- Add privacy-preserving aggregate learning across consenting deployments; raw customer prompts and outputs remain opt-in.
- Connect receipts to governance workflows, incident systems, model registries, and compliance evidence exports.
- Add policy simulation: replay a proposed contract or routing rule over historical receipts before activation.
- Expose an evidence API for risk, audit, and third-party assurance partners.
- Evaluate insurer and technology-risk partnerships only after customer loss/incident data supports the hypothesis.

#### Exit gates

- Ten production workloads and repeatable onboarding for the initial vertical.
- Net revenue retention evidence or equivalent expansion behavior from early customers.
- Comparative NanoCanary claims supported by prospective, pre-registered, multi-model evidence.
- Policy simulation and replay are used in every production policy change.
- A clear decision, backed by usage, on whether Substrate, ShadowDeploy, and advanced routing become integrated products, optional modules, or remain research/incubation projects.

## 6. Shared data contract

The first integration should exchange evidence records, not internal databases.

```json
{
  "schema_version": "1.0",
  "evidence_id": "immutable-id",
  "model": {
    "provider": "provider-name",
    "model_id": "exact-model-id",
    "model_version": "immutable-version-if-available",
    "endpoint_id": "customer-deployment-id"
  },
  "nanocanary": {
    "probe_battery_version": "version",
    "scorer_version": "version",
    "coverage": {"completed": 0, "total": 32},
    "validation_tier": "diagnostic|engineering|validation_candidate|release_acceptance",
    "allowed_actions": ["retest_required", "shadow_only", "drift_alert"],
    "caveats": [],
    "criteria_ref": "committed-reference",
    "evidence_hash": "sha256"
  },
  "observed_at": "RFC-3339 timestamp"
}
```

Kaaval Assurance must reject or downgrade records with unknown schema versions, missing model identity, stale evidence, incomplete coverage, unresolved runtime failures, or actions that exceed the record's validation tier.

## 7. Scorecard

### Product truth

| Metric | Why it matters |
|---|---|
| Contract false-accept and false-reject rate | Prevents conformance from masquerading as correctness |
| Critical-field accuracy | Measures whether consequential decisions are right, not merely well-shaped |
| Escalation recovery rate | Shows whether paying for another model actually rescues the decision |
| Human-review rate and disposition | Makes unresolved risk visible |
| Receipt completeness and replay success | Proves the accountability artifact is operational |
| NanoCanary valid coverage and rerun variability | Separates behavioral evidence from runtime noise |
| Drift alert confirmation rate | Measures whether alerts survive rerun instead of creating policy churn |

### Customer value

| Metric | Why it matters |
|---|---|
| Time to first shadow receipt | Integration friction |
| Time to author and enforce first contract | Product usability |
| Cost per contract-conformant decision | Economic value of routing and recovery |
| Manual reviews avoided or better targeted | Operational ROI |
| Mean time to reconstruct an AI decision | Audit and incident-response value |
| Consequential errors caught before action | Core value proof |
| Weekly active policy owners and reviewers | Whether Kaaval becomes an operating process |

### Company validation

- Two shadow-mode design partners by day 90.
- One paid deployment and three production workloads by month 6.
- Ten production workloads with expansion evidence by month 12.
- No product roadmap milestone is considered commercially validated by test count, demo quality, or hackathon recognition alone.

## 8. Packaging and business model hypothesis

### Open source / developer

- Local Kaaval Assurance gateway and contract SDK.
- Local NanoCanary CLI, probe execution, redacted artifacts, and evidence verification.
- Single-node receipts and local replay.

### Team

- Hosted policy and evidence control plane.
- Shared contract registry, review queue, scheduled NanoCanary runs, dashboards, and integrations.
- Usage-based metering by assured decision and evidence retention.

### Enterprise

- Self-hosted or hybrid deployment, SSO/SCIM, advanced RBAC, retention, signed evidence export, support, and validated domain packs.
- Commercial terms should follow design-partner evidence; pricing is a hypothesis until buyers commit.

## 9. Explicitly not now

- A general agent framework or multi-step autonomous orchestrator.
- A public leaderboard claiming NanoCanary ranks model reliability.
- Routing directly on raw `k`, `I`, `eta`, `Pc`, or `thinning_rate` values.
- A single “trust score” that hides different evidence types and caveats.
- Broad Substrate, ShadowDeploy, Chakra, or contextual-bandit integration before the Assurance plus NanoCanary wedge earns repeated use.
- Fine-tuned scoring models or GRUs before a sufficiently large, reviewed probe corpus exists.
- Insurance-premium, compliance-certification, or liability-reduction claims without external evidence.
- New verticals before one workflow produces repeatable deployment and buying behavior.

## 10. Immediate operating backlog

| Order | Workstream | Deliverable | Proof of completion |
|---:|---|---|---|
| 1 | Customer discovery | Ten interviews and two design-partner candidates around one consequential workflow | Interview notes, current process map, buyer, baseline metric, and written pilot interest |
| 2 | Assurance semantics | Blind semantic benchmark and two-sided error report | Versioned dataset, preregistered scoring, reproducible report |
| 3 | Gateway adoption | OpenAI-compatible proxy and shadow mode | Unmodified sample app produces receipts without response-path impact |
| 4 | Reliability | Durable receipts, idempotency, recovery probes, and failure tests | Chaos/failure suite and replayable recovery evidence |
| 5 | NanoCanary validity | Scorer backlog decisions and two-provider full battery | Promoted ledger records and updated claim map |
| 6 | Evidence bridge | `BehavioralEvidenceRecord` schema and advisory ingestion | Contract tests prove invalid or overpowered records are rejected/downgraded |
| 7 | Pilot UX | Contract authoring, receipt search, and review queue | Design partner completes core workflow without developer intervention |
| 8 | Economics | TCO comparison using actual pilot traffic | Cost per accepted decision including review and infrastructure |

## 11. The pitch after this roadmap

> Enterprises are putting model outputs into consequential workflows, but observability tells them what happened only after the model answered. Kaaval governs the decision itself. NanoCanary qualifies how a model behaves under pressure; Kaaval Assurance enforces task contracts on every live call, escalates failures, and leaves a replayable receipt. We are building the accountability layer between enterprise AI and real-world action.

## 12. Evidence index used for this roadmap

This roadmap reconciles current code and tests with the most recent canonical
notes. Where a note and code disagree, code and promoted validation records win.

### Kaaval Assurance

- [Repository README](../README.md)
- [Architecture and built-versus-pending boundary](kaaval-assurance-architecture.md)
- [Feature verification matrix](feature-verification.md)
- Current source and tests under `src/kaaval_assurance/`, `apps/`, and `tests/`

### NanoCanary

- [Repository README](https://github.com/kaaval-ai/nanoCanary/blob/main/README.md)
- [Claim map](https://github.com/kaaval-ai/nanoCanary/blob/main/docs/validation/claim-map.md)
- [Decision semantics](https://github.com/kaaval-ai/nanoCanary/blob/main/docs/kaaval-decision-semantics.md)
- [Validation index](https://github.com/kaaval-ai/nanoCanary/blob/main/docs/validation/README.md)
- Current source and tests under `src/nanocanary/` and `tests/`

### Cross-product strategy

- [Technical position and roadmap](https://github.com/kaaval-ai/research-notes/blob/main/kaaval-technical-position-and-roadmap.md)
- [Canonical Kaaval master notes](https://github.com/kaaval-ai/research-notes/tree/main/kaaval)
- [Pre-mortem and competitive positioning](https://github.com/kaaval-ai/research-notes/blob/main/ip-strategy/pre-mortem-and-competitive-positioning.md)
- [Service-to-IP alignment](https://github.com/kaaval-ai/research-notes/blob/main/ip-strategy/service-alignment.md)
