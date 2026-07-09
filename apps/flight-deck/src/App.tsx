import { useState, useEffect } from 'react';
import { defaultState as mockFlightDeckState } from './mock/data';
import type { FlightDeckState } from './types';
import Header from './components/Header';
import StatusBar from './components/StatusBar';
import SummaryDashboard from './components/SummaryDashboard';
import PipelinePanel from './components/PipelinePanel';
import ProviderSwitchboard from './components/ProviderSwitchboard';
import ContractGate from './components/ContractGate';
import ModelComparison from './components/ModelComparison';
import TelemetryTruth from './components/TelemetryTruth';
import TrajectoryReplay from './components/TrajectoryReplay';
import AMDProof from './components/AMDProof';

type DashboardView = 'summary' | 'telemetry';

export default function App() {
  const [state, setState] = useState<FlightDeckState>(mockFlightDeckState);
  const [view, setView] = useState<DashboardView>('summary');

  useEffect(() => {
    fetch('/api/telemetry')
      .then(res => {
        if (!res.ok) throw new Error("Telemetry not found");
        return res.json();
      })
      .then(data => {
        setState(prev => {
          // 1. Providers Mapping
          const updatedProviders = prev.providers.map(p => {
            const providerId = p.name.toLowerCase().includes('gemini') || p.name.toLowerCase().includes('mock') ? 'mock' : 'fireworks'; // Simplified map based on known tiers
            const attemptCount = data.provider_mix?.attempts_by_provider?.[providerId] || 0;
            return {
              ...p,
              status: attemptCount > 0 ? 'online' : (p.id === 'prv-1' ? 'online' : 'idle'),
              quotaUsed: attemptCount,
            };
          });

          // 2. Telemetry Mapping
          const updatedTelemetry = [
            {
              id: 'tel-1',
              label: 'Latency',
              unit: 'ms',
              icon: 'latency',
              current: data.latency_ms_p50 || prev.telemetry[0].current,
              min: data.latency_ms_p50 ? data.latency_ms_p50 * 0.8 : prev.telemetry[0].min,
              max: data.latency_ms_p95 || prev.telemetry[0].max,
              avg: data.latency_ms_p50 || prev.telemetry[0].avg,
              alarm: false,
              sparkline: prev.telemetry[0].sparkline,
              value: data.latency_ms_p50 || prev.telemetry[0].value,
            },
            {
              id: 'tel-2',
              label: 'Throughput',
              unit: 'req/run',
              icon: 'throughput',
              current: data.requests || prev.telemetry[1].current,
              min: data.requests ? data.requests * 0.8 : prev.telemetry[1].min,
              max: data.requests ? data.requests * 1.2 : prev.telemetry[1].max,
              avg: data.requests || prev.telemetry[1].avg,
              alarm: false,
              sparkline: prev.telemetry[1].sparkline,
              value: data.requests || prev.telemetry[1].value,
            },
            {
              id: 'tel-3',
              label: 'Error Rate',
              unit: '%',
              icon: 'error',
              current: data.routing?.escalation_rate !== undefined ? data.routing.escalation_rate * 100 : prev.telemetry[2].current,
              min: 0,
              max: 100,
              avg: data.routing?.escalation_rate !== undefined ? data.routing.escalation_rate * 100 : prev.telemetry[2].avg,
              alarm: (data.routing?.escalation_rate || 0) > 0.2, // 20% threshold
              sparkline: prev.telemetry[2].sparkline,
              value: data.routing?.escalation_rate !== undefined ? data.routing.escalation_rate * 100 : prev.telemetry[2].value,
            },
            {
              id: 'tel-4',
              label: 'Cost',
              unit: '$',
              icon: 'cost',
              current: data.cost?.total_cost_usd || prev.telemetry[3].current,
              min: 0,
              max: data.cost?.total_cost_usd ? data.cost.total_cost_usd * 1.5 : prev.telemetry[3].max,
              avg: data.cost?.total_cost_usd || prev.telemetry[3].avg,
              alarm: false,
              sparkline: prev.telemetry[3].sparkline,
              value: data.cost?.total_cost_usd || prev.telemetry[3].value,
            }
          ];

          return {
            ...prev,
            totalRequests: data.requests || prev.totalRequests,
            providerCount: data.provider_mix ? Object.keys(data.provider_mix.attempts_by_provider || {}).length : prev.providerCount,
            trajectory: data.attempts_detail ? data.attempts_detail.map((a: any, i: number) => ({
              id: a.request_id + '-' + i,
              timestamp: new Date().toISOString(),
              action: `${a.tier} attempt (${a.provider})`,
              status: a.verifier_passed ? 'success' : (a.escalated ? 'warning' : 'error'),
              durationMs: a.latency_ms,
              detail: a.verifier_failures?.join(', ') || 'No failures'
            })) : prev.trajectory,
            providers: updatedProviders,
            telemetry: updatedTelemetry,
          };
        });
      })
      .catch(err => console.error("API error:", err));
  }, []);

  return (
    <div className="h-full flex flex-col bg-canvas text-foreground bg-noc-grid">
      {/* CRT overlay */}
      <div className="bg-crt" />

      {/* Header with view toggle */}
      <Header currentView={view} onViewChange={setView} />

      {/* Main dashboard content */}
      <main className="flex-1 overflow-y-auto p-3 md:p-4 space-y-3">
        {view === 'summary' ? (
          <SummaryDashboard state={state} />
        ) : (
          <>
            {/* Row 1: Pipeline + Switchboard */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
              <PipelinePanel stages={state.pipeline} />
              <ProviderSwitchboard providers={state.providers} />
            </div>

            {/* Row 2: Contract Gate (half width on large) + Telemetry Truth */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
              <div className="lg:col-span-1">
                <ContractGate policies={state.policies} />
              </div>
              <div className="lg:col-span-2">
                <TelemetryTruth metrics={state.telemetry} />
              </div>
            </div>

            {/* Row 3: Model Comparison — full width */}
            <ModelComparison models={state.models} />

            {/* Row 4: Trajectory + AMD Proof */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
              <div className="lg:col-span-2">
                <TrajectoryReplay steps={state.trajectory} />
              </div>
              <div className="lg:col-span-1">
                <AMDProof measurements={state.amdMeasurements} />
              </div>
            </div>
          </>
        )}
      </main>

      {/* Status bar */}
      <StatusBar state={state} />
    </div>
  );
}