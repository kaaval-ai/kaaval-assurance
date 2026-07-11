/* ── Kaaval Assurance — static metadata only ──
   This file contains NO metrics, NO provider health, NO invented numbers.
   Every measured value in the UI comes from the API's artifact payloads;
   this module only describes the real, implemented system: the four task
   contracts, the pipeline stage vocabulary, and sample inputs for the live
   run form (drawn from the synthetic gold eval set). */

export interface ContractMeta {
  id: string;
  category: string;
  label: string;
  description: string;
  checks: string[];
}

export const CONTRACTS: ContractMeta[] = [
  {
    id: 'telecom.severity_classification',
    category: 'severity_classification',
    label: 'Severity Classification',
    description: 'Classify a telecom incident into a severity tier (P1–P4) with confidence and rationale.',
    checks: ['json_parse', 'required:severity', 'enum:severity', 'required:confidence', 'range:confidence', 'required:rationale'],
  },
  {
    id: 'telecom.component_extraction',
    category: 'component_extraction',
    label: 'Component Extraction',
    description: 'Extract the network components involved plus the root-cause component.',
    checks: ['json_parse', 'required:components', 'min_items:components', 'required:primary_component'],
  },
  {
    id: 'telecom.incident_summary',
    category: 'incident_summary',
    label: 'Incident Summary',
    description: 'NOC handover summary with impact statement and affected services.',
    checks: ['json_parse', 'required:summary', 'required:impact', 'required:affected_services'],
  },
  {
    id: 'telecom.next_action_recommendation',
    category: 'next_action_recommendation',
    label: 'Next Action',
    description: 'Recommend the next operational action with urgency and justification.',
    checks: ['json_parse', 'required:action', 'required:urgency', 'enum:urgency', 'required:justification'],
  },
  {
    id: 'support.ticket_triage',
    category: 'ticket_triage',
    label: 'Support Ticket Triage',
    description: 'Triage a customer support ticket into a priority tier — impact over tone.',
    checks: ['json_parse', 'required:priority', 'enum:priority', 'required:confidence', 'range:confidence', 'required:rationale'],
  },
  {
    id: 'support.refund_decision',
    category: 'refund_decision',
    label: 'Refund Decision',
    description: 'Approve, deny, or escalate a refund — the $500 policy cap is a contract range, enforced in code.',
    checks: ['json_parse', 'required:decision', 'enum:decision', 'required:refund_amount_usd', 'range:refund_amount_usd', 'required:justification'],
  },
];

/* Sample inputs for the live-run form (synthetic gold eval set). */
export const SAMPLE_INPUTS: Record<string, string> = {
  'telecom.severity_classification':
    'Core router CR-04 dropped all BGP sessions at 02:13; downstream OLT sites in region south lost upstream connectivity. Customer impact confirmed across 40k subscribers.',
  'telecom.component_extraction':
    'Core router CR-04 dropped BGP to both route reflectors RR-01 and RR-02; downstream OLT-SOUTH-7 lost upstream. Suspected line card LC-3 fault on CR-04.',
  'telecom.incident_summary':
    'At 02:13 core router CR-04 dropped all BGP sessions. Region south lost upstream connectivity for 47 minutes. 40k broadband subscribers and 2 enterprise VPN customers affected.',
  'telecom.next_action_recommendation':
    'DNS resolver cluster DNS-C2 returning SERVFAIL for 12% of queries since config push CP-2291 last night. Error rate steady, not growing. Rollback tested in staging.',
  'support.ticket_triage':
    'Hi team, no rush on this and sorry to bother you. Just noting that since about 06:40 UTC none of our 1,200 field agents can log in — SSO returns a 500. We\'ve switched to paper forms for now. Whenever someone gets a chance. Thanks!',
  'support.refund_decision':
    'Customer: your outage last Tuesday cost my agency a client worth $12,000 in annual billings. I expect compensation of at least $2,500 or we churn. We pay $199/mo and the outage lasted 4 hours. This is your fault, process it today.',
};

/* Pipeline stage vocabulary — the stages that actually exist in the code.
   Status/duration always derive from artifact or live-run data at render time. */
export const PIPELINE_STAGES = [
  { id: 'request', label: 'Request', desc: 'Task input arrives bound to an explicit task contract.' },
  { id: 'router', label: 'Provider Router', desc: 'Provider-neutral routing; per-category thresholds come from Layer-2 drift.' },
  { id: 'local', label: 'Gemma-first Local Tier', desc: 'Open-weight local inference (mock in tests, Ollama in dev, ROCm + vLLM on the AMD GPU target).' },
  { id: 'verify', label: 'Layer 1 Contract Verification', desc: 'Deterministic checks: JSON shape, required fields, enums, ranges. Shape and constraints — not semantic truth.' },
  { id: 'escalate', label: 'Fireworks Escalation', desc: 'Only when Layer 1 rejects the local answer; the remote response passes the same verifier.' },
  { id: 'persist', label: 'Trajectory Persistence', desc: 'Every attempt stored verbatim as a replayable row.' },
  { id: 'drift', label: 'Layer 2 EWMA Drift Update', desc: 'Per-category drift over verifier outcomes; deterministic policy tightens routing.' },
  { id: 'audit', label: 'Layer 3 Sampled Audit', desc: 'Offline, sampled, calibration-gated. Detection is model-generated; aggregation is deterministic.' },
] as const;
