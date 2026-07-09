import { useState, useEffect } from 'react';
import { Activity, Clock, Shield, Users, AlertTriangle, Server, LayoutDashboard, BarChart3 } from 'lucide-react';

interface HeaderProps {
  currentView: 'summary' | 'telemetry';
  onViewChange: (view: 'summary' | 'telemetry') => void;
}

export default function Header({ currentView, onViewChange }: HeaderProps) {
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

  return (
    <header className="flex items-center justify-between px-4 py-2 bg-surface border-b border-border">
      {/* Left: Brand */}
      <div className="flex items-center gap-3">
        <Shield className="w-5 h-5 text-accent" />
        <div>
          <h1 className="font-heading text-sm font-semibold text-foreground tracking-wider">
            KAAVAL ASSURANCE
          </h1>
          <p className="text-[10px] text-muted font-mono leading-tight">
            INFERENCE FLIGHT DECK · v2.4.1
          </p>
        </div>
        <span className="flex items-center gap-1.5 ml-3 px-2 py-0.5 bg-accent/10 border border-accent/20 rounded text-[10px] font-mono text-accent">
          <span className="relative flex h-1.5 w-1.5">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-accent opacity-75" />
            <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-accent" />
          </span>
          LIVE
        </span>
      </div>

      {/* Center: Quick Stats */}
      <div className="hidden md:flex items-center gap-4 text-[11px] font-mono text-muted">
        <div className="flex items-center gap-1.5">
          <Activity className="w-3.5 h-3.5 text-accent" />
          <span>847.3K req</span>
        </div>
        <div className="flex items-center gap-1.5">
          <Clock className="w-3.5 h-3.5 text-muted" />
          <span>45h 39m uptime</span>
        </div>
        <div className="flex items-center gap-1.5">
          <AlertTriangle className="w-3.5 h-3.5 text-warning" />
          <span className="text-warning">3 alerts</span>
        </div>
        <div className="flex items-center gap-1.5">
          <Server className="w-3.5 h-3.5 text-success" />
          <span className="text-success">6 providers</span>
        </div>
        <div className="flex items-center gap-1.5">
          <Users className="w-3.5 h-3.5 text-muted" />
          <span>12 contracts</span>
        </div>
      </div>

      {/* Right: View Toggle + Clock */}
      <div className="flex items-center gap-3">
        {/* Segmented control: Summary ↔ Telemetry */}
        <div className="flex items-center bg-elevated rounded-md border border-border p-0.5">
          <button
            onClick={() => onViewChange('summary')}
            className={`flex items-center gap-1 px-2.5 py-1 rounded text-[10px] font-mono font-medium transition-all duration-150 active:scale-95 ${
              currentView === 'summary'
                ? 'bg-accent text-white shadow-sm'
                : 'text-muted hover:text-foreground'
            }`}
          >
            <LayoutDashboard className="w-3 h-3" />
            Summary
          </button>
          <button
            onClick={() => onViewChange('telemetry')}
            className={`flex items-center gap-1 px-2.5 py-1 rounded text-[10px] font-mono font-medium transition-all duration-150 active:scale-95 ${
              currentView === 'telemetry'
                ? 'bg-accent text-white shadow-sm'
                : 'text-muted hover:text-foreground'
            }`}
          >
            <BarChart3 className="w-3 h-3" />
            Telemetry
          </button>
        </div>

        <span className="font-mono text-xs text-muted tabular-nums">
          {time} UTC
        </span>
      </div>
    </header>
  );
}