import { Terminal, Database, Clock } from 'lucide-react';
import type { ConnectionStatus, DashboardPayload, LiveRunResponse } from '../types';

interface StatusBarProps {
  mode: 'captured' | 'live';
  payload: DashboardPayload | null;
  status: ConnectionStatus;
  lastRefresh: Date | null;
  liveRun: LiveRunResponse | null;
}

function originChip(name: string, origin: string | undefined) {
  const color =
    origin === 'artifacts' ? 'text-accent' : origin === 'sample' ? 'text-warning' : 'text-muted';
  return (
    <span className="flex items-center gap-1">
      <span className="text-muted">{name}:</span>
      <span className={color}>{origin ?? 'not_available'}</span>
    </span>
  );
}

export default function StatusBar({ mode, payload, status, lastRefresh, liveRun }: StatusBarProps) {
  if (mode === 'live') {
    return (
      <footer className="flex items-center justify-between px-4 py-1.5 bg-surface border-t border-border text-[10px] font-mono text-muted flex-wrap gap-2">
        <div className="flex items-center gap-3 flex-wrap">
          <span className="flex items-center gap-1">
            <Terminal className="w-3 h-3 text-accent" />
            <span>kaaval-flight-deck</span>
          </span>
          <span className="text-border">|</span>
          <span className="font-bold text-success tracking-widest">LIVE RUN</span>
          <span className="text-border">|</span>
          {liveRun ? (
            <span className="flex items-center gap-2">
              <span className="text-foreground">run {liveRun.run_id.slice(0, 13)}...</span>
              <span className="text-muted">·</span>
              <span>{liveRun.request.local_provider} / {liveRun.request.remote_provider}</span>
              <span className="text-muted">·</span>
              <span className={liveRun.result.status === 'accepted' ? 'text-success' : 'text-destructive'}>
                {liveRun.result.status === 'accepted' ? 'contract-conformant' : 'NO SAFE ANSWER'}
              </span>
              <span className="text-muted">·</span>
              <span>
                {liveRun.result.attempts} attempt{liveRun.result.attempts === 1 ? '' : 's'}
                ({liveRun.result.escalated ? 'escalated' : liveRun.result.tier})
              </span>
              <span className="text-muted">·</span>
              <span className="tabular-nums">${liveRun.telemetry.cost.total_cost_usd.toFixed(4)}</span>
            </span>
          ) : (
            <span>no live run yet</span>
          )}
        </div>
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1">
            <Clock className="w-3 h-3" />
            {liveRun ? new Date(liveRun.generated_at).toLocaleTimeString('en-GB', { hour12: false }) : '—'}
          </span>
        </div>
      </footer>
    );
  }

  const prov = payload?.provenance;
  const highDrift = payload?.telemetry?.routing.high_drift_categories.length ?? 0;
  return (
    <footer className="flex items-center justify-between px-4 py-1.5 bg-surface border-t border-border text-[10px] font-mono text-muted flex-wrap gap-2">
      <div className="flex items-center gap-3 flex-wrap">
        <span className="flex items-center gap-1">
          <Terminal className="w-3 h-3 text-accent" />
          <span>kaaval-flight-deck</span>
        </span>
        <span className="text-border">|</span>
        <span className="flex items-center gap-1">
          <Database className="w-3 h-3" />
          {prov ? (
            <span className="flex items-center gap-2">
              {originChip('telemetry', prov.telemetry.origin)}
              {originChip('trajectory', prov.trajectory.origin)}
              {originChip('probe', prov.runtime_probe.origin)}
            </span>
          ) : (
            <span>no artifacts loaded</span>
          )}
        </span>
        {highDrift > 0 && (
          <>
            <span className="text-border">|</span>
            <span className="text-warning">{highDrift} high-drift categor{highDrift === 1 ? 'y' : 'ies'}</span>
          </>
        )}
      </div>
      <div className="flex items-center gap-3">
        <span className="flex items-center gap-1">
          <Clock className="w-3 h-3" />
          last refresh:{' '}
          {lastRefresh ? lastRefresh.toLocaleTimeString('en-GB', { hour12: false }) : '—'}
        </span>
        <span className="text-border">|</span>
        <span className={status === 'connected' ? 'text-success' : status === 'stale' ? 'text-warning' : status === 'loading' ? 'text-muted' : 'text-destructive'}>
          {status}
        </span>
      </div>
    </footer>
  );
}
