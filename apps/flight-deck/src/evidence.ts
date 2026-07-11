import type {
  DashboardPayload,
  FireworksComparisonArtifact,
  RuntimeProbeReport,
  SourceTag,
  TelemetrySummary,
} from './types';

export interface EvidenceMetric {
  label: string;
  value: string;
  sub: string;
  source: SourceTag;
  tone: 'success' | 'accent' | 'warning' | 'destructive' | 'muted';
}

export interface ParsedAmdFacts {
  gpu: string | null;
  gfx: string | null;
  vramGiB: string | null;
  vllmVersion: string | null;
  servedModel: string | null;
  endpoint: string | null;
}

const formatPctFromFraction = (value: number | null | undefined): string =>
  value === null || value === undefined ? 'n/a' : `${(value * 100).toFixed(1)}%`;

const formatPctFromPercent = (value: number | null | undefined): string =>
  value === null || value === undefined ? 'n/a' : `${value.toFixed(1)}%`;

const formatUsd = (value: number | null | undefined): string =>
  value === null || value === undefined ? 'n/a' : `$${value.toFixed(4)}`;

function lineMatch(output: string | null | undefined, pattern: RegExp): string | null {
  if (!output) return null;
  const match = output.match(pattern);
  return match?.[1]?.trim() ?? null;
}

export function parseAmdFacts(probe: RuntimeProbeReport | null): ParsedAmdFacts {
  const product = probe?.commands?.rocm_smi_product?.output ?? null;
  const vram = probe?.commands?.rocm_smi_vram?.output ?? null;
  const vllm = probe?.commands?.vllm_version?.output ?? null;
  const bytes = lineMatch(vram, /VRAM Total Memory \(B\):\s*([0-9]+)/);
  const vramGiB = bytes ? `${(Number(bytes) / 1024 ** 3).toFixed(1)} GiB` : null;
  const model = probe?.endpoint?.served_models?.[0] ?? probe?.endpoint?.configured_model ?? null;
  const endpoint = probe?.endpoint
    ? probe.endpoint.reachable
      ? `${probe.endpoint.base_url} · ${probe.endpoint.latency_ms?.toFixed(1) ?? 'n/a'}ms`
      : 'endpoint unreachable'
    : null;

  return {
    gpu:
      lineMatch(product, /Card Vendor:\s*(.+)/) ||
      lineMatch(product, /Card Model:\s*(.+)/) ||
      lineMatch(product, /Card Series:\s*(.+)/),
    gfx: lineMatch(product, /GFX Version:\s*(.+)/),
    vramGiB,
    vllmVersion: vllm?.trim() || probe?.endpoint?.vllm_version || null,
    servedModel: model,
    endpoint,
  };
}

export function headlineMetrics(payload: DashboardPayload | null): EvidenceMetric[] {
  const telemetry = payload?.telemetry ?? null;
  const comparison = payload?.comparison ?? null;
  const facts = parseAmdFacts(payload?.runtime_probe ?? null);
  const usedSample = payload?.used_sample ?? false;
  const measuredRun = payload?.amd.status === 'measured';
  const telemetrySource: SourceTag = usedSample ? 'sample' : telemetry ? 'measured' : 'not_available';
  const comparisonSource: SourceTag = comparison
    ? payload?.comparison_provenance.origin === 'artifacts'
      ? 'measured'
      : 'sample'
    : 'not_available';

  return [
    {
      label: 'AMD proof',
      value: measuredRun ? 'Measured' : payload?.amd.status === 'configured' ? 'Configured' : 'Pending',
      sub: measuredRun
        ? `${facts.gfx ?? 'AMD GPU'} · ${facts.vramGiB ?? 'VRAM captured'}`
        : payload?.amd.reason ?? 'No probe artifact loaded',
      source: measuredRun ? 'measured' : payload ? 'planned' : 'not_available',
      tone: measuredRun ? 'success' : 'warning',
    },
    {
      label: 'Gemma runtime',
      value:
        telemetry?.runtime.profile?.model_id ||
        facts.servedModel ||
        'not loaded',
      sub:
        telemetry?.runtime.profile?.provider === 'vllm-gemma'
          ? 'ROCm + vLLM local tier'
          : telemetry?.runtime.note ?? 'runtime profile unavailable',
      source: telemetry?.runtime.profile || facts.servedModel ? telemetrySource : 'not_available',
      tone: telemetry?.runtime.profile?.provider === 'vllm-gemma' ? 'success' : 'accent',
    },
    {
      label: 'Remote calls avoided',
      value: comparison ? String(comparison.comparison.remote_calls_avoided) : 'n/a',
      sub: comparison
        ? `${formatPctFromPercent(comparison.comparison.remote_call_reduction_percentage)} fewer remote calls`
        : 'comparison artifact missing',
      source: comparisonSource,
      tone: comparison ? 'success' : 'muted',
    },
    {
      label: 'Cost avoided',
      value: comparison ? formatUsd(comparison.comparison.configured_cost_avoided) : 'n/a',
      sub: comparison
        ? `${formatPctFromPercent(comparison.comparison.cost_reduction_percentage)} configured-cost reduction`
        : 'comparison artifact missing',
      source: comparisonSource,
      tone: comparison ? 'success' : 'muted',
    },
    {
      label: 'Final verified',
      value: telemetry ? formatPctFromFraction(telemetry.verification.final_verified_rate) : 'n/a',
      sub: comparison
        ? `always-remote baseline: ${formatPctFromPercent(comparison.always_remote.final_verified_rate)}`
        : `local: ${telemetry ? formatPctFromFraction(telemetry.verification.local_verified_rate) : 'n/a'}`,
      source: telemetrySource,
      tone: telemetry?.verification.final_verified_rate === 1 ? 'success' : 'warning',
    },
  ];
}

export function comparisonRows(comparison: FireworksComparisonArtifact | null) {
  if (!comparison) return [];
  const maxCost = Math.max(
    comparison.local_first.total_configured_remote_cost,
    comparison.always_remote.total_configured_remote_cost,
    0.000001,
  );
  const maxCalls = Math.max(
    comparison.local_first.remote_attempts,
    comparison.always_remote.remote_attempts,
    1,
  );

  return [
    {
      label: 'Remote calls',
      localFirst: String(comparison.local_first.remote_attempts),
      alwaysRemote: String(comparison.always_remote.remote_attempts),
      localWidth: (comparison.local_first.remote_attempts / maxCalls) * 100,
      remoteWidth: (comparison.always_remote.remote_attempts / maxCalls) * 100,
      delta: `${comparison.comparison.remote_calls_avoided} avoided`,
    },
    {
      label: 'Configured remote cost',
      localFirst: formatUsd(comparison.local_first.total_configured_remote_cost),
      alwaysRemote: formatUsd(comparison.always_remote.total_configured_remote_cost),
      localWidth: (comparison.local_first.total_configured_remote_cost / maxCost) * 100,
      remoteWidth: (comparison.always_remote.total_configured_remote_cost / maxCost) * 100,
      delta: `${formatUsd(comparison.comparison.configured_cost_avoided)} avoided`,
    },
    {
      label: 'Final verified rate',
      localFirst: formatPctFromPercent(comparison.local_first.final_verified_rate),
      alwaysRemote: formatPctFromPercent(comparison.always_remote.final_verified_rate),
      localWidth: comparison.local_first.final_verified_rate,
      remoteWidth: comparison.always_remote.final_verified_rate,
      delta: `${(comparison.local_first.final_verified_rate - comparison.always_remote.final_verified_rate).toFixed(1)} pt lift`,
    },
  ];
}
