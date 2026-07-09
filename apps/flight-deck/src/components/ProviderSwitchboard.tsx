import { useState } from 'react';
import { Wifi, AlertTriangle, WifiOff, Ban, Activity, ChevronDown, ChevronRight } from 'lucide-react';
import type { Provider, ProviderStatus } from '../types';

const statusIcon = (status: ProviderStatus) => {
  switch (status) {
    case 'online': return <Wifi className="w-3 h-3 text-success" />;
    case 'degraded': return <AlertTriangle className="w-3 h-3 text-warning" />;
    case 'down': return <WifiOff className="w-3 h-3 text-destructive" />;
    case 'disabled': return <Ban className="w-3 h-3 text-muted" />;
  }
};

const statusDotClass = (status: ProviderStatus) => {
  switch (status) {
    case 'online': return 'status-dot--online';
    case 'degraded': return 'status-dot--degraded';
    case 'down': return 'status-dot--down';
    case 'disabled': return 'status-dot--disabled';
  }
};

export default function ProviderSwitchboard({ providers }: { providers: Provider[] }) {
  const [expanded, setExpanded] = useState<string | null>(null);

  return (
    <div className="panel panel-sweep">
      <div className="panel-header">
        <span className="panel-title">Provider Switchboard</span>
        <span className="text-[10px] font-mono text-muted">
          {providers.filter(p => p.status === 'online').length}/{providers.filter(p => p.status !== 'disabled').length} active
        </span>
      </div>
      <div className="panel-body space-y-1.5">
        {providers.length === 0 ? (
          <div className="py-6 text-center text-muted text-xs">
            No providers configured. Add API keys in Settings to get started.
          </div>
        ) : (
          providers.map((p) => {
            const isExpanded = expanded === p.id;
            return (
              <div key={p.id}>
                <div
                  onClick={() => setExpanded(isExpanded ? null : p.id)}
                  className={`flex items-center gap-2 px-2 py-1.5 rounded border transition-colors duration-200 cursor-pointer select-none active:scale-[0.99] ${
                    p.status === 'disabled'
                      ? 'border-border/50 opacity-50'
                      : p.status === 'degraded'
                      ? 'border-warning/20 bg-warning/5'
                      : 'border-border hover:border-accent/20'
                  }`}
                >
                  {/* Status */}
                  <span className="flex-shrink-0">{statusIcon(p.status)}</span>

                  {/* Name */}
                  <span className={`font-mono text-[11px] flex-1 truncate ${p.status === 'disabled' ? 'text-muted' : 'text-foreground'}`}>
                    {p.name}
                  </span>

                  {/* Metrics */}
                  <div className="hidden sm:flex items-center gap-2 text-[10px] font-mono tabular-nums">
                    <span className="flex items-center gap-0.5 text-muted">
                      <Activity className="w-2.5 h-2.5" />
                      {p.latencyMs}ms
                    </span>
                    <span className="text-muted">|</span>
                    <span className="text-muted">{p.requestsPerMin}/min</span>
                    <span className="text-muted">|</span>
                    <span className={
                      p.errorRate > 1 ? 'text-destructive' : p.errorRate > 0.5 ? 'text-warning' : 'text-muted'
                    }>
                      {p.errorRate}% err
                    </span>
                  </div>

                  {/* Quota bar */}
                  <div className="w-16 bg-elevated rounded-full h-1.5 overflow-hidden flex-shrink-0">
                    <div
                      className={`h-full rounded-full transition-all duration-500 ${
                        p.quotaUsed > 90 ? 'bg-destructive' : p.quotaUsed > 70 ? 'bg-warning' : 'bg-accent'
                      }`}
                      style={{ width: `${p.quotaUsed}%` }}
                    />
                  </div>
                  <span className="text-[10px] font-mono text-muted tabular-nums w-8 text-right">{p.quotaUsed}%</span>

                  {/* Expand icon */}
                  <span className="text-muted flex-shrink-0">
                    {isExpanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
                  </span>
                </div>

                {/* Expanded detail */}
                {isExpanded && (
                  <div className="mx-2 mt-1 mb-1.5 px-2 py-1.5 rounded bg-elevated border border-border/50 text-[10px] font-mono space-y-1 animate-[metric-up_0.2s_ease-out]">
                    <div className="flex items-center justify-between">
                      <span className="text-muted">Status</span>
                      <span className={`text-foreground capitalize ${p.status === 'disabled' ? 'text-muted' : ''}`}>
                        {p.status}
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-muted">Quota</span>
                      <span className="text-foreground tabular-nums">{p.quotaUsed} / {p.quotaLimit} req/min</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-muted">Last checked</span>
                      <span className="text-foreground tabular-nums">
                        {new Date(p.lastChecked).toLocaleTimeString('en-GB', { hour12: false })}
                      </span>
                    </div>
                    {p.status === 'degraded' && (
                      <div className="pt-1 border-t border-border/30 text-warning flex items-center gap-1">
                        <AlertTriangle className="w-2.5 h-2.5 flex-shrink-0" />
                        <span>Latency exceeds threshold — failover may trigger</span>
                      </div>
                    )}
                    {p.status === 'disabled' && (
                      <div className="pt-1 border-t border-border/30 text-muted italic">
                        Provider disabled in settings. Enable to route traffic.
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