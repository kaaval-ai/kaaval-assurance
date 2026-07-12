import { ReceiptText, TrendingDown } from 'lucide-react';
import type { FireworksComparisonArtifact, Provenance } from '../types';
import { comparisonRows } from '../evidence';
import { NotAvailable, SourceChip } from './Tags';

function BarPair({
  label,
  localFirst,
  alwaysRemote,
  localWidth,
  remoteWidth,
  delta,
}: ReturnType<typeof comparisonRows>[number]) {
  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between gap-2 text-[10px] font-mono">
        <span className="text-foreground">{label}</span>
        <span className="text-success">{delta}</span>
      </div>
      <div className="grid grid-cols-[96px_1fr_80px] gap-2 items-center text-[10px] font-mono">
        <span className="text-muted">local-first</span>
        <div className="h-2 rounded-full bg-elevated overflow-hidden border border-border/60">
          <div className="h-full rounded-full bg-success" style={{ width: `${Math.max(localWidth, 2)}%` }} />
        </div>
        <span className="text-foreground tabular-nums text-right">{localFirst}</span>

        <span className="text-muted">always-remote</span>
        <div className="h-2 rounded-full bg-elevated overflow-hidden border border-border/60">
          <div className="h-full rounded-full bg-warning" style={{ width: `${Math.max(remoteWidth, 2)}%` }} />
        </div>
        <span className="text-foreground tabular-nums text-right">{alwaysRemote}</span>
      </div>
    </div>
  );
}

export default function CostAvoidanceReceipt({
  comparison,
  provenance,
}: {
  comparison: FireworksComparisonArtifact | null;
  provenance: Provenance | null;
}) {
  const rows = comparisonRows(comparison);

  return (
    <section className="panel panel-sweep">
      <div className="panel-header">
        <span className="panel-title flex items-center gap-1.5">
          <ReceiptText className="w-3 h-3 text-success" />
          Kaaval Receipt · Cost Avoidance
        </span>
        <span className="flex items-center gap-1.5 text-[10px] font-mono text-muted">
          {provenance?.available ? provenance.artifact : 'comparison not loaded'}
          <SourceChip tag={provenance?.available ? 'measured' : 'not_available'} />
        </span>
      </div>
      <div className="panel-body">
        {!comparison ? (
          <div className="py-5 text-center">
            <NotAvailable note="run scripts/write_fireworks_comparison.sh to load the local-first vs always-remote receipt" />
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-[1fr_240px] gap-3">
            <div className="space-y-3">
              {rows.map((row) => (
                <BarPair key={row.label} {...row} />
              ))}
            </div>
            <div className="rounded-lg border border-success/30 bg-success/5 p-3">
              <div className="flex items-center gap-2 text-success">
                <TrendingDown className="w-4 h-4" aria-hidden="true" />
                <span className="text-[10px] font-mono uppercase tracking-wider">efficiency readout</span>
              </div>
              <div className="mt-2 text-2xl font-heading font-bold text-foreground tabular-nums">
                {comparison.comparison.remote_call_reduction_percentage.toFixed(1)}%
              </div>
              <p className="mt-1 text-[10px] font-mono text-muted leading-relaxed">
                fewer remote calls on the captured local-first smoke than the always-remote
                baseline, using configured pricing from recorded token counts.
              </p>
              <div className="mt-2 text-[10px] font-mono text-success">
                {comparison.comparison.remote_calls_avoided} calls avoided · ${comparison.comparison.configured_cost_avoided.toFixed(4)} saved
              </div>
            </div>
          </div>
        )}
        {comparison?.caveats?.length ? (
          <div className="mt-3 pt-2 border-t border-border/40 space-y-1">
            {comparison.caveats.map((caveat) => (
              <p key={caveat} className="text-[9px] font-mono text-muted leading-relaxed">
                {caveat}
              </p>
            ))}
          </div>
        ) : null}
      </div>
    </section>
  );
}
