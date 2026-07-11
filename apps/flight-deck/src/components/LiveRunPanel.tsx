import { useEffect, useState } from 'react';
import {
  AlertTriangle,
  CheckCircle,
  Loader2,
  PlugZap,
  Radio,
  RefreshCw,
  Server,
  Unplug,
  XCircle,
} from 'lucide-react';
import type {
  LiveRunResponse,
  RuntimeCapabilities,
  RuntimeConnection,
  RuntimeRole,
} from '../types';
import {
  ApiError,
  deleteRuntimeConnection,
  fetchCapabilities,
  resetSession,
  startRun,
} from '../api';
import { CONTRACTS, SAMPLE_INPUTS } from '../mock/data';
import ContractGate from './ContractGate';
import ModelComparison from './ModelComparison';
import PipelinePanel from './PipelinePanel';
import ProviderSwitchboard from './ProviderSwitchboard';
import RuntimeConnectionModal from './RuntimeConnectionModal';
import TelemetryTruth from './TelemetryTruth';
import TrajectoryReplay from './TrajectoryReplay';

interface Props {
  run: LiveRunResponse | null;
  onRunComplete: (run: LiveRunResponse | null) => void;
}

function RuntimeCard({
  title,
  connection,
  onConnect,
  onDisconnect,
}: {
  title: string;
  connection: RuntimeConnection | null;
  onConnect: () => void;
  onDisconnect: () => void;
}) {
  return (
    <div className={`rounded border p-3 ${connection ? 'border-success/40 bg-success/5' : 'border-border bg-elevated/30'}`}>
      <div className="flex items-center justify-between gap-2">
        <p className="flex items-center gap-1.5 text-[10px] font-mono font-bold uppercase tracking-wider text-foreground">
          {connection ? <PlugZap className="h-3.5 w-3.5 text-success" /> : <Server className="h-3.5 w-3.5 text-muted" />}
          {title}
        </p>
        {connection ? (
          <button onClick={onDisconnect} className="flex items-center gap-1 text-[10px] font-mono text-muted hover:text-destructive">
            <Unplug className="h-3 w-3" /> Disconnect
          </button>
        ) : (
          <button onClick={onConnect} className="flex items-center gap-1 rounded bg-accent px-2 py-1 text-[10px] font-mono font-semibold text-white">
            <PlugZap className="h-3 w-3" /> Connect
          </button>
        )}
      </div>
      {connection ? (
        <div className="mt-2 space-y-1 text-[10px] font-mono text-muted">
          <p className="text-foreground">{connection.provider} · {connection.model_id}</p>
          <p>{connection.endpoint_host ?? 'managed provider endpoint'} · {connection.hardware_target}</p>
          <p>credentials expire after {Math.round(connection.expires_in_seconds / 60)} idle minutes</p>
        </div>
      ) : (
        <p className="mt-2 text-[10px] font-mono text-muted">
          {title === 'Primary runtime' ? 'Required before a live run can start.' : 'Optional; used only after a failed contract check or adaptive pre-route.'}
        </p>
      )}
    </div>
  );
}

export default function LiveRunPanel({ run, onRunComplete }: Props) {
  const [capabilities, setCapabilities] = useState<RuntimeCapabilities | null>(null);
  const [primary, setPrimary] = useState<RuntimeConnection | null>(null);
  const [escalation, setEscalation] = useState<RuntimeConnection | null>(null);
  const [modalRole, setModalRole] = useState<RuntimeRole | null>(null);
  const [contractId, setContractId] = useState(CONTRACTS[0].id);
  const [taskInput, setTaskInput] = useState(SAMPLE_INPUTS[CONTRACTS[0].id] ?? '');
  const [confirmSpend, setConfirmSpend] = useState(false);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string | undefined>();
  const [isResetting, setIsResetting] = useState(false);

  useEffect(() => {
    fetchCapabilities()
      .then((result) => {
        setCapabilities(result);
        if (result.live_runs_enabled && result.byok_allowed) setModalRole('primary');
      })
      .catch((err) => setError(err instanceof ApiError ? err.message : 'capability discovery failed'));
  }, []);

  const selectContract = (id: string) => {
    setContractId(id);
    setTaskInput(SAMPLE_INPUTS[id] ?? '');
  };

  const acceptConnection = (connection: RuntimeConnection) => {
    if (connection.role === 'primary') setPrimary(connection);
    else setEscalation(connection);
    setSessionId(undefined);
    setConfirmSpend(false);
    onRunComplete(null);
  };

  const disconnect = async (connection: RuntimeConnection) => {
    try {
      await deleteRuntimeConnection(connection.connection_id);
    } finally {
      if (connection.role === 'primary') setPrimary(null);
      else setEscalation(null);
      setSessionId(undefined);
      setConfirmSpend(false);
      onRunComplete(null);
    }
  };

  const submit = async () => {
    if (!primary) {
      setModalRole('primary');
      return;
    }
    setPending(true);
    setError(null);
    try {
      const result = await startRun({
        task_input: taskInput,
        contract_id: contractId,
        local_provider: 'mock',
        remote_provider: 'mock',
        confirm_spend: confirmSpend,
        failure_mode: null,
        remote_failure_mode: null,
        export_artifacts: false,
        session_id: sessionId,
        include_unverified_raw: false,
        primary_connection_id: primary.connection_id,
        escalation_connection_id: escalation?.connection_id,
      });
      setSessionId(result.session.session_id);
      onRunComplete(result);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'request failed');
    } finally {
      setPending(false);
    }
  };

  const handleReset = async () => {
    if (!sessionId) return;
    setIsResetting(true);
    setError(null);
    try {
      await resetSession(sessionId);
      onRunComplete(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'reset failed');
    } finally {
      setIsResetting(false);
    }
  };

  const spendsCredits = Boolean(
    primary?.requires_spend_confirmation || escalation?.requires_spend_confirmation,
  );
  const selectCls = 'w-full rounded border border-border bg-elevated px-2 py-1.5 text-[11px] font-mono text-foreground';

  return (
    <div className="space-y-3">
      {capabilities && modalRole && (
        <RuntimeConnectionModal
          open
          role={modalRole}
          capabilities={capabilities}
          onClose={() => setModalRole(null)}
          onConnected={acceptConnection}
        />
      )}

      <div className="panel panel-sweep">
        <div className="panel-header">
          <span className="panel-title flex items-center gap-1.5">
            <Radio className="h-3 w-3 text-accent" /> Live Assurance Session
          </span>
          <span className="text-[10px] font-mono text-muted">real provider calls · real checks · replayable live receipts</span>
        </div>
        <div className="panel-body space-y-3">
          {capabilities && (!capabilities.live_runs_enabled || !capabilities.byok_allowed) && (
            <p className="rounded border border-warning/40 bg-warning/5 px-3 py-2 text-[10px] font-mono text-warning">
              Runtime onboarding is disabled in this deployment. The container operator must enable live runs and BYOK.
            </p>
          )}

          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            <RuntimeCard title="Primary runtime" connection={primary} onConnect={() => setModalRole('primary')} onDisconnect={() => primary && disconnect(primary)} />
            <RuntimeCard title="Escalation runtime" connection={escalation} onConnect={() => setModalRole('escalation')} onDisconnect={() => escalation && disconnect(escalation)} />
          </div>

          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            <label className="space-y-1 text-[10px] font-mono text-muted">
              <span className="uppercase tracking-wider">Task contract</span>
              <select className={selectCls} value={contractId} onChange={(event) => selectContract(event.target.value)}>
                {CONTRACTS.map((contract) => <option key={contract.id} value={contract.id}>{contract.label} — {contract.id}</option>)}
              </select>
            </label>
            <div className="rounded border border-border bg-elevated/30 px-3 py-2 text-[10px] font-mono text-muted">
              <p className="font-semibold uppercase tracking-wider text-foreground">Runtime policy</p>
              <p className="mt-1">Primary first · deterministic Layer 1 · escalation only on failure or EWMA pre-route.</p>
            </div>
          </div>

          <label className="block space-y-1 text-[10px] font-mono text-muted">
            <span className="uppercase tracking-wider">Task input</span>
            <textarea className={`${selectCls} min-h-[88px] resize-y`} value={taskInput} onChange={(event) => setTaskInput(event.target.value)} maxLength={4000} />
          </label>

          {spendsCredits && (
            <label className="flex cursor-pointer items-center gap-2 rounded border border-warning/40 bg-warning/5 px-2 py-2 text-[10px] font-mono text-warning">
              <input type="checkbox" checked={confirmSpend} onChange={(event) => setConfirmSpend(event.target.checked)} />
              I confirm this run may spend credits on my connected Fireworks runtime.
            </label>
          )}

          <div className="flex flex-wrap items-center gap-3">
            <button
              onClick={submit}
              disabled={pending || !taskInput.trim() || !primary || (spendsCredits && !confirmSpend)}
              className="flex items-center gap-1.5 rounded bg-accent px-3 py-1.5 text-[11px] font-mono font-semibold text-white transition-colors disabled:opacity-40"
            >
              {pending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Radio className="h-3.5 w-3.5" />}
              {pending ? 'Executing live pipeline…' : 'Run live assurance'}
            </button>
            {error && <span className="flex items-center gap-1 text-[10px] font-mono text-destructive"><AlertTriangle className="h-3 w-3" />{error}</span>}
          </div>

          {run?.session && (
            <div className="rounded border border-border/50 bg-elevated p-2 text-[10px] font-mono text-muted">
              <div className="flex items-center justify-between gap-2">
                <span className="font-semibold text-foreground">Session {run.session.session_id}</span>
                <button onClick={handleReset} disabled={isResetting} className="flex items-center gap-1 hover:text-foreground disabled:opacity-50">
                  <RefreshCw className={`h-3 w-3 ${isResetting ? 'animate-spin' : ''}`} /> Reset drift state
                </button>
              </div>
              <div className="mt-1 grid grid-cols-1 gap-1 sm:grid-cols-3">
                <span>category: {run.session.category}</span>
                <span>EWMA drift: {run.session.online_ewma_drift.toFixed(2)}</span>
                <span>policy: {run.session.current_policy_action}</span>
              </div>
            </div>
          )}
        </div>
      </div>

      {run && (
        <>
          <div className="panel panel-sweep">
            <div className="panel-header"><span className="panel-title">Live result — {run.run_id}</span><span className="text-[10px] font-mono text-muted">{run.generated_at}</span></div>
            <div className="panel-body space-y-2 text-[11px] font-mono">
              <div className="flex flex-wrap items-center gap-2">
                {run.result.status === 'accepted' ? (
                  <span className="flex items-center gap-1 text-success"><CheckCircle className="h-3.5 w-3.5" />Contract-conformant answer accepted</span>
                ) : (
                  <span className="flex items-center gap-1 text-destructive"><XCircle className="h-3.5 w-3.5" />NO SAFE ANSWER: {run.result.failures.join(', ')}</span>
                )}
                <span className="text-muted">· {run.result.attempts} attempt{run.result.attempts === 1 ? '' : 's'} · {run.result.checks_run} deterministic checks</span>
              </div>
              <p className="text-[10px] text-muted">routing: {run.result.routing_reason}</p>
              {run.result.answer ? (
                <pre className="overflow-x-auto rounded border border-border/50 bg-elevated px-2 py-2 text-[10px]">{JSON.stringify(run.result.answer, null, 2)}</pre>
              ) : (
                <p className="rounded border border-destructive/40 bg-destructive/10 px-2 py-2 text-[10px] text-destructive">No model payload crossed the acceptance boundary. Failed check IDs remain visible in the receipt.</p>
              )}
            </div>
          </div>

          <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
            <PipelinePanel trajectory={run.trajectory} telemetry={run.telemetry} />
            <ProviderSwitchboard telemetry={run.telemetry} usedSample={false} />
          </div>
          <div className="grid grid-cols-1 gap-3 lg:grid-cols-3">
            <ContractGate telemetry={run.telemetry} />
            <div className="lg:col-span-2"><TelemetryTruth telemetry={run.telemetry} usedSample={false} /></div>
          </div>
          <ModelComparison telemetry={run.telemetry} usedSample={false} />
          <TrajectoryReplay rows={run.trajectory} label="LIVE RUN" escalationReason={run.result.escalated ? run.result.routing_reason : null} autoPlay />
        </>
      )}
    </div>
  );
}
