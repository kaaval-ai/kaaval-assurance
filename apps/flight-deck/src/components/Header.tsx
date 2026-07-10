import { useState, useEffect } from 'react';
import { Shield, LayoutDashboard, BarChart3, RefreshCw, Radio, Archive } from 'lucide-react';
import type { ConnectionStatus, DataLabel } from '../types';
import { DataLabelBadge } from './Tags';

export type AppMode = 'captured' | 'live';
export type DashboardView = 'summary' | 'telemetry';

interface HeaderProps {
  mode: AppMode;
  onModeChange: (mode: AppMode) => void;
  view: DashboardView;
  onViewChange: (view: DashboardView) => void;
  label: DataLabel | 'LIVE RUN' | null;
  status: ConnectionStatus;
  onRefresh: () => void;
  refreshing: boolean;
}

export default function Header({
  mode, onModeChange, view, onViewChange, label, status, onRefresh, refreshing,
}: HeaderProps) {
  const [time, setTime] = useState(() =>
    new Date().toLocaleTimeString('en-GB', { hour12: false })
  );
  useEffect(() => {
    const id = setInterval(
      () => setTime(new Date().toLocaleTimeString('en-GB', { hour12: false })),
      1000
    );
    return () => clearInterval(id);
  }, []);

  const seg = (active: boolean) =>
    `flex items-center gap-1 px-2.5 py-1 rounded text-[10px] font-mono font-medium transition-all duration-150 active:scale-95 ${
      active ? 'bg-accent text-white shadow-sm' : 'text-muted hover:text-foreground'
    }`;

  return (
    <header className="flex items-center justify-between px-4 py-2 bg-surface border-b border-border gap-3 flex-wrap">
      <div className="flex items-center gap-3">
        <Shield className="w-5 h-5 text-accent" />
        <div>
          <h1 className="font-heading text-sm font-semibold text-foreground tracking-wider">
            KAAVAL ASSURANCE
          </h1>
          <p className="text-[10px] text-muted font-mono leading-tight">
            INFERENCE FLIGHT DECK · {mode === 'live' ? 'live assurance execution' : 'captured-run observability'}
          </p>
        </div>
        {label && <DataLabelBadge label={label} />}
        {status === 'unavailable' && (
          <span className="text-[10px] font-mono text-destructive">API unavailable</span>
        )}
        {status === 'stale' && (
          <span className="text-[10px] font-mono text-warning">showing last good payload</span>
        )}
      </div>

      <div className="flex items-center gap-3">
        {/* Mode switch: Captured Evidence / Live Run */}
        <div className="flex items-center bg-elevated rounded-md border border-border p-0.5">
          <button onClick={() => onModeChange('captured')} className={seg(mode === 'captured')}>
            <Archive className="w-3 h-3" />
            Captured Evidence
          </button>
          <button onClick={() => onModeChange('live')} className={seg(mode === 'live')}>
            <Radio className="w-3 h-3" />
            Live Run
          </button>
        </div>

        {mode === 'captured' && (
          <div className="flex items-center bg-elevated rounded-md border border-border p-0.5">
            <button onClick={() => onViewChange('summary')} className={seg(view === 'summary')}>
              <LayoutDashboard className="w-3 h-3" />
              Summary
            </button>
            <button onClick={() => onViewChange('telemetry')} className={seg(view === 'telemetry')}>
              <BarChart3 className="w-3 h-3" />
              Telemetry
            </button>
          </div>
        )}

        <button
          onClick={onRefresh}
          disabled={refreshing}
          className="flex items-center gap-1 px-2 py-1 rounded border border-border bg-elevated text-[10px] font-mono text-muted hover:text-foreground transition-colors disabled:opacity-50"
          title="Refresh artifacts"
        >
          <RefreshCw className={`w-3 h-3 ${refreshing ? 'animate-spin' : ''}`} />
          Refresh
        </button>

        <span className="font-mono text-xs text-muted tabular-nums">{time} UTC</span>
      </div>
    </header>
  );
}
