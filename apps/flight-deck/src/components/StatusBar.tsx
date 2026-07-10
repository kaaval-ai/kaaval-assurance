import { Terminal, Database, Clock } from 'lucide-react';
import type { ConnectionStatus, DashboardPayload } from '../types';

interface StatusBarProps {
  payload: DashboardPayload | null;
  status: ConnectionStatus;
  lastRefresh: Date | null;
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

export default function StatusBar({ payload, status, lastRefresh }: StatusBarProps) {
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
