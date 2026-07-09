/* ── Kaaval Assurance — Mock Data for Inference Flight Deck ── */

import type { FlightDeckState } from '../types';

const now = new Date().toISOString();

function minutesAgo(n: number) {
  const d = new Date(Date.now() - n * 60_000);
  return d.toISOString();
}

/* ── Pipeline Stages ── */
const pipelineStages = [
  {
    id: 'stage-1',
    label: 'Request Queue',
    status: 'running' as const,
    durationMs: 12,
    logs: ['2025-03-20T14:23:01Z [INFO] Request received', '2025-03-20T14:23:01Z [INFO] Queued for routing'],
  },
  {
    id: 'stage-2',
    label: 'Router',
    status: 'passed' as const,
    durationMs: 8,
    logs: ['2025-03-20T14:23:01Z [INFO] Routing decision made'],
  },
  {
    id: 'stage-3',
    label: 'Policy Gate',
    status: 'passed' as const,
    durationMs: 15,
    logs: ['2025-03-20T14:23:01Z [INFO] Policy check passed'],
  },
  {
    id: 'stage-4',
    label: 'Inference',
    status: 'running' as const,
    durationMs: 340,
    logs: ['2025-03-20T14:23:02Z [INFO] Inference started'],
  },
  {
    id: 'stage-5',
    label: 'Response',
    status: 'idle' as const,
    durationMs: 0,
    logs: ['Awaiting completion...'],
  },
];

/* ── Providers ── */
const providers = [
  {
    id: 'prv-1',
    name: 'OpenAI GPT-4o',
    status: 'online' as const,
    latencyMs: 142,
    requestsPerMin: 1280,
    errorRate: 0.4,
    quotaUsed: 72,
    quotaLimit: 100,
    lastChecked: now,
  },
  {
    id: 'prv-2',
    name: 'Anthropic Claude 3.5',
    status: 'online' as const,
    latencyMs: 211,
    requestsPerMin: 890,
    errorRate: 0.7,
    quotaUsed: 45,
    quotaLimit: 100,
    lastChecked: now,
  },
  {
    id: 'prv-3',
    name: 'Google Gemini Pro',
    status: 'degraded' as const,
    latencyMs: 487,
    requestsPerMin: 340,
    errorRate: 3.2,
    quotaUsed: 88,
    quotaLimit: 100,
    lastChecked: now,
  },
  {
    id: 'prv-4',
    name: 'Meta Llama 3',
    status: 'online' as const,
    latencyMs: 98,
    requestsPerMin: 2100,
    errorRate: 0.2,
    quotaUsed: 34,
    quotaLimit: 100,
    lastChecked: now,
  },
  {
    id: 'prv-5',
    name: 'Mistral Large',
    status: 'down' as const,
    latencyMs: 0,
    requestsPerMin: 0,
    errorRate: 100,
    quotaUsed: 100,
    quotaLimit: 100,
    lastChecked: minutesAgo(2),
  },
  {
    id: 'prv-6',
    name: 'DeepSeek R1',
    status: 'online' as const,
    latencyMs: 310,
    requestsPerMin: 560,
    errorRate: 1.1,
    quotaUsed: 62,
    quotaLimit: 100,
    lastChecked: now,
  },
];

/* ── Policies (Contract Gate) ── */
const policies = [
  {
    id: 'pol-1',
    name: 'Data Residency',
    icon: 'globe',
    verifiers: ['AWS Nitro', 'Azure CCA'],
    status: 'pass' as const,
    lastVerified: minutesAgo(1),
  },
  {
    id: 'pol-2',
    name: 'Model Version',
    icon: 'tag',
    verifiers: ['SLSA 2.0', 'Sigstore'],
    status: 'pass' as const,
    lastVerified: minutesAgo(3),
  },
  {
    id: 'pol-3',
    name: 'Latency SLA',
    icon: 'clock',
    verifiers: ['CloudWatch', 'Datadog'],
    status: 'warn' as const,
    lastVerified: minutesAgo(1),
  },
  {
    id: 'pol-4',
    name: 'Cost Cap',
    icon: 'dollar-sign',
    verifiers: ['AWS Budgets'],
    status: 'pass' as const,
    lastVerified: minutesAgo(5),
  },
  {
    id: 'pol-5',
    name: 'PII Redaction',
    icon: 'shield',
    verifiers: ['Presidio', 'NVIDIA NeMo'],
    status: 'fail' as const,
    lastVerified: minutesAgo(0),
  },
  {
    id: 'pol-6',
    name: 'Rate Limit',
    icon: 'zap',
    verifiers: ['Envoy', 'Kong'],
    status: 'pass' as const,
    lastVerified: minutesAgo(2),
  },
  {
    id: 'pol-7',
    name: 'Audit Trail',
    icon: 'file-text',
    verifiers: ['OpenTelemetry', 'Fluentd'],
    status: 'pass' as const,
    lastVerified: minutesAgo(4),
  },
  {
    id: 'pol-8',
    name: 'Encryption',
    icon: 'lock',
    verifiers: ['KMS', 'Tink'],
    status: 'pass' as const,
    lastVerified: minutesAgo(2),
  },
];

/* ── Models ── */
const models = [
  {
    id: 'mod-1',
    name: 'GPT-4o',
    provider: 'OpenAI',
    metrics: {
      latencyP50: 142,
      latencyP95: 320,
      throughput: 1280,
      costPerToken: 0.000015,
      accuracy: 97.2,
      hallucinationRate: 1.8,
    },
    status: 'active' as const,
  },
  {
    id: 'mod-2',
    name: 'Claude 3.5 Sonnet',
    provider: 'Anthropic',
    metrics: {
      latencyP50: 211,
      latencyP95: 450,
      throughput: 890,
      costPerToken: 0.000012,
      accuracy: 96.5,
      hallucinationRate: 1.2,
    },
    status: 'active' as const,
  },
  {
    id: 'mod-3',
    name: 'Gemini Pro 1.5',
    provider: 'Google',
    metrics: {
      latencyP50: 487,
      latencyP95: 920,
      throughput: 340,
      costPerToken: 0.000010,
      accuracy: 94.8,
      hallucinationRate: 2.1,
    },
    status: 'active' as const,
  },
  {
    id: 'mod-4',
    name: 'Llama 3 70B',
    provider: 'Meta',
    metrics: {
      latencyP50: 98,
      latencyP95: 210,
      throughput: 2100,
      costPerToken: 0.000005,
      accuracy: 92.3,
      hallucinationRate: 2.9,
    },
    status: 'active' as const,
  },
  {
    id: 'mod-5',
    name: 'Mistral Large',
    provider: 'Mistral',
    metrics: {
      latencyP50: 175,
      latencyP95: 380,
      throughput: 1050,
      costPerToken: 0.000008,
      accuracy: 93.7,
      hallucinationRate: 2.4,
    },
    status: 'active' as const,
  },
];

/* ── Telemetry Metrics ── */
const telemetryMetrics = [
  {
    id: 'tel-1',
    label: 'Latency',
    unit: 'ms',
    icon: 'latency',
    current: 187,
    min: 82,
    max: 1250,
    avg: 215,
    alarm: false,
    sparkline: Array.from({ length: 20 }, (_, i) => ({
      timestamp: minutesAgo(20 - i),
      value: 150 + Math.random() * 200,
    })),
    value: 187,
  },
  {
    id: 'tel-2',
    label: 'Throughput',
    unit: 'req/s',
    icon: 'throughput',
    current: 847,
    min: 320,
    max: 2100,
    avg: 890,
    alarm: false,
    sparkline: Array.from({ length: 20 }, (_, i) => ({
      timestamp: minutesAgo(20 - i),
      value: 600 + Math.random() * 800,
    })),
    value: 847,
  },
  {
    id: 'tel-3',
    label: 'Error Rate',
    unit: '%',
    icon: 'error',
    current: 1.2,
    min: 0.1,
    max: 8.4,
    avg: 1.8,
    alarm: false,
    sparkline: Array.from({ length: 20 }, (_, i) => ({
      timestamp: minutesAgo(20 - i),
      value: Math.random() * 4,
    })),
    value: 1.2,
  },
  {
    id: 'tel-4',
    label: 'Uptime',
    unit: '%',
    icon: 'uptime',
    current: 99.97,
    min: 99.2,
    max: 100,
    avg: 99.94,
    alarm: false,
    sparkline: Array.from({ length: 20 }, (_, i) => ({
      timestamp: minutesAgo(20 - i),
      value: 99.8 + Math.random() * 0.2,
    })),
    value: 99.97,
  },
];

/* ── Trajectory Replay Steps ── */
const trajectorySteps = [
  {
    id: 'traj-1',
    timestamp: '2025-03-20T14:22:58.123Z',
    action: 'Incoming request POST /v1/chat/completions',
    status: 'success' as const,
    durationMs: 2,
    detail: 'HTTP 200 · 1.2 KB payload',
  },
  {
    id: 'traj-2',
    timestamp: '2025-03-20T14:22:58.201Z',
    action: 'Router: select provider',
    status: 'success' as const,
    durationMs: 8,
    detail: 'Selected OpenAI GPT-4o (latency-based)',
  },
  {
    id: 'traj-3',
    timestamp: '2025-03-20T14:22:58.302Z',
    action: 'Policy Gate: Data Residency',
    status: 'success' as const,
    durationMs: 15,
    detail: 'AWS Nitro attestation passed',
  },
  {
    id: 'traj-4',
    timestamp: '2025-03-20T14:22:58.401Z',
    action: 'Policy Gate: PII Redaction',
    status: 'warning' as const,
    durationMs: 22,
    detail: 'Potential PII detected in user prompt (SSN pattern)',
  },
  {
    id: 'traj-5',
    timestamp: '2025-03-20T14:22:58.510Z',
    action: 'Inference call to OpenAI',
    status: 'running' as const,
    durationMs: 340,
    detail: 'Processing tokens...',
  },
  {
    id: 'traj-6',
    timestamp: '2025-03-20T14:22:58.750Z',
    action: 'AMD SEV-SNP attestation',
    status: 'success' as const,
    durationMs: 5,
    detail: 'Hardware TEE verified · firmware 1.55',
  },
  {
    id: 'traj-7',
    timestamp: '2025-03-20T14:22:58.950Z',
    action: 'Response assembled',
    status: 'running' as const,
    durationMs: 0,
    detail: 'Awaiting inference completion...',
  },
];

/* ── AMD Measurements ── */
const amdMeasurements = [
  {
    id: 'amd-1',
    measurementId: 'SEV-SNP-0x7A3F',
    status: 'verified' as const,
    firmwareVersion: 155,
    tcbVersion: 'v1.55.0',
    launchDigest: 'a1b2c3d4e5f6...',
    reportId: 'rpt-001',
    signature: '3045022100...',
  },
  {
    id: 'amd-2',
    measurementId: 'SEV-SNP-0x9B12',
    status: 'pending' as const,
    firmwareVersion: 150,
    tcbVersion: 'v1.50.2',
    launchDigest: 'f6e5d4c3b2a1...',
    reportId: 'rpt-002',
    signature: '3045022100...',
  },
  {
    id: 'amd-3',
    measurementId: 'SEV-SNP-0x4C7E',
    status: 'verified' as const,
    firmwareVersion: 155,
    tcbVersion: 'v1.55.0',
    launchDigest: '9a8b7c6d5e4f...',
    reportId: 'rpt-003',
    signature: '3045022100...',
  },
  {
    id: 'amd-4',
    measurementId: 'SEV-SNP-0x2D8F',
    status: 'failed' as const,
    firmwareVersion: 148,
    tcbVersion: 'v1.48.1',
    launchDigest: '3c4d5e6f7a8b...',
    reportId: 'rpt-004',
    signature: '3045022100...',
  },
];

/* ── Full App State ── */
export const defaultState: FlightDeckState = {
  pipeline: pipelineStages,
  providers: providers,
  policies: policies,
  models: models,
  telemetry: telemetryMetrics,
  trajectory: trajectorySteps,
  amdMeasurements: amdMeasurements,
  systemUptime: 45 * 3600 + 39 * 60, // 45h 39m in seconds
  totalRequests: 847300,
  activeAlerts: 3,
  providerCount: 6,
  contractCount: 12,
};