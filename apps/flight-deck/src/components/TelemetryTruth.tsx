import { useState } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';
import type { TelemetrySummary } from '../types';
import { NotAvailable, SourceChip, ms, pct, usd } from './Tags';

/* Every value here is a stored artifact field with a source tag. One captured
   run yields point statistics — rendered as stats, never as a pretend time
   series, never with randomized sparklines or invented ± bands. */

const STAT_NOTES: Record<string, { what: string; why: string }> = {
  'Latency P50 / P95': {
    what: 'Request-level latency percentiles across the captured run (sum of attempt latencies per request).',
    why: 'Single-run point statistics — a time series appears only when multiple runs are captured.',
  },
  'Requests / attempts': {
    what: 'Requests in the run and total model attempts (escalations add attempts).',
    why: 'The gap between the two is the escalation workload the local tier could not absorb.',
  },
  'Local contract-conformance': {
    what: 'Requests whose local-tier answer passed every Layer-1 deterministic contract check (shape, enums, ranges, grounding rules), with no escalation. Not a semantic-correctness claim.',
    why: 'This is the fraction of traffic the cheap open-weight tier fully earned.',
  },
  'Final contract-conformance': {
    what: 'Requests whose final attempt passed Layer-1 contract checks. Deterministic conformance, not semantic truth — that boundary is by design.',
    why: 'The quality floor after escalation — what actually reached users contract-checked.',
  },
  'Escalation rate': {
    what: 'Requests escalated to the remote tier after a Layer-1 failure. Not an error rate: escalation is the designed recovery path.',
    why: 'Sustained escalation is a cost signal and feeds Layer-2 drift tracking.',
  },
  'Pre-route remote rate': {
    what: 'Requests routed straight to the remote tier by drift policy, skipping the local attempt.',
    why: 'Visible proof of the closed loop: high-drift categories stop burning local attempts.',
  },
  'Cost per conformant answer': {
    what: 'Generation cost divided by contract-conformant requests, using configured per-token pricing.',
    why: 'The economic headline: what one provably-contract-satisfying answer costs.',
  },
  'Calibration FP rate': {
    what: 'Fraction of known-good gold answers the audit challenger wrongly flagged.',
    why: 'This only detects over-eager critics. The sampled audit is display-only and does not feed routing; two-sided calibration is roadmap work.',
  },
};

function Stat({
  label,
  value,
  source,
  expanded,
  onToggle,
}: {
  label: string;
  value: string;
  source: 'measured' | 'configured' | 'not_available' | 'planned';
  expanded: boolean;
  onToggle: () => void;
}) {
  const note = STAT_NOTES[label];
  return (
    <div>
      <div
        onClick={onToggle}
        className="flex items-center gap-2 px-2 py-1.5 rounded border border-border/50 hover:bg-elevated/50 transition-colors duration-200 cursor-pointer select-none active:scale-[0.99]"
      >
        <span className="text-muted text-[9px] uppercase tracking-wider font-mono flex-1">{label}</span>
        <span className="text-foreground text-[11px] font-mono font-semibold tabular-nums">{value}</span>
        <SourceChip tag={source} />
        <span className="text-muted">{expanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}</span>
      </div>
      {expanded && note && (
        <div className="mx-2 mt-1 mb-1.5 px-2 py-1.5 rounded bg-elevated border border-border/50 text-[10px] font-mono space-y-1 animate-[metric-up_0.2s_ease-out]">
          <p className="text-foreground/80 leading-relaxed">{note.what}</p>
          <p className="text-muted leading-relaxed pt-1 border-t border-border/30">{note.why}</p>
        </div>
      )}
    </div>
  );
}

export default function TelemetryTruth({ telemetry, usedSample }: { telemetry: TelemetrySummary | null; usedSample: boolean }) {
  const [expanded, setExpanded] = useState<string | null>(null);
  const [tab, setTab] = useState<'stats' | 'claims'>('stats');

  if (!telemetry) {
    return (
      <div className="panel panel-sweep">
        <div className="panel-header"><span className="panel-title">Telemetry Truth</span></div>
        <div className="panel-body py-6 text-center text-muted text-xs">
          No telemetry artifact loaded. <NotAvailable />
        </div>
      </div>
    );
  }

  const m = telemetry;
  const baseline = m.cost.remote_calls_avoided_rate;
  const stats: { label: string; value: string; source: 'measured' | 'not_available' }[] = [
    { label: 'Latency P50 / P95', value: `${ms(m.latency_ms_p50)} / ${ms(m.latency_ms_p95)}`, source: 'measured' },
    { label: 'Requests / attempts', value: `${m.requests} / ${m.attempts}`, source: 'measured' },
    { label: 'Local contract-conformance', value: pct(m.verification.local_verified_rate), source: 'measured' },
    { label: 'Final contract-conformance', value: pct(m.verification.final_verified_rate), source: 'measured' },
    { label: 'Escalation rate', value: pct(m.routing.escalation_rate), source: 'measured' },
    { label: 'Pre-route remote rate', value: pct(m.routing.preroute_remote_rate), source: 'measured' },
    { label: 'Cost per conformant answer', value: usd(m.cost.cost_per_verified_answer_usd), source: 'measured' },
    {
      label: 'Remote calls avoided',
      value: baseline === null ? 'n/a (no always-remote baseline)' : pct(baseline),
      source: baseline === null ? 'not_available' : 'measured',
    },
    {
      label: 'Calibration FP rate',
      value:
        m.audit.enabled && m.audit.calibration_fp_rate !== null
          ? `${pct(m.audit.calibration_fp_rate)} (threshold ${pct(m.audit.calibration_threshold)})`
          : 'no audit in this run',
      source: m.audit.enabled && m.audit.calibration_fp_rate !== null ? 'measured' : 'not_available',
    },
    {
      label: 'Audit sampled',
      value: m.audit.enabled ? `${m.audit.sampled}/${m.audit.accepted_answers} accepted` : 'no audit in this run',
      source: m.audit.enabled ? 'measured' : 'not_available',
    },
    {
      label: 'High-drift categories',
      value: m.routing.high_drift_categories.join(', ') || 'none',
      source: 'measured',
    },
  ];

  return (
    <div className="panel panel-sweep">
      <div className="panel-header">
        <span className="panel-title">Telemetry Truth</span>
        <div className="flex items-center gap-2">
          <div className="flex items-center bg-elevated rounded border border-border p-0.5">
            {(['stats', 'claims'] as const).map((t) => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className={`px-1.5 py-0.5 rounded text-[9px] font-mono font-medium transition-all duration-150 active:scale-95 capitalize ${
                  tab === t ? 'bg-accent text-white shadow-sm' : 'text-muted hover:text-foreground'
                }`}
              >
                {t}
              </button>
            ))}
          </div>
          <span className="text-[10px] font-mono text-muted">single captured run · point statistics</span>
        </div>
      </div>
      <div className="panel-body space-y-1">
        {tab === 'stats' ? (
          stats.map((s) => (
            <Stat
              key={s.label}
              label={s.label}
              value={s.value}
              source={s.source === 'measured' && usedSample ? 'sample' : s.source as any}
              expanded={expanded === s.label}
              onToggle={() => setExpanded(expanded === s.label ? null : s.label)}
            />
          ))
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-[10px] font-mono">
              <thead>
                <tr className="text-muted border-b border-border">
                  <th className="text-left py-1.5 pr-2 font-semibold">Claim</th>
                  <th className="text-left px-1.5 py-1.5 font-semibold">Value</th>
                  <th className="text-right pl-1.5 py-1.5 font-semibold">Source</th>
                </tr>
              </thead>
              <tbody>
                {m.claims.map((c) => (
                  <tr key={c.claim} className="border-b border-border/40">
                    <td className="py-1.5 pr-2 text-foreground">{c.claim}</td>
                    <td className="px-1.5 py-1.5 text-foreground/80">{c.value}</td>
                    <td className="pl-1.5 py-1.5 text-right"><SourceChip tag={c.source === 'measured' && usedSample ? 'sample' : c.source} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
