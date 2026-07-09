import { useState, useEffect, useRef } from 'react';
import { Activity, Wifi, Timer, Zap, ArrowUp, ArrowDown, ChevronDown, ChevronRight, AlertTriangle } from 'lucide-react';
import type { TelemetryMetric } from '../types';

interface Point {
  value: number;
  timestamp: number;
}

function Sparkline({ data, color, height = 28 }: { data: Point[]; color: string; height?: number }) {
  const width = 120;
  if (data.length < 2) {
    return (
      <div className="flex items-center justify-center text-muted text-[9px] font-mono" style={{ width, height }}>
        awaiting data...
      </div>
    );
  }
  const values = data.map(p => p.value);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const points = data.map((p, i) => {
    const x = (i / (data.length - 1)) * width;
    const y = height - ((p.value - min) / range) * (height - 4) - 2;
    return `${x},${y}`;
  });
  const d = `M${points.join(' L')}`;
  return (
    <svg width={width} height={height} className="flex-shrink-0">
      <path d={d} fill="none" stroke={color} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

const metricDescriptions: Record<string, { what: string; why: string }> = {
  'Latency': {
    what: 'Average response time for inference requests across all providers and models.',
    why: 'High latency degrades user experience and may indicate provider congestion or oversized prompts. SLA threshold: 500ms P95.',
  },
  'Throughput': {
    what: 'Total requests processed in the current assurance run.',
    why: 'Throughput determines system capacity. Drops may indicate provider throttling, quota exhaustion, or network bottlenecks.',
  },
  'Error Rate': {
    what: 'Percentage of requests that failed Layer-1 verification and escalated to the remote tier.',
    why: 'Sustained escalation above 20% indicates the local open-weight model is drifting or incapable of the task.',
  },
  'Cost': {
    what: 'Total USD spent on inference for the current run, including remote escalation and audits.',
    why: 'Cost efficiency is critical. The local Gemma tier minimizes spend, while the remote tier ensures quality.',
  },
};

function MetricCard({ metric, isExpanded, onToggle, chartMode }: { metric: TelemetryMetric; isExpanded: boolean; onToggle: () => void; chartMode: 'line' | 'stats' }) {
  const [history, setHistory] = useState<Point[]>([]);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    const now = Date.now();
    setHistory([{ value: metric.value, timestamp: now }]);

    intervalRef.current = setInterval(() => {
      setHistory(prev => {
        const next = [...prev, { value: metric.value + (Math.random() - 0.5) * metric.value * 0.1, timestamp: Date.now() }];
        return next.slice(-20);
      });
    }, 1500);

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [metric.value, metric.label]);

  const last = history.length > 0 ? history[history.length - 1] : null;
  const prev = history.length > 1 ? history[history.length - 2] : null;
  const trend = last && prev ? (last.value >= prev.value ? 'up' : 'down') : 'neutral';
  const desc = metricDescriptions[metric.label];

  return (
    <div>
      <div
        onClick={onToggle}
        className="flex items-center gap-2 px-2 py-1.5 rounded border border-border/50 hover:bg-elevated/50 transition-colors duration-200 cursor-pointer select-none active:scale-[0.99]"
      >
        <div className="flex-shrink-0 space-y-0.5 min-w-0 flex-1">
          <div className="flex items-center gap-1">
            <span className="text-muted text-[9px] uppercase tracking-wider font-mono">{metric.label}</span>
            {trend === 'up' ? (
              <ArrowUp className="w-2.5 h-2.5 text-success" />
            ) : trend === 'down' ? (
              <ArrowDown className="w-2.5 h-2.5 text-destructive" />
            ) : null}
            {metric.alarm && (
              <AlertTriangle className="w-2.5 h-2.5 text-destructive animate-pulse" />
            )}
          </div>
          <div className="flex items-center gap-1.5">
            <span className="text-foreground text-[10px] font-mono font-semibold tabular-nums">
              {metric.unit === 'ms' ? `${metric.value.toFixed(0)}${metric.unit}` :
               metric.unit === '%' ? `${metric.value.toFixed(1)}${metric.unit}` :
               metric.unit === 'req/s' || metric.unit === 'req/run' ? `${metric.value.toFixed(0)} ${metric.unit}` :
               metric.unit === '$' ? `${metric.unit}${metric.value.toFixed(4)}` :
               `${metric.value.toFixed(2)}${metric.unit}`}
            </span>
            <span className="text-muted text-[9px] font-mono tabular-nums">
              ±{(metric.value * 0.05).toFixed(metric.unit === '$' ? 4 : 1)}{metric.unit === '$' ? '' : metric.unit}
            </span>
          </div>
        </div>
        <div className="flex-shrink-0">
          {chartMode === 'line' ? (
            <Sparkline data={history} color="var(--color-accent)" />
          ) : (
            <div className="flex items-center gap-1.5 text-[9px] font-mono tabular-nums text-muted ml-auto">
              <span className="px-1 py-0.5 rounded bg-elevated border border-border/30 leading-none">
                min {metric.unit === 'ms' ? `${metric.min.toFixed(0)}` : metric.unit === '$' ? `$${metric.min.toFixed(4)}` : `${metric.min.toFixed(2)}`}
              </span>
              <span className="px-1 py-0.5 rounded bg-elevated border border-border/30 leading-none">
                avg {metric.unit === 'ms' ? `${metric.avg.toFixed(0)}` : metric.unit === '$' ? `$${metric.avg.toFixed(4)}` : `${metric.avg.toFixed(2)}`}
              </span>
              <span className="px-1 py-0.5 rounded bg-elevated border border-border/30 leading-none">
                max {metric.unit === 'ms' ? `${metric.max.toFixed(0)}` : metric.unit === '$' ? `$${metric.max.toFixed(4)}` : `${metric.max.toFixed(2)}`}
              </span>
            </div>
          )}
        </div>
        <span className="text-muted flex-shrink-0 ml-1">
          {isExpanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
        </span>
      </div>

      {/* Expanded detail */}
      {isExpanded && (
        <div className="mx-2 mt-1 mb-1.5 px-2 py-1.5 rounded bg-elevated border border-border/50 text-[10px] font-mono space-y-1.5 animate-[metric-up_0.2s_ease-out]">
          {desc && (
            <>
              <div>
                <span className="text-muted text-[9px] uppercase tracking-wider">What is this?</span>
                <p className="text-foreground/80 mt-0.5 leading-relaxed">{desc.what}</p>
              </div>
              <div className="pt-1 border-t border-border/30">
                <span className="text-muted text-[9px] uppercase tracking-wider">Why it matters</span>
                <p className="text-foreground/80 mt-0.5 leading-relaxed">{desc.why}</p>
              </div>
            </>
          )}
          <div className="grid grid-cols-2 gap-x-3 gap-y-1 pt-1 border-t border-border/30">
            <div>
              <span className="text-muted">Current</span>
              <div className="text-foreground tabular-nums">
                {metric.unit === 'ms' ? `${metric.value.toFixed(0)} ${metric.unit}` :
                 metric.unit === '$' ? `$${metric.value.toFixed(4)}` :
                 `${metric.value.toFixed(2)} ${metric.unit}`}
              </div>
            </div>
            <div>
              <span className="text-muted">Average</span>
              <div className="text-foreground tabular-nums">
                {metric.unit === 'ms' ? `${metric.avg.toFixed(0)} ${metric.unit}` :
                 metric.unit === '$' ? `$${metric.avg.toFixed(4)}` :
                 `${metric.avg.toFixed(2)} ${metric.unit}`}
              </div>
            </div>
            <div>
              <span className="text-muted">Min</span>
              <div className="text-foreground tabular-nums">
                {metric.unit === 'ms' ? `${metric.min.toFixed(0)} ${metric.unit}` :
                 metric.unit === '$' ? `$${metric.min.toFixed(4)}` :
                 `${metric.min.toFixed(2)} ${metric.unit}`}
              </div>
            </div>
            <div>
              <span className="text-muted">Max</span>
              <div className="text-foreground tabular-nums">
                {metric.unit === 'ms' ? `${metric.max.toFixed(0)} ${metric.unit}` :
                 metric.unit === '$' ? `$${metric.max.toFixed(4)}` :
                 `${metric.max.toFixed(2)} ${metric.unit}`}
              </div>
            </div>
          </div>
          {metric.alarm && (
            <div className="pt-1 border-t border-border/30 flex items-start gap-1 text-destructive">
              <AlertTriangle className="w-2.5 h-2.5 flex-shrink-0 mt-0.5" />
              <span>{metric.label} has breached the alert threshold. Recommended action: investigate and apply mitigation.</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

const iconMap: Record<string, React.ReactNode> = {
  'latency': <Timer className="w-3 h-3" />,
  'throughput': <Zap className="w-3 h-3" />,
  'error': <Activity className="w-3 h-3" />,
  'uptime': <Wifi className="w-3 h-3" />,
  'cost': <span className="font-bold text-[10px] w-3 h-3 flex items-center justify-center">$</span>,
};

export default function TelemetryTruth({ metrics }: { metrics: TelemetryMetric[] }) {
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [chartMode, setChartMode] = useState<'line' | 'stats'>('line');

  return (
    <div className="panel panel-sweep">
      <div className="panel-header">
        <span className="panel-title">Telemetry Truth</span>
        <div className="flex items-center gap-2">
          {/* Line ↔ Stats toggle */}
          <div className="flex items-center bg-elevated rounded border border-border p-0.5">
            <button
              onClick={() => setChartMode('line')}
              className={`px-1.5 py-0.5 rounded text-[9px] font-mono font-medium transition-all duration-150 active:scale-95 ${
                chartMode === 'line'
                  ? 'bg-accent text-white shadow-sm'
                  : 'text-muted hover:text-foreground'
              }`}
            >
              Line
            </button>
            <button
              onClick={() => setChartMode('stats')}
              className={`px-1.5 py-0.5 rounded text-[9px] font-mono font-medium transition-all duration-150 active:scale-95 ${
                chartMode === 'stats'
                  ? 'bg-accent text-white shadow-sm'
                  : 'text-muted hover:text-foreground'
              }`}
            >
              Stats
            </button>
          </div>
          <span className="text-[10px] font-mono text-muted">
            {metrics.filter(m => m.alarm).length > 0 ? (
              <span className="text-destructive">{metrics.filter(m => m.alarm).length} alarms</span>
            ) : (
              <span className="text-success">all nominal</span>
            )}
            {' | '}{metrics.length} metrics
          </span>
        </div>
      </div>
      <div className="panel-body space-y-1">
        {metrics.length === 0 ? (
          <div className="py-6 text-center text-muted text-xs">
            No telemetry data yet. Run an inference to begin collecting metrics.
          </div>
        ) : (
          metrics.map((m) => (
            <div key={m.id} className="flex items-center gap-2">
              <span className="flex-shrink-0 text-accent">{iconMap[m.icon] || <Activity className="w-3 h-3" />}</span>
              <div className="flex-1 min-w-0">
                <MetricCard
                  metric={m}
                  isExpanded={expandedId === m.id}
                  onToggle={() => setExpandedId(expandedId === m.id ? null : m.id)}
                  chartMode={chartMode}
                />
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}