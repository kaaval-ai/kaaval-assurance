import { AlertTriangle, CheckCircle, ReceiptText, XCircle } from 'lucide-react';
import type { LiveRunResponse } from '../types';
import { SourceChip, usd } from './Tags';

export default function LiveAssuranceReceipt({ run }: { run: LiveRunResponse }) {
  const caught = run.trajectory.filter(
    (row) => row.attempt_status === 'provider_error' || !row.verifier_passed,
  );
  const providerPath = run.trajectory
    .map((row) => `${row.provider}/${row.model_id}`)
    .join(' → ');

  return (
    <section className={`panel ${run.result.status === 'accepted' ? 'border-success/40' : 'border-destructive/50'}`}>
      <div className="panel-header">
        <span className="panel-title flex items-center gap-1.5">
          <ReceiptText className="h-3.5 w-3.5 text-accent" /> Kaaval Receipt
        </span>
        <SourceChip tag="measured" />
      </div>
      <div className="panel-body space-y-3 text-[10px] font-mono">
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-4">
          <div className="rounded border border-border/60 bg-elevated/40 p-2">
            <div className="text-muted uppercase tracking-wider">Decision</div>
            <div className={`mt-1 flex items-center gap-1 font-semibold ${run.result.status === 'accepted' ? 'text-success' : 'text-destructive'}`}>
              {run.result.status === 'accepted' ? <CheckCircle className="h-3 w-3" /> : <XCircle className="h-3 w-3" />}
              {run.result.status === 'accepted' ? 'contract-conformant' : 'NO SAFE ANSWER'}
            </div>
          </div>
          <div className="rounded border border-border/60 bg-elevated/40 p-2">
            <div className="text-muted uppercase tracking-wider">Attempts / checks</div>
            <div className="mt-1 text-foreground tabular-nums">{run.result.attempts} / {run.result.checks_run}</div>
          </div>
          <div className="rounded border border-border/60 bg-elevated/40 p-2">
            <div className="text-muted uppercase tracking-wider">Run cost</div>
            <div className="mt-1 text-foreground tabular-nums">{usd(run.telemetry.cost.total_cost_usd)}</div>
          </div>
          <div className="rounded border border-border/60 bg-elevated/40 p-2">
            <div className="text-muted uppercase tracking-wider">Receipt ID</div>
            <div className="mt-1 truncate text-foreground" title={run.run_id}>{run.run_id}</div>
          </div>
        </div>

        <div className="rounded border border-border/60 bg-elevated/30 p-2 text-muted">
          <div><span className="text-foreground">provider path:</span> {providerPath || 'not available'}</div>
          <div className="mt-1"><span className="text-foreground">routing:</span> {run.result.routing_reason}</div>
        </div>

        {caught.length > 0 ? (
          <div className="rounded border border-warning/40 bg-warning/5 p-2">
            <div className="mb-1.5 flex items-center gap-1 font-semibold uppercase tracking-wider text-warning">
              <AlertTriangle className="h-3 w-3" /> Caught before acceptance
            </div>
            <div className="space-y-1">
              {caught.map((row, index) => {
                const failures = row.attempt_status === 'provider_error'
                  ? [`transport:${row.error_type ?? 'provider_error'}`]
                  : row.verifier_failures;
                return (
                  <div key={`${row.request_id}-${row.tier}-${index}`} className="break-words text-foreground">
                    {row.provider}/{row.model_id}: {failures.join(', ') || 'contract check failed'}
                  </div>
                );
              })}
            </div>
          </div>
        ) : (
          <div className="rounded border border-success/30 bg-success/5 p-2 text-success">
            No failed attempt or transport error occurred in this run.
          </div>
        )}
      </div>
    </section>
  );
}
