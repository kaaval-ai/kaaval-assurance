import { useState } from 'react';
import { Shield, Activity, AlertTriangle, Wifi, WifiOff, CheckCircle, Loader2, Server, Clock, ChevronDown, ChevronRight, Target, Eye, GitBranch, ScrollText, Scale, BarChart3, Timeline, Fingerprint } from 'lucide-react';
import type { FlightDeckState, TelemetryMetric } from '../types';

interface StatCardProps {
  label: string;
  value: string | number;
  sub: string;
  icon: React.ReactNode;
  trend?: 'up' | 'down' | 'neutral';
  color?: string;
}

function StatCard({ label, value, sub, icon, trend, color }: StatCardProps) {
  return (
    <div className="flex items-center gap-3 px-3 py-2.5 rounded-lg border border-border/50 bg-surface/50">
      <span className={`flex-shrink-0 ${color || 'text-accent'}`}>{icon}</span>
      <div className="min-w-0">
        <div className="text-[11px] font-mono text-muted uppercase tracking-wider">{label}</div>
        <div className="flex items-center gap-1.5">
          <span className={`text-base font-semibold font-heading tabular-nums ${color || 'text-foreground'}`}>{value}</span>
          <span className={`text-[12px] font-mono tabular-nums ${trend === 'up' ? 'text-success' : trend === 'down' ? 'text-destructive' : 'text-muted'}`}>
            {sub}
          </span>
        </div>
      </div>
    </div>
  );
}

export default function SummaryDashboard({ state }: { state: FlightDeckState }) {
  const [introOpen, setIntroOpen] = useState(true);
  const [preloaded, setPreloaded] = useState(false);
  const onlineProviders = state.providers.filter(p => p.status === 'online').length;
  const degradedProviders = state.providers.filter(p => p.status === 'degraded').length;
  const downProviders = state.providers.filter(p => p.status === 'down').length;
  const failedPolicies = state.policies.filter(p => p.status === 'fail').length;
  const passedPolicies = state.policies.filter(p => p.status === 'pass').length;
  const pipelineRunning = state.pipeline.some(s => s.status === 'running');

  const formatUptime = (seconds: number) => {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    return `${h}h ${m}m`;
  };

  const getMetricStatus = (m: TelemetryMetric): 'success' | 'warning' | 'destructive' => {
    if (m.alarm) return 'destructive';
    switch (m.label) {
      case 'Latency':
        return m.current <= 200 ? 'success' : m.current <= 500 ? 'warning' : 'destructive';
      case 'Throughput':
        return m.current >= 800 ? 'success' : m.current >= 400 ? 'warning' : 'destructive';
      case 'Error Rate':
        return m.current <= 1 ? 'success' : m.current <= 3 ? 'warning' : 'destructive';
      case 'Uptime':
        return m.current >= 99.9 ? 'success' : m.current >= 99.5 ? 'warning' : 'destructive';
      default:
        return 'success';
    }
  };

  const statusStyles = {
    success: {
      border: 'border-success/30',
      bg: 'bg-success/[0.04]',
      text: 'text-success',
      label: 'text-success/70',
    },
    warning: {
      border: 'border-warning/30',
      bg: 'bg-warning/[0.04]',
      text: 'text-warning',
      label: 'text-warning/70',
    },
    destructive: {
      border: 'border-destructive/30',
      bg: 'bg-destructive/[0.04]',
      text: 'text-destructive',
      label: 'text-destructive/70',
    },
  } as const;

  return (
    <div className="space-y-3">
      {/* Mission Intro — collapsible explanation banner */}
      <div className={`panel overflow-hidden transition-all duration-500 ${
        preloaded
          ? 'border-destructive shadow-[0_0_18px_rgba(255,50,50,0.35)]'
          : !introOpen
            ? 'border-destructive/40 shadow-[0_0_10px_rgba(255,50,50,0.15)]'
            : 'panel-sweep'
      }`}>
        <div className="w-full flex items-center gap-2 px-3 py-2.5">
          <button
            onClick={() => {
              setIntroOpen(!introOpen);
              if (introOpen) setPreloaded(false);
            }}
            className={`flex items-center gap-2 flex-1 min-w-0 text-left transition-all duration-200 active:scale-[0.997] ${
              introOpen
                ? 'hover:opacity-80'
                : 'hover:opacity-80'
            }`}
          >
            <Shield className={`w-4 h-4 flex-shrink-0 transition-colors duration-500 ${
              preloaded ? 'text-destructive' : introOpen ? 'text-accent' : 'text-destructive'
            }`} />
            <span className="text-sm font-heading font-semibold text-foreground tracking-wide truncate">
              Kaaval Assurance — Inference Flight Deck
            </span>
            <span className={`hidden sm:inline text-[11px] font-mono ml-1 transition-all duration-500 ${
              preloaded ? 'text-destructive' : introOpen ? 'text-muted' : 'text-destructive/70'
            }`}>
              · {introOpen
                  ? 'AI governance &amp; compliance console'
                  : preloaded
                    ? 'PRE-LOADED — all systems standby'
                    : 'PRE-LOADED — briefing dismissed'
                }
            </span>
          </button>

          {/* Live / PRE-LOADED badge — clickable, always visible (hybrid) */}
          <button
            onClick={() => setPreloaded(!preloaded)}
            className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-mono font-bold uppercase tracking-widest border cursor-pointer transition-all duration-500 active:scale-[0.93] ${
              preloaded
                ? 'bg-destructive/20 text-destructive border-destructive/50 opacity-100'
                : 'bg-destructive/15 text-destructive border-destructive/30 animate-pulse-fast opacity-100 hover:bg-destructive/25'
            }`}
            style={{ animation: preloaded ? 'fadeToRed 0.5s ease-out forwards' : '' }}
          >
            {/* Animated dot */}
            <span className={`w-1.5 h-1.5 rounded-full transition-all duration-500 ${
              preloaded ? 'bg-destructive' : 'bg-destructive animate-pulse'
            }`} />
            {preloaded ? 'PRE-LOADED' : 'Live'}
          </button>

          <button
            onClick={() => {
              setIntroOpen(!introOpen);
              if (introOpen) setPreloaded(false);
            }}
            className="transition-all duration-200 active:scale-[0.997] flex-shrink-0"
          >
            <span className={`transition-all duration-300 ${
              preloaded ? 'text-destructive' : introOpen ? 'text-muted' : 'text-destructive'
            }`} style={{ transform: introOpen ? 'rotate(0deg)' : 'rotate(-90deg)' }}>
              <ChevronDown className="w-3.5 h-3.5" />
            </span>
          </button>
        </div>

        {introOpen && (
          <div className="px-3 pb-3 space-y-3 border-t border-border/40 pt-2.5 animate-[fadeSlideIn_0.25s_ease-out]">
            {/* Why we built this */}
            <div>
              <div className="flex items-center gap-1.5 mb-1.5">
                <Target className="w-3 h-3 text-accent" />
                <span className="text-sm font-heading font-semibold text-foreground uppercase tracking-wider">Why Kaaval Assurance</span>
              </div>
              <p className="text-sm font-mono text-muted leading-relaxed">
                Every AI inference is a trust decision. Kaaval Assurance gives engineering teams a single pane of glass over
                their inference infrastructure — routing, compliance, performance, and cryptographic proof — so you can
                deploy models at scale with the same rigor you'd expect from a mission-control NOC.
              </p>
            </div>

            {/* What each panel represents */}
            <div>
              <div className="flex items-center gap-1.5 mb-1.5">
                <Eye className="w-3 h-3 text-accent" />
                <span className="text-sm font-heading font-semibold text-foreground uppercase tracking-wider">Dashboard Panels</span>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-1.5">
                {[
                  { icon: <GitBranch className="w-3 h-3" />, label: 'Pipeline Viz', desc: 'Real-time inference request flow through model gates, with per-stage latency and status.', neon: '#00D4FF' },
                  { icon: <Server className="w-3 h-3" />, label: 'Provider Switchboard', desc: 'AI provider health, routing distribution, and failover status across all endpoints.', neon: '#34C759' },
                  { icon: <ScrollText className="w-3 h-3" />, label: 'Contract Gate', desc: 'Policy enforcement — every inference checked against compliance, security, and cost rules.', neon: '#FFB000' },
                  { icon: <BarChart3 className="w-3 h-3" />, label: 'Model Comparison', desc: 'Side-by-side evaluation of model outputs: latency, quality scores, and cost per call.', neon: '#FF6B9D' },
                  { icon: <Activity className="w-3 h-3" />, label: 'Telemetry Truth', desc: 'Ground-truth metrics — latency, throughput, error rates — with sparkline toggle.', neon: '#7CFF7C' },
                  { icon: <Timeline className="w-3 h-3" />, label: 'Trajectory Replay', desc: 'Full audit trail of every request: from ingress through each gate to final response.', neon: '#A78BFA' },
                  { icon: <Fingerprint className="w-3 h-3" />, label: 'AMD Proof', desc: 'Cryptographic attestation measurements for verifiable, tamper-proof inference logs.', neon: '#FF8C42' },
                  { icon: <Scale className="w-3 h-3" />, label: 'Summary Dashboard', desc: 'At-a-glance KPIs, provider health, pipeline status, and policy compliance snapshot.', neon: '#D94FFF' },
                ].map((item) => (
                  <div key={item.label} className="flex items-start gap-1.5 px-2 py-1.5 rounded bg-surface/30 border border-border/20"
                       style={{ borderColor: `${item.neon}20` }}>
                    <span className="flex-shrink-0 mt-0.5" style={{ color: item.neon }}>{item.icon}</span>
                    <div>
                      <span className="text-[13px] font-heading font-semibold text-foreground">{item.label}</span>
                      <p className="text-[12px] font-mono text-muted leading-snug">{item.desc}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Row 1: Primary KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
        <StatCard
          label="Total Requests"
          value={(state.totalRequests / 1000).toFixed(1) + 'K'}
          sub="all time"
          icon={<Activity className="w-4 h-4" />}
          trend="up"
        />
        <StatCard
          label="System Uptime"
          value={formatUptime(state.systemUptime)}
          sub={`${((1 - (86400 - state.systemUptime) / 86400) * 100).toFixed(2)}%`}
          icon={<Clock className="w-4 h-4" />}
          color="text-success"
        />
        <StatCard
          label="Active Alerts"
          value={state.activeAlerts}
          sub={state.activeAlerts > 0 ? 'attention needed' : 'all clear'}
          icon={<AlertTriangle className="w-4 h-4" />}
          color={state.activeAlerts > 0 ? 'text-warning' : 'text-success'}
          trend={state.activeAlerts > 0 ? 'up' : 'down'}
        />
        <StatCard
          label="Active Contracts"
          value={state.contractCount}
          sub={`${state.providers.length} providers`}
          icon={<Server className="w-4 h-4" />}
        />
      </div>

      {/* Row 2: Provider + Pipeline + Policy health */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {/* Provider Health */}
        <div className="panel panel-sweep">
          <div className="panel-header">
            <span className="panel-title">Provider Health</span>
            <span className="text-[11px] font-mono text-muted">
              {onlineProviders}/{state.providers.length} online
            </span>
          </div>
          <div className="panel-body space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5">
                <Wifi className="w-3 h-3 text-success" />
                <span className="text-[11px] font-mono text-foreground">Online</span>
              </div>
              <span className="text-[11px] font-mono tabular-nums text-success">{onlineProviders}</span>
            </div>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5">
                <AlertTriangle className="w-3 h-3 text-warning" />
                <span className="text-[11px] font-mono text-foreground">Degraded</span>
              </div>
              <span className="text-[11px] font-mono tabular-nums text-warning">{degradedProviders}</span>
            </div>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5">
                <WifiOff className="w-3 h-3 text-destructive" />
                <span className="text-[11px] font-mono text-foreground">Down</span>
              </div>
              <span className="text-[11px] font-mono tabular-nums text-destructive">{downProviders}</span>
            </div>
            {/* Health bar */}
            <div className="h-2 bg-elevated rounded-full overflow-hidden flex">
              <div className="bg-success h-full transition-all" style={{ width: `${(onlineProviders / state.providers.length) * 100}%` }} />
              <div className="bg-warning h-full transition-all" style={{ width: `${(degradedProviders / state.providers.length) * 100}%` }} />
              <div className="bg-destructive h-full transition-all" style={{ width: `${(downProviders / state.providers.length) * 100}%` }} />
            </div>
          </div>
        </div>

        {/* Pipeline Status */}
        <div className="panel panel-sweep">
          <div className="panel-header">
            <span className="panel-title">Pipeline Status</span>
            <span className="text-[11px] font-mono text-muted">
              {pipelineRunning ? (
                <span className="text-accent flex items-center gap-1">
                  <Loader2 className="w-2.5 h-2.5 animate-spin" /> In flight
                </span>
              ) : (
                <span className="text-success">All clear</span>
              )}
            </span>
          </div>
          <div className="panel-body space-y-1.5">
            {state.pipeline.map((stage) => (
              <div key={stage.id} className="flex items-center gap-2">
                {stage.status === 'running' ? (
                  <Loader2 className="w-3 h-3 text-accent animate-spin flex-shrink-0" />
                ) : stage.status === 'passed' ? (
                  <CheckCircle className="w-3 h-3 text-success flex-shrink-0" />
                ) : stage.status === 'failed' ? (
                  <AlertTriangle className="w-3 h-3 text-destructive flex-shrink-0" />
                ) : (
                  <span className="w-3 h-3 rounded-full border border-border flex-shrink-0" />
                )}
                <span className="text-[12px] font-mono text-foreground">{stage.label}</span>
                <span className="ml-auto text-[11px] font-mono text-muted tabular-nums">
                  {stage.durationMs > 0 ? `${stage.durationMs}ms` : '—'}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Policy Summary */}
        <div className="panel panel-sweep">
          <div className="panel-header">
            <span className="panel-title">Policy Compliance</span>
            <span className="text-[12px] font-mono text-muted">
              {failedPolicies > 0 ? (
                <span className="text-destructive">{failedPolicies} violations</span>
              ) : (
                <span className="text-success">{passedPolicies} passed</span>
              )}
            </span>
          </div>
          <div className="panel-body space-y-2">
            {state.policies.slice(0, 6).map((p) => (
              <div key={p.id} className="flex items-center gap-1.5">
                {p.status === 'pass' ? (
                  <CheckCircle className="w-2.5 h-2.5 text-success flex-shrink-0" />
                ) : p.status === 'warn' ? (
                  <AlertTriangle className="w-2.5 h-2.5 text-warning flex-shrink-0" />
                ) : p.status === 'fail' ? (
                  <AlertTriangle className="w-2.5 h-2.5 text-destructive flex-shrink-0" />
                ) : (
                  <span className="w-2.5 h-2.5 rounded-full border border-border flex-shrink-0" />
                )}
                <span className="text-[12px] font-mono text-foreground truncate">{p.name}</span>
              </div>
            ))}
            {state.policies.length > 6 && (
              <div className="text-[11px] font-mono text-muted text-center">
                +{state.policies.length - 6} more policies
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Row 3: Key Telemetry at a glance */}
      <div className="panel panel-sweep">
        <div className="panel-header">
          <span className="panel-title">Key Metrics</span>
          <span className="text-[12px] font-mono text-muted">real-time</span>
        </div>
        <div className="panel-body">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
            {state.telemetry.slice(0, 4).map((m) => {
              const status = getMetricStatus(m);
              const s = statusStyles[status];
              return (
                <div key={m.id} className={`flex flex-col items-center justify-center px-3 py-3 rounded-lg border ${s.border} ${s.bg} text-center transition-all duration-300`}>
                  <span className={`text-[12px] font-mono ${s.label} uppercase tracking-wider`}>{m.label}</span>
                  <span className={`text-lg font-heading font-semibold tabular-nums ${s.text}`}>
                    {m.unit === 'ms' ? `${m.value.toFixed(0)}` :
                     m.unit === '%' ? `${m.value.toFixed(1)}` :
                     m.unit === 'req/s' ? `${m.value.toFixed(0)}` :
                     `${m.value.toFixed(2)}`}
                  </span>
                  <span className={`text-[11px] font-mono ${s.label}`}>{m.unit}</span>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}