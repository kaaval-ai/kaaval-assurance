/* ── Kaaval Assurance — Inference Flight Deck Types ── */

/* ── Provider ── */
export type ProviderStatus = 'online' | 'degraded' | 'down' | 'disabled';

export interface Provider {
  id: string;
  name: string;
  status: ProviderStatus;
  latencyMs: number;
  requestsPerMin: number;
  errorRate: number;
  quotaUsed: number;
  quotaLimit: number;
  lastChecked: string;
}

/* ── Pipeline Stage ── */
export type StageStatus = 'running' | 'passed' | 'failed' | 'idle';

export interface PipelineStage {
  id: string;
  label: string;
  status: StageStatus;
  durationMs: number;
  logs: string[];
}

/* ── Contract Gate / Policy ── */
export type PolicyStatus = 'pass' | 'warn' | 'fail' | 'pending';

export interface Policy {
  id: string;
  name: string;
  icon: string;
  verifiers: string[];
  status: PolicyStatus;
  lastVerified: string;
}

/* ── Model Comparison ── */
export interface ModelMetrics {
  latencyP50: number;
  latencyP95: number;
  throughput: number;
  costPerToken: number;
  accuracy: number;
  hallucinationRate: number;
}

export interface ModelEntry {
  id: string;
  name: string;
  provider: string;
  metrics: ModelMetrics;
  status: 'active' | 'deprecated' | 'staging';
}

/* ── Telemetry ── */
export interface TelemetryPoint {
  timestamp: string;
  value: number;
  label?: string;
}

export interface TelemetryMetric {
  id: string;
  label: string;
  unit: string;
  icon?: string;
  current: number;
  min: number;
  max: number;
  avg: number;
  alarm: boolean;
  sparkline: TelemetryPoint[];
  value: number;
}

/* ── Trajectory Replay ── */
export type StepStatus = 'success' | 'warning' | 'error' | 'running';

export interface TrajectoryStep {
  id: string;
  timestamp: string;
  action: string;
  status: StepStatus;
  durationMs?: number;
  detail?: string;
}

/* ── AMD Proof ── */
export type AttestationStatus = 'verified' | 'pending' | 'failed';

export interface AMDMeasurement {
  id: string;
  measurementId: string;
  status: AttestationStatus;
  firmwareVersion: number;
  tcbVersion: string;
  launchDigest: string;
  reportId: string;
  signature: string;
}

/* ── App State ── */
export interface FlightDeckState {
  pipeline: PipelineStage[];
  providers: Provider[];
  policies: Policy[];
  models: ModelEntry[];
  telemetry: TelemetryMetric[];
  trajectory: TrajectoryStep[];
  amdMeasurements: AMDMeasurement[];
  systemUptime: number;
  totalRequests: number;
  activeAlerts: number;
  providerCount: number;
  contractCount: number;
}