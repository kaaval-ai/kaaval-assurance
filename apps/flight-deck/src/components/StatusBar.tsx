import { Terminal, Wifi, WifiOff, AlertTriangle } from 'lucide-react';
import type { FlightDeckState } from '../types';

export default function StatusBar({ state }: { state: FlightDeckState }) {
  const onlineCount = state.providers.filter(p => p.status === 'online').length;
  const degradedCount = state.providers.filter(p => p.status === 'degraded').length;
  const downCount = state.providers.filter(p => p.status === 'down').length;

  return (
    <footer className="flex items-center justify-between px-4 py-1.5 bg-surface border-t border-border text-[10px] font-mono text-muted">
      <div className="flex items-center gap-3">
        <span className="flex items-center gap-1">
          <Terminal className="w-3 h-3 text-accent" />
          <span>kaaval-flight-deck@2.4.1</span>
        </span>
        <span className="text-border">|</span>
        <span className="flex items-center gap-1">
          <Wifi className="w-3 h-3 text-success" />
          <span className="text-success">{onlineCount} online</span>
        </span>
        {degradedCount > 0 && (
          <>
            <span className="text-border">|</span>
            <span className="flex items-center gap-1">
              <AlertTriangle className="w-3 h-3 text-warning" />
              <span className="text-warning">{degradedCount} degraded</span>
            </span>
          </>
        )}
        {downCount > 0 && (
          <>
            <span className="text-border">|</span>
            <span className="flex items-center gap-1">
              <WifiOff className="w-3 h-3 text-destructive" />
              <span className="text-destructive">{downCount} down</span>
            </span>
          </>
        )}
      </div>
      <div className="flex items-center gap-3">
        <span>Last sync: {new Date().toLocaleTimeString('en-GB', { hour12: false })}</span>
        <span className="text-border">|</span>
        <span>Alerts: <span className={state.activeAlerts > 0 ? 'text-warning' : 'text-success'}>{state.activeAlerts}</span></span>
      </div>
    </footer>
  );
}