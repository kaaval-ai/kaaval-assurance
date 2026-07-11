import { useState, useEffect, useCallback, useRef } from 'react';
import type { ConnectionStatus, DashboardPayload, LiveRunResponse } from './types';
import { fetchDashboard } from './api';
import Header, { type AppMode, type DashboardView } from './components/Header';
import StatusBar from './components/StatusBar';
import SummaryDashboard from './components/SummaryDashboard';
import PipelinePanel from './components/PipelinePanel';
import ProviderSwitchboard from './components/ProviderSwitchboard';
import ContractGate from './components/ContractGate';
import ModelComparison from './components/ModelComparison';
import TelemetryTruth from './components/TelemetryTruth';
import TrajectoryReplay from './components/TrajectoryReplay';
import AMDProof from './components/AMDProof';
import LiveRunPanel from './components/LiveRunPanel';
import EvidenceModeBanner from './components/EvidenceModeBanner';

const REFRESH_INTERVAL_MS = 5000;

export default function App() {
  const [payload, setPayload] = useState<DashboardPayload | null>(null);
  const [status, setStatus] = useState<ConnectionStatus>('loading');
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [view, setView] = useState<DashboardView>('summary');
  const [mode, setMode] = useState<AppMode>('captured');
  const [liveRun, setLiveRun] = useState<LiveRunResponse | null>(null);
  const hasPayload = useRef(false);

  const refresh = useCallback(async () => {
    setRefreshing(true);
    try {
      const data = await fetchDashboard();
      setPayload(data);
      hasPayload.current = true;
      setStatus('connected');
      setLastRefresh(new Date());
    } catch {
      // Keep the last valid payload; mark it stale rather than inventing data.
      setStatus(hasPayload.current ? 'stale' : 'unavailable');
    } finally {
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, REFRESH_INTERVAL_MS);
    return () => clearInterval(id);
  }, [refresh]);

  const telemetry = payload?.telemetry ?? null;
  const trajectory = payload?.trajectory ?? null;
  const replayLabel = payload?.label ?? 'UNAVAILABLE';

  return (
    <div className="h-full flex flex-col bg-canvas text-foreground bg-noc-grid">
      <div className="bg-crt" />

      <Header
        mode={mode}
        onModeChange={setMode}
        view={view}
        onViewChange={setView}
        label={mode === 'live' ? 'LIVE RUN' : payload?.label ?? null}
        status={status}
        onRefresh={refresh}
        refreshing={refreshing}
      />

      <EvidenceModeBanner mode={mode} label={payload?.label ?? null} />

      <main className="flex-1 overflow-y-auto p-3 md:p-4 space-y-3">
        {mode === 'live' ? (
          <LiveRunPanel run={liveRun} onRunComplete={setLiveRun} />
        ) : status === 'unavailable' ? (
          <div className="panel px-4 py-10 text-center space-y-2">
            <p className="text-sm font-mono text-destructive">API unavailable — no artifacts to display.</p>
            <p className="text-[11px] font-mono text-muted">
              Start the backend from the repo root: <code>uv run uvicorn apps.api.server:app --port 8000</code>
            </p>
          </div>
        ) : status === 'loading' && !payload ? (
          <div className="panel px-4 py-10 text-center text-sm font-mono text-muted">
            Loading captured artifacts…
          </div>
        ) : view === 'summary' ? (
          <SummaryDashboard payload={payload} />
        ) : (
          <>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
              <PipelinePanel trajectory={trajectory} telemetry={telemetry} />
              <ProviderSwitchboard telemetry={telemetry} usedSample={payload?.used_sample ?? false} />
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
              <div className="lg:col-span-1">
                <ContractGate telemetry={telemetry} />
              </div>
              <div className="lg:col-span-2">
                <TelemetryTruth telemetry={telemetry} usedSample={payload?.used_sample ?? false} />
              </div>
            </div>

            <ModelComparison telemetry={telemetry} usedSample={payload?.used_sample ?? false} />

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
              <div className="lg:col-span-2">
                <TrajectoryReplay rows={trajectory ?? []} label={replayLabel} />
              </div>
              <div className="lg:col-span-1">
                {payload && (
                  <AMDProof
                    probe={payload.runtime_probe}
                    provenance={payload.provenance.runtime_probe}
                    amd={payload.amd}
                    telemetry={telemetry}
                  />
                )}
              </div>
            </div>
          </>
        )}
      </main>

      <StatusBar 
        mode={mode} 
        payload={payload} 
        status={status} 
        lastRefresh={lastRefresh} 
        liveRun={liveRun} 
      />
    </div>
  );
}
