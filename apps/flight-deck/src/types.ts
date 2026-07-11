/* ── Kaaval Assurance — Flight Deck domain types ──
   These mirror the backend artifact schemas (TelemetrySummary, TrajectoryRow,
   RuntimeProbeReport) and the /api/dashboard envelope. Nothing here models
   invented concepts: every field corresponds to a stored artifact value. */

export type SourceTag = 'measured' | 'configured' | 'not_available' | 'planned' | 'sample';

export interface Claim {
  claim: string;
  value: string;
  source: SourceTag;
  field: string;
}

export interface AttemptDetail {
  request_id: string;
  contract_id: string;
  category: string;
  provider: string;
  model_id: string;
  tier: 'local' | 'remote';
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  cached_tokens: number | null;
  latency_ms: number;
  cost_usd: number;
  verifier_passed: boolean;
  verifier_failure_count: number;
  verifier_failure_types: string[];
  verifier_failures: string[];
  escalated: boolean;
  escalation_reason: string | null;
}

export interface RuntimeProfile {
  provider: string;
  model_id: string;
  served_model_name?: string;
  model_family?: string | null;
  tier?: string;
  endpoint_type?: string;
  base_url_host?: string | null;
  hardware_target: string;
  rocm_version?: string | null;
  vllm_version?: string | null;
  dtype?: string;
  kv_cache_dtype?: string;
  tensor_parallel_size?: number;
  gpu_memory_utilization?: number;
  prefix_caching_enabled?: boolean;
  max_context_tokens?: number | null;
  structured_output_mode?: string;
}

export interface TelemetrySummary {
  run_id: string;
  requests: number;
  attempts: number;
  latency_ms_p50: number;
  latency_ms_p95: number;
  provider_mix: {
    attempts_by_provider: Record<string, number>;
    requests_by_first_tier: Record<string, number>;
    local_attempts: number;
    remote_attempts: number;
    audit_calls: number;
  };
  runtime: {
    status: 'configured' | 'planned';
    profile: RuntimeProfile | null;
    cached_tokens_total: number | null;
    note: string;
  };
  verification: {
    local_verified_rate: number;
    final_verified_rate: number;
    failures_by_check: Record<string, number>;
  };
  routing: {
    escalation_rate: number;
    preroute_remote_rate: number;
    ewma_drift_by_category: Record<string, number>;
    high_drift_categories: string[];
    watch_categories: string[];
  };
  audit: {
    enabled: boolean;
    sampled: number;
    accepted_answers: number;
    trusted: boolean | null;
    calibration_status: string | null;
    calibration_fp_rate: number | null;
    calibration_threshold: number | null;
    passed: number;
    failed: number;
    errors: number;
    violations_by_severity: Record<string, number>;
    audit_tokens: number;
  };
  cost: {
    total_cost_usd: number;
    local_cost_usd: number;
    remote_cost_usd: number;
    audit_cost_usd: number;
    cost_per_verified_answer_usd: number | null;
    audit_cost_per_verified_accepted_usd: number | null;
    remote_calls_avoided: number | null;
    remote_calls_avoided_rate: number | null;
    remote_tokens_avoided: number | null;
    estimated_cost_saved_vs_always_remote_usd: number | null;
  };
  attempts_detail: AttemptDetail[];
  claims: Claim[];
}

export interface TrajectoryRow {
  db_id: number | null;
  request_id: string;
  ts: string;
  category: string;
  contract_id: string;
  contract_version: string;
  tier: 'local' | 'remote';
  provider: string;
  model_id: string;
  verifier_passed: boolean;
  verifier_failures: string[];
  escalated: boolean;
  latency_ms: number;
  cost_usd: number;
  prompt_tokens: number;
  completion_tokens: number;
  task_input: string;
  raw_text: string;
  audit_sampled: boolean;
  audit_result: string | null;
  audit_violations: Record<string, unknown>[] | null;
}

export interface ProbeCommand {
  command: string[];
  available: boolean;
  output: string | null;
  error: string | null;
  source: string;
}

export interface RuntimeProbeReport {
  probed_at: string;
  system: {
    cwd: string;
    under_workspace: boolean;
    python_version: string;
    source: string;
  };
  packages: { name: string; importable: boolean; version: string | null; source: string }[];
  commands: Record<string, ProbeCommand>;
  env_vllm: Record<string, string>;
  env_fireworks: Record<string, string>;
  endpoint: {
    base_url: string;
    reachable: boolean;
    latency_ms: number | null;
    served_models: string[];
    configured_model: string | null;
    configured_model_served: boolean | null;
    model_family: string;
    vllm_version: string | null;
    error: string | null;
  } | null;
  policy: string;
}

export interface Provenance {
  available: boolean;
  artifact: string | null;
  origin: 'artifacts' | 'sample' | 'not_available';
  modified_at: string | null;
}

export interface FireworksRunMetrics {
  requests: number;
  total_attempts: number;
  remote_attempts: number;
  total_configured_remote_cost: number;
  final_verified_rate: number;
}

export interface FireworksComparisonArtifact {
  local_first: FireworksRunMetrics;
  always_remote: FireworksRunMetrics;
  comparison: {
    remote_calls_avoided: number;
    remote_call_reduction_percentage: number;
    configured_cost_avoided: number;
    cost_reduction_percentage: number;
  };
  caveats: string[];
}

export interface AmdEvidence {
  status: 'measured' | 'configured' | 'pending' | 'unavailable';
  reason: string;
}

export type DataLabel =
  | 'SAMPLE'
  | 'CAPTURED LOCAL RUN'
  | 'CAPTURED FIREWORKS RUN'
  | 'MEASURED AMD RUN'
  | 'UNAVAILABLE'
  | 'UNVERIFIED (INCONSISTENT BUNDLE)';

export interface DashboardPayload {
  generated_at: string;
  mode: 'captured';
  label: DataLabel;
  used_sample: boolean;
  amd: AmdEvidence;
  bundle_consistent?: boolean;
  bundle_id?: string | null;
  consistency_reason?: string;
  provenance: {
    telemetry: Provenance;
    trajectory: Provenance;
    runtime_probe: Provenance;
  };
  comparison_provenance: Provenance;
  telemetry: TelemetrySummary | null;
  trajectory: TrajectoryRow[] | null;
  runtime_probe: RuntimeProbeReport | null;
  comparison: FireworksComparisonArtifact | null;
}

/* ── Live runs ── */

export interface LiveRunRequest {
  task_input: string;
  contract_id: string;
  local_provider: 'mock' | 'ollama' | 'vllm';
  remote_provider: 'mock' | 'fireworks';
  confirm_spend: boolean;
  failure_mode: string | null;
  remote_failure_mode: string | null;
  export_artifacts: boolean;
  session_id?: string;
}

export interface LiveRunResponse {
  run_id: string;
  mode: 'live';
  label: 'LIVE RUN';
  generated_at: string;
  session: {
    session_id: string;
    category: string;
    online_ewma_drift: number;
    current_policy_action: string;
    current_policy_reason: string;
  };
  request: {
    contract_id: string;
    category: string;
    local_provider: string;
    remote_provider: string;
    failure_mode: string | null;
    remote_failure_mode: string | null;
  };
  result: {
    verified: boolean;
    checks_run: number;
    failures: string[];
    escalated: boolean;
    attempts: number;
    tier: string;
    routing_reason: string;
    answer: Record<string, unknown> | null;
    raw_text: string;
  };
  trajectory: TrajectoryRow[];
  telemetry: TelemetrySummary;
  runtime_profile: RuntimeProfile | null;
  artifacts_written: string[];
}

export type ConnectionStatus = 'loading' | 'connected' | 'stale' | 'unavailable';
