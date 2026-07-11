import { AlertTriangle, BadgeCheck, GitBranch, Radar, WalletCards } from 'lucide-react';
import type { DashboardPayload } from '../types';
import { SourceChip } from './Tags';

const STEPS = [
  {
    title: 'Struggle',
    body: 'A local/open-weight tier can fail a hard contract case.',
    icon: AlertTriangle,
  },
  {
    title: 'Catch',
    body: 'Layer 1 names the failed check instead of trusting fluent text.',
    icon: BadgeCheck,
  },
  {
    title: 'Rescue',
    body: 'Only failed answers escalate to the remote tier.',
    icon: GitBranch,
  },
  {
    title: 'Adapt',
    body: 'EWMA drift shifts routing when a category keeps failing.',
    icon: Radar,
  },
  {
    title: 'Prove',
    body: 'Receipts show cost, verification, AMD runtime, and provenance.',
    icon: WalletCards,
  },
] as const;

export default function DemoScriptRail({ payload }: { payload: DashboardPayload | null }) {
  const hasEscalation = Boolean(payload?.telemetry && payload.telemetry.routing.escalation_rate > 0);
  const hasDrift = Boolean(
    payload?.telemetry &&
      Object.values(payload.telemetry.routing.ewma_drift_by_category).some((v) => v > 0),
  );
  const activeIndex = hasDrift ? 3 : hasEscalation ? 2 : payload?.telemetry ? 4 : 0;

  return (
    <section className="panel">
      <div className="panel-header">
        <span className="panel-title">Assurance path</span>
        <span className="text-[10px] font-mono text-muted">
          failure-aware runtime proof <SourceChip tag={payload ? 'measured' : 'not_available'} />
        </span>
      </div>
      <div className="panel-body">
        <div className="grid grid-cols-1 md:grid-cols-5 gap-2">
          {STEPS.map((step, index) => {
            const Icon = step.icon;
            const active = index === activeIndex;
            return (
              <div
                key={step.title}
                className={`relative rounded-lg border px-2.5 py-2 transition-colors ${
                  active
                    ? 'border-accent/50 bg-accent/10'
                    : 'border-border/50 bg-surface/40'
                }`}
              >
                <div className="flex items-center gap-1.5">
                  <span className={`flex h-6 w-6 items-center justify-center rounded-full border text-[10px] font-mono ${
                    active ? 'border-accent text-accent' : 'border-border text-muted'
                  }`}>
                    {index + 1}
                  </span>
                  <Icon className={active ? 'w-3.5 h-3.5 text-accent' : 'w-3.5 h-3.5 text-muted'} aria-hidden="true" />
                  <span className="text-[11px] font-heading font-semibold uppercase tracking-wider text-foreground">
                    {step.title}
                  </span>
                </div>
                <p className="mt-1.5 text-[10px] font-mono leading-snug text-muted">
                  {step.body}
                </p>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
