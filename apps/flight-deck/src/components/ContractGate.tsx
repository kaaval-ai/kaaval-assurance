import { useState } from 'react';
import { ShieldCheck, ShieldX, ChevronDown, ChevronRight, ScrollText } from 'lucide-react';
import type { TelemetrySummary } from '../types';
import { CONTRACTS } from '../mock/data';
import { pct } from './Tags';

/* The four real task contracts, joined with measured per-category outcomes
   from the loaded telemetry artifact. Layer 1 validates shape and
   constraints — never semantic truth (that gap is Layer 3's job). */

interface CategoryStats {
  attempts: number;
  passed: number;
  failures: string[];
  drift: number | null;
}

function statsFor(telemetry: TelemetrySummary | null, category: string): CategoryStats {
  if (!telemetry) return { attempts: 0, passed: 0, failures: [], drift: null };
  const attempts = telemetry.attempts_detail.filter((a) => a.category === category);
  const failures = [...new Set(attempts.flatMap((a) => a.verifier_failures))];
  return {
    attempts: attempts.length,
    passed: attempts.filter((a) => a.verifier_passed).length,
    failures,
    drift: telemetry.routing.ewma_drift_by_category[category] ?? null,
  };
}

export default function ContractGate({ telemetry }: { telemetry: TelemetrySummary | null }) {
  const [expanded, setExpanded] = useState<string | null>(null);

  return (
    <div className="panel panel-sweep">
      <div className="panel-header">
        <span className="panel-title">Contract Gate</span>
        <span className="text-[10px] font-mono text-muted">{CONTRACTS.length} task contracts</span>
      </div>
      <div className="panel-body space-y-1.5">
        {CONTRACTS.map((c) => {
          const isExpanded = expanded === c.id;
          const stats = statsFor(telemetry, c.category);
          const hasFailures = stats.failures.length > 0;
          return (
            <div key={c.id}>
              <div
                onClick={() => setExpanded(isExpanded ? null : c.id)}
                className={`flex items-center gap-2 px-2 py-1.5 rounded border transition-colors duration-200 cursor-pointer select-none active:scale-[0.99] ${
                  hasFailures ? 'border-warning/20 bg-warning/5' : 'border-border hover:border-accent/20'
                }`}
              >
                <span className="flex-shrink-0 text-accent"><ScrollText className="w-3 h-3" /></span>
                <span className="font-mono text-[11px] flex-1 truncate text-foreground">{c.label}</span>
                {stats.attempts > 0 ? (
                  <span className="text-[10px] font-mono tabular-nums text-muted">
                    {stats.passed}/{stats.attempts} passed
                  </span>
                ) : (
                  <span className="text-[9px] font-mono text-muted italic">no attempts in artifact</span>
                )}
                {stats.attempts > 0 && (
                  stats.passed === stats.attempts
                    ? <ShieldCheck className="w-3 h-3 text-success flex-shrink-0" />
                    : <ShieldX className="w-3 h-3 text-warning flex-shrink-0" />
                )}
                <span className="text-muted flex-shrink-0">
                  {isExpanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
                </span>
              </div>
              {isExpanded && (
                <div className="mx-2 mt-1 mb-1.5 px-2 py-1.5 rounded bg-elevated border border-border/50 text-[10px] font-mono space-y-1.5 animate-[metric-up_0.2s_ease-out]">
                  <p className="text-muted leading-relaxed">{c.description}</p>
                  <div>
                    <span className="text-muted text-[9px] uppercase tracking-wider">Layer 1 checks</span>
                    <div className="flex flex-wrap gap-1 mt-1">
                      {c.checks.map((check) => (
                        <span
                          key={check}
                          className={`px-1 py-0.5 rounded border text-[9px] leading-none ${
                            stats.failures.includes(check)
                              ? 'border-destructive/40 text-destructive bg-destructive/5'
                              : 'border-border/50 text-muted bg-elevated'
                          }`}
                        >
                          {check}
                        </span>
                      ))}
                    </div>
                  </div>
                  {stats.failures.length > 0 && (
                    <div className="pt-1 border-t border-border/30 text-warning">
                      failed checks observed: {stats.failures.join(', ')}
                    </div>
                  )}
                  {stats.drift !== null && (
                    <div className="flex items-center justify-between pt-1 border-t border-border/30">
                      <span className="text-muted">Layer-2 EWMA drift</span>
                      <span className={`tabular-nums ${stats.drift >= 0.5 ? 'text-destructive' : stats.drift >= 0.2 ? 'text-warning' : 'text-success'}`}>
                        {stats.drift.toFixed(2)}
                      </span>
                    </div>
                  )}
                  {stats.attempts > 0 && (
                    <div className="flex items-center justify-between">
                      <span className="text-muted">attempt pass rate</span>
                      <span className="text-foreground tabular-nums">{pct(stats.passed / stats.attempts)}</span>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
        <p className="px-2 pt-1 text-[9px] font-mono text-muted leading-relaxed">
          Layer 1 validates output shape and constraints (JSON, required fields, enums,
          ranges) deterministically. It does not certify semantic truth — semantic risk
          is estimated statistically by the calibrated, sampled Layer 3 audit.
        </p>
      </div>
    </div>
  );
}
