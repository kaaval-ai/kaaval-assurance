import { Archive, KeyRound, Radio, ShieldCheck } from 'lucide-react';
import type { DataLabel } from '../types';
import { DataLabelBadge } from './Tags';

interface EvidenceModeBannerProps {
  mode: 'captured' | 'live';
  label: DataLabel | null;
}

export default function EvidenceModeBanner({ mode, label }: EvidenceModeBannerProps) {
  const isLive = mode === 'live';

  return (
    <section className="px-3 md:px-4 pt-3">
      <div className="panel border-accent/30 bg-surface/95 px-3 py-2 md:px-4 md:py-2.5">
        <div className="flex flex-col gap-2 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex min-w-0 items-start gap-2.5">
            <div className={`mt-0.5 rounded border p-1.5 ${isLive ? 'border-warning/40 bg-warning/10 text-warning' : 'border-success/40 bg-success/10 text-success'}`}>
              {isLive ? <Radio className="h-3.5 w-3.5" /> : <Archive className="h-3.5 w-3.5" />}
            </div>
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <p className="font-mono text-[11px] font-bold uppercase tracking-wider text-foreground">
                  {isLive ? 'Live execution guard' : 'Hosted replay evidence'}
                </p>
                {!isLive && label && <DataLabelBadge label={label} />}
              </div>
              <p className="mt-1 text-[11px] leading-relaxed text-muted md:text-xs">
                {isLive
                  ? 'Live model calls require provider configuration; Fireworks additionally requires operator authorization and per-run spend confirmation.'
                  : 'The public demo can run without secrets or paid calls; every number is replayed from captured evidence artifacts.'}
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-1.5 text-[10px] font-mono text-muted sm:grid-cols-3 lg:min-w-[520px]">
            <span className="inline-flex items-center gap-1 rounded border border-border bg-elevated/50 px-2 py-1">
              <ShieldCheck className="h-3 w-3 text-success" />
              {isLive ? 'Layer 1 still verifies every answer' : 'No API key required'}
            </span>
            <span className="inline-flex items-center gap-1 rounded border border-border bg-elevated/50 px-2 py-1">
              <KeyRound className="h-3 w-3 text-accent" />
              {isLive ? 'Operator gate + run confirmation' : 'No hosted spend path'}
            </span>
            <span className="inline-flex items-center gap-1 rounded border border-border bg-elevated/50 px-2 py-1">
              <Archive className="h-3 w-3 text-warning" />
              {isLive ? 'Exports isolated per run' : 'Artifacts are the source of truth'}
            </span>
          </div>
        </div>
      </div>
    </section>
  );
}
