import { useState } from 'react';
import { CheckCircle, XCircle, Circle, ChevronDown, ChevronRight, CornerDownRight } from 'lucide-react';
import type { TelemetrySummary, TrajectoryRow } from '../types';
import { PIPELINE_STAGES } from '../mock/data';
import { ms } from './Tags';

/* Pipeline stages derive entirely from the trajectory rows of one request.
   The escalation stage renders only when an escalation actually happened. */

interface Stage {
  id: string;
  label: string;
  desc: string;
  status: 'passed' | 'failed' | 'idle';
  detail: string;
  durationMs: number | null;
}

function buildStages(rows: TrajectoryRow[], telemetry: TelemetrySummary | null): Stage[] {
  const meta = Object.fromEntries(PIPELINE_STAGES.map((s) => [s.id, s]));
  const local = rows.find((r) => r.tier === 'local') ?? null;
  const remote = rows.find((r) => r.tier === 'remote') ?? null;
  const finalRow = rows[rows.length - 1] ?? null;
  const escalated = rows.some((r) => r.escalated);
  const drift = telemetry?.routing.ewma_drift_by_category?.[finalRow?.category ?? ''] ?? null;
  const audited = rows.some((r) => r.audit_sampled);

  const stages: Stage[] = [
    {
      ...meta.request,
      status: 'passed',
      detail: finalRow ? `contract ${finalRow.contract_id} v${finalRow.contract_version}` : '',
      durationMs: null,
    },
    {
      ...meta.router,
      status: 'passed',
      detail: local ? 'primary tier first' : 'pre-routed escalation tier',
      durationMs: null,
    },
  ];
  if (local) {
    stages.push({
      ...meta.local,
      label: `${local.provider} primary tier`,
      desc: 'The configured primary runtime generates the first candidate answer.',
      status: 'passed',
      detail: `${local.provider}/${local.model_id}`,
      durationMs: local.latency_ms,
    });
    stages.push({
      ...meta.verify,
      status: local.verifier_passed ? 'passed' : 'failed',
      detail: local.verifier_passed
        ? 'all contract checks passed'
        : `failed: ${local.verifier_failures.join(', ')}`,
      durationMs: null,
    });
  }
  if (escalated && remote) {
    stages.push({
      ...meta.escalate,
      label: `${remote.provider} escalation tier`,
      desc: 'A failed primary answer routes to the configured escalation runtime and returns through the same contract gate.',
      status: remote.verifier_passed ? 'passed' : 'failed',
      detail: `${remote.provider}/${remote.model_id} — checked by the same Layer 1 gate${remote.verifier_passed ? ': passed' : `: failed (${remote.verifier_failures.join(', ')})`}`,
      durationMs: remote.latency_ms,
    });
  } else if (!local && remote) {
    // pre-routed remote request (no local attempt)
    stages.push({
      ...meta.escalate,
      label: `${remote.provider} escalation tier (pre-routed)`,
      status: remote.verifier_passed ? 'passed' : 'failed',
      detail: `${remote.provider}/${remote.model_id}`,
      durationMs: remote.latency_ms,
    });
  }
  stages.push({
    ...meta.persist,
    status: 'passed',
    detail: `${rows.length} replayable row${rows.length === 1 ? '' : 's'} written`,
    durationMs: null,
  });
  stages.push({
    ...meta.drift,
    status: 'passed',
    detail:
      drift !== null
        ? `category drift ${drift.toFixed(2)}`
        : 'drift computed over stored rows',
    durationMs: null,
  });
  stages.push({
    ...meta.audit,
    status: audited ? 'passed' : 'idle',
    detail: audited
      ? 'this request was sampled for offline audit'
      : 'offline sampler; not sampled in this trace',
    durationMs: null,
  });
  return stages;
}

const statusIcon = (status: Stage['status']) => {
  switch (status) {
    case 'passed': return <CheckCircle className="w-3.5 h-3.5 text-success" />;
    case 'failed': return <XCircle className="w-3.5 h-3.5 text-destructive" />;
    case 'idle': return <Circle className="w-3.5 h-3.5 text-muted" />;
  }
};

const statusColor = (status: Stage['status']) => {
  switch (status) {
    case 'passed': return 'border-success/30 bg-success/5';
    case 'failed': return 'border-destructive/30 bg-destructive/5';
    case 'idle': return 'border-border bg-transparent';
  }
};

export default function PipelinePanel({
  trajectory,
  telemetry,
}: {
  trajectory: TrajectoryRow[] | null;
  telemetry: TelemetrySummary | null;
}) {
  const [expanded, setExpanded] = useState<string | null>(null);

  // Show the first request in the trajectory artifact.
  const firstRequestId = trajectory?.[0]?.request_id;
  const rows = (trajectory ?? []).filter((r) => r.request_id === firstRequestId);
  const stages = rows.length > 0 ? buildStages(rows, telemetry) : [];

  return (
    <div className="panel panel-sweep">
      <div className="panel-header">
        <span className="panel-title">Assurance Pipeline</span>
        <span className="text-[10px] font-mono text-muted">
          {rows.length > 0 ? (
            <span title={firstRequestId}>request trace · {rows.length} attempt{rows.length === 1 ? '' : 's'}</span>
          ) : (
            'no trace loaded'
          )}
        </span>
      </div>
      <div className="panel-body space-y-1">
        {stages.length === 0 ? (
          <div className="py-6 text-center text-muted text-xs">
            No trajectory artifact available — nothing to trace.
          </div>
        ) : (
          stages.map((stage) => {
            const isExpanded = expanded === stage.id;
            return (
              <div key={stage.id}>
                <div
                  onClick={() => setExpanded(isExpanded ? null : stage.id)}
                  className={`flex items-center gap-2 px-2 py-1.5 rounded border ${statusColor(stage.status)} transition-colors duration-200 cursor-pointer select-none active:scale-[0.99]`}
                >
                  <span className="flex-shrink-0">{statusIcon(stage.status)}</span>
                  <span className="font-mono text-[11px] text-foreground flex-1">{stage.label}</span>
                  {stage.durationMs !== null && (
                    <span className="font-mono text-[10px] text-muted tabular-nums">{ms(stage.durationMs)}</span>
                  )}
                  <span className="text-muted">
                    {isExpanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
                  </span>
                </div>
                {isExpanded && (
                  <div className="mx-2 mt-1 mb-1.5 px-2 py-1.5 rounded bg-elevated border border-border/50 text-[10px] font-mono space-y-1 animate-[metric-up_0.2s_ease-out]">
                    <p className="text-muted leading-relaxed">{stage.desc}</p>
                    {stage.detail && (
                      <div className="pt-1 border-t border-border/30 text-foreground/80 flex items-start gap-1">
                        <CornerDownRight className="w-2.5 h-2.5 flex-shrink-0 mt-0.5 text-border" />
                        <span>{stage.detail}</span>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
