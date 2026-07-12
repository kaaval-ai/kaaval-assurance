import { Cpu, Gauge, ShieldCheck, Sparkles, WalletCards } from 'lucide-react';
import type { DashboardPayload } from '../types';
import { headlineMetrics } from '../evidence';
import { DataLabelBadge, SourceChip } from './Tags';

const ICONS = [Cpu, Sparkles, Gauge, WalletCards, ShieldCheck];

const TONE_CLASS = {
  success: 'border-success/40 bg-success/5 text-success shadow-[0_0_24px_rgba(52,199,89,0.08)]',
  accent: 'border-accent/40 bg-accent/5 text-accent shadow-[0_0_24px_rgba(0,212,255,0.08)]',
  warning: 'border-warning/40 bg-warning/5 text-warning',
  destructive: 'border-destructive/40 bg-destructive/5 text-destructive',
  muted: 'border-border bg-elevated/40 text-muted',
} as const;

export default function ProofStrip({ payload }: { payload: DashboardPayload | null }) {
  const metrics = headlineMetrics(payload);

  return (
    <section className="relative overflow-hidden rounded-xl border border-accent/30 bg-[radial-gradient(circle_at_top_left,rgba(0,212,255,0.16),transparent_35%),linear-gradient(135deg,rgba(28,33,40,0.96),rgba(13,17,23,0.98))] p-3 md:p-4 shadow-[0_0_50px_rgba(0,212,255,0.08)]">
      <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-accent to-transparent" />
      <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <div className="space-y-1.5">
          <div className="flex items-center gap-2 flex-wrap">
            <DataLabelBadge label={payload?.label ?? 'UNAVAILABLE'} />
            <span className="text-[10px] font-mono uppercase tracking-[0.32em] text-muted">
              captured assurance evidence
            </span>
          </div>
          <h1 className="text-xl md:text-2xl font-heading font-bold tracking-tight text-foreground">
            Kaaval proves the local tier earned the answer.
          </h1>
          <p className="max-w-3xl text-xs md:text-sm font-mono text-muted leading-relaxed">
            Local Gemma/open-weight inference is routed through deterministic task contracts,
            escalates only when verification fails, and leaves a replayable receipt for every claim.
          </p>
        </div>
        <div className="text-[10px] font-mono text-muted lg:text-right">
          <div>bundle: {payload?.bundle_id || payload?.telemetry?.run_id || 'not loaded'}</div>
          <div>{payload?.comparison ? 'cost comparison loaded' : 'cost comparison unavailable'}</div>
        </div>
      </div>

      <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-2">
        {metrics.filter(m => ['AMD proof', 'Gemma runtime', 'Cost avoided', 'Final contract-conformance'].includes(m.label)).map((metric) => {
          const Icon = ICONS[metrics.indexOf(metric)] ?? ShieldCheck;
          return (
            <div key={metric.label} className={`rounded-lg border px-3 py-2.5 ${TONE_CLASS[metric.tone]}`}>
              <div className="flex items-center justify-between gap-2">
                <span className="text-[10px] font-mono uppercase tracking-wider opacity-80">{metric.label}</span>
                <Icon className="w-3.5 h-3.5" aria-hidden="true" />
              </div>
              <div className="mt-1 text-lg font-heading font-bold tabular-nums text-foreground">
                {metric.value}
              </div>
              <div className="mt-1 flex items-start justify-between gap-2">
                <p className="text-[10px] font-mono leading-snug text-muted">{metric.sub}</p>
                <SourceChip tag={metric.source} />
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
