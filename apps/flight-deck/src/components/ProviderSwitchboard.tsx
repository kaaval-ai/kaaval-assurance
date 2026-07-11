import { useState } from 'react';
import { Server, ChevronDown, ChevronRight, Activity } from 'lucide-react';
import type { TelemetrySummary } from '../types';
import { NotAvailable, SourceChip, ms, pct } from './Tags';

/* Providers derive from telemetry attempts — only tiers that actually served
   requests appear, plus the configured runtime profile when present.
   No invented health, RPM, quota, or error-rate numbers. */

interface ProviderRow {
  key: string;
  provider: string;
  modelId: string;
  tier: string;
  attempts: number;
  verifiedRate: number;
  meanLatencyMs: number;
  totalCostUsd: number;
}

function deriveProviders(telemetry: TelemetrySummary): ProviderRow[] {
  const groups = new Map<string, ProviderRow & { passed: number; latencySum: number }>();
  for (const a of telemetry.attempts_detail) {
    const key = `${a.provider}·${a.model_id}·${a.tier}`;
    const g = groups.get(key) ?? {
      key,
      provider: a.provider,
      modelId: a.model_id,
      tier: a.tier,
      attempts: 0,
      passed: 0,
      latencySum: 0,
      verifiedRate: 0,
      meanLatencyMs: 0,
      totalCostUsd: 0,
    };
    g.attempts += 1;
    g.passed += a.verifier_passed ? 1 : 0;
    g.latencySum += a.latency_ms;
    g.totalCostUsd += a.cost_usd;
    groups.set(key, g);
  }
  return [...groups.values()].map((g) => ({
    ...g,
    verifiedRate: g.attempts ? g.passed / g.attempts : 0,
    meanLatencyMs: g.attempts ? g.latencySum / g.attempts : 0,
  }));
}

export default function ProviderSwitchboard({ telemetry, usedSample }: { telemetry: TelemetrySummary | null; usedSample: boolean }) {
  const [expanded, setExpanded] = useState<string | null>(null);
  const providers = telemetry ? deriveProviders(telemetry) : [];
  const profile = telemetry?.runtime.profile ?? null;

  return (
    <div className="panel panel-sweep">
      <div className="panel-header">
        <span className="panel-title">Provider Switchboard</span>
        <span className="text-[10px] font-mono text-muted">
          {providers.length} provider{providers.length === 1 ? '' : 's'} in this run
        </span>
      </div>
      <div className="panel-body space-y-1.5">
        {providers.length === 0 ? (
          <div className="py-6 text-center text-muted text-xs">
            No provider attempts in the loaded artifact.
          </div>
        ) : (
          providers.map((p) => {
            const isExpanded = expanded === p.key;
            return (
              <div key={p.key}>
                <div
                  onClick={() => setExpanded(isExpanded ? null : p.key)}
                  className="flex items-center gap-2 px-2 py-1.5 rounded border border-border hover:border-accent/20 transition-colors duration-200 cursor-pointer select-none active:scale-[0.99]"
                >
                  <Server className="w-3 h-3 text-accent flex-shrink-0" />
                  <span className="font-mono text-[11px] text-foreground truncate">
                    {p.provider}
                  </span>
                  <span className="font-mono text-[10px] text-muted truncate">{p.modelId}</span>
                  <span className={`px-1 py-0.5 rounded text-[9px] font-mono uppercase ${p.tier === 'local' ? 'bg-accent/10 text-accent' : 'bg-warning/10 text-warning'}`}>
                    {p.tier}
                  </span>
                  <div className="ml-auto hidden sm:flex items-center gap-2 text-[10px] font-mono tabular-nums text-muted">
                    <span>{p.attempts} attempt{p.attempts === 1 ? '' : 's'}</span>
                    <span className="text-border">|</span>
                    <span className="flex items-center gap-0.5">
                      <Activity className="w-2.5 h-2.5" />
                      {ms(p.meanLatencyMs)} mean
                    </span>
                  </div>
                  <SourceChip tag={usedSample ? 'sample' : 'measured'} />
                  <span className="text-muted flex-shrink-0">
                    {isExpanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
                  </span>
                </div>
                {isExpanded && (
                  <div className="mx-2 mt-1 mb-1.5 px-2 py-1.5 rounded bg-elevated border border-border/50 text-[10px] font-mono space-y-1 animate-[metric-up_0.2s_ease-out]">
                    <div className="flex items-center justify-between">
                      <span className="text-muted">Layer-1 conformance rate</span>
                      <span className="text-foreground tabular-nums">{pct(p.verifiedRate)}</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-muted">Mean latency (measured)</span>
                      <span className="text-foreground tabular-nums">{ms(p.meanLatencyMs)}</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-muted">Cost (configured pricing)</span>
                      <span className="text-foreground tabular-nums">${p.totalCostUsd.toFixed(4)}</span>
                    </div>
                  </div>
                )}
              </div>
            );
          })
        )}

        {/* Configured local endpoint from the runtime profile */}
        <div className="px-2 py-1.5 rounded border border-dashed border-border/60 text-[10px] font-mono">
          <div className="flex items-center gap-2">
            <span className="text-muted">Local endpoint:</span>
            {profile ? (
              <>
                <span className="text-foreground">
                  {profile.endpoint_type || 'unknown'}
                  {profile.base_url_host ? ` @ ${profile.base_url_host}` : ''}
                </span>
                <span className="text-muted">· {profile.model_family ?? 'model'} · target {profile.hardware_target}</span>
                <SourceChip tag="configured" />
              </>
            ) : (
              <>
                <span className="text-foreground">mock (deterministic stand-in)</span>
                <SourceChip tag={telemetry ? 'planned' : 'not_available'} />
                {telemetry && (
                  <span className="text-muted">Gemma via ROCm + vLLM is the AMD deployment target</span>
                )}
              </>
            )}
          </div>
        </div>
        {telemetry && !providers.some((p) => p.provider === 'fireworks') && (
          <div className="px-2 text-[9px] font-mono text-muted">
            Fireworks escalation tier: no attempts in this run.{' '}
            <NotAvailable note="shown only when escalations exist or the tier is configured" />
          </div>
        )}
      </div>
    </div>
  );
}
