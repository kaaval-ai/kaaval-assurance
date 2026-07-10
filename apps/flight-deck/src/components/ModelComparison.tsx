import { BarChart3 } from 'lucide-react';
import type { TelemetrySummary } from '../types';
import { NotAvailable, SourceChip, ms, pct } from './Tags';

/* Local tier vs remote escalation tier, from captured measurements only.
   A side with no captured attempts renders as not available — never as a
   plausible default. No accuracy or hallucination columns: those are not
   measured by this system. */

interface TierStats {
  provider: string;
  modelId: string;
  attempts: number;
  verifiedRate: number;
  meanLatencyMs: number;
  totalTokens: number;
  costUsd: number;
}

function tierStats(telemetry: TelemetrySummary, tier: 'local' | 'remote'): TierStats | null {
  const attempts = telemetry.attempts_detail.filter((a) => a.tier === tier);
  if (attempts.length === 0) return null;
  const first = attempts[0];
  return {
    provider: first.provider,
    modelId: first.model_id,
    attempts: attempts.length,
    verifiedRate: attempts.filter((a) => a.verifier_passed).length / attempts.length,
    meanLatencyMs: attempts.reduce((s, a) => s + a.latency_ms, 0) / attempts.length,
    totalTokens: attempts.reduce((s, a) => s + a.total_tokens, 0),
    costUsd: attempts.reduce((s, a) => s + a.cost_usd, 0),
  };
}

function TierColumn({ title, stats }: { title: string; stats: TierStats | null }) {
  return (
    <div className="flex-1 min-w-[220px] px-3 py-2 rounded border border-border/60 bg-surface/40">
      <div className="flex items-center justify-between mb-1.5">
        <span className="text-[10px] font-mono uppercase tracking-wider text-muted">{title}</span>
        {stats ? <SourceChip tag="measured" /> : <SourceChip tag="not_available" />}
      </div>
      {stats ? (
        <div className="space-y-1 text-[10px] font-mono">
          <div className="flex justify-between"><span className="text-muted">provider / model</span><span className="text-foreground truncate ml-2">{stats.provider} · {stats.modelId}</span></div>
          <div className="flex justify-between"><span className="text-muted">attempts</span><span className="text-foreground tabular-nums">{stats.attempts}</span></div>
          <div className="flex justify-between"><span className="text-muted">Layer-1 verified rate</span><span className="text-foreground tabular-nums">{pct(stats.verifiedRate)}</span></div>
          <div className="flex justify-between"><span className="text-muted">mean latency</span><span className="text-foreground tabular-nums">{ms(stats.meanLatencyMs)}</span></div>
          <div className="flex justify-between"><span className="text-muted">total tokens</span><span className="text-foreground tabular-nums">{stats.totalTokens}</span></div>
          <div className="flex justify-between">
            <span className="text-muted">cost (configured pricing)</span>
            <span className="text-foreground tabular-nums">${stats.costUsd.toFixed(4)}</span>
          </div>
        </div>
      ) : (
        <div className="py-4 text-center">
          <NotAvailable note="no captured attempts for this tier in the loaded artifact" />
        </div>
      )}
    </div>
  );
}

export default function ModelComparison({ telemetry }: { telemetry: TelemetrySummary | null }) {
  const local = telemetry ? tierStats(telemetry, 'local') : null;
  const remote = telemetry ? tierStats(telemetry, 'remote') : null;

  return (
    <div className="panel panel-sweep">
      <div className="panel-header">
        <span className="panel-title flex items-center gap-1.5">
          <BarChart3 className="w-3 h-3 text-accent" />
          Tier Comparison
        </span>
        <span className="text-[10px] font-mono text-muted">
          local tier vs escalation tier · captured measurements only
        </span>
      </div>
      <div className="panel-body">
        {!telemetry ? (
          <div className="py-6 text-center text-muted text-xs">No telemetry artifact loaded.</div>
        ) : (
          <div className="flex flex-col sm:flex-row gap-2">
            <TierColumn title="Local tier (Gemma-first)" stats={local} />
            <TierColumn title="Remote tier (Fireworks escalation)" stats={remote} />
          </div>
        )}
        <p className="pt-2 text-[9px] font-mono text-muted leading-relaxed">
          Quality here means Layer-1 contract verification outcomes. This system does not
          measure accuracy or hallucination rates; semantic risk is estimated separately by
          the calibrated, sampled Layer 3 audit.
        </p>
      </div>
    </div>
  );
}
