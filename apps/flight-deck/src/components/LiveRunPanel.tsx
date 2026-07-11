import { useState } from 'react';
import { Radio, Loader2, AlertTriangle, CheckCircle, XCircle, RefreshCw } from 'lucide-react';
import type { LiveRunResponse } from '../types';
import { startRun, resetSession, ApiError } from '../api';
import { CONTRACTS, SAMPLE_INPUTS } from '../mock/data';
import TrajectoryReplay from './TrajectoryReplay';
import TelemetryTruth from './TelemetryTruth';

/* Live Assurance Run: drives the real pipeline through POST /api/runs.
   Everything rendered after submission derives from the returned run —
   never merged with sample or captured data. The request is synchronous;
   the pending state says so honestly. */

const FAILURE_MODES = ['none', 'missing_field', 'bad_enum', 'out_of_range', 'unparseable', 'undersevere'] as const;

export default function LiveRunPanel({ run, onRunComplete }: { run: LiveRunResponse | null; onRunComplete: (r: LiveRunResponse | null) => void }) {
  const [contractId, setContractId] = useState(CONTRACTS[0].id);
  const [taskInput, setTaskInput] = useState(SAMPLE_INPUTS[CONTRACTS[0].id] ?? '');
  const [localProvider, setLocalProvider] = useState<'mock' | 'ollama' | 'vllm'>('mock');
  const [remoteProvider, setRemoteProvider] = useState<'mock' | 'fireworks'>('mock');
  // Default to the policy-cap near-miss: first click, no configuration,
  // shows the local tier try to approve $1,000 over the $500 refund cap
  // and get caught before it ships.
  const [failureMode, setFailureMode] = useState<string>('out_of_range');
  const [remoteFailureMode, setRemoteFailureMode] = useState<string>('none');
  const [confirmSpend, setConfirmSpend] = useState(false);
  const [exportArtifacts, setExportArtifacts] = useState(false);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string | undefined>();
  const [isResetting, setIsResetting] = useState(false);

  const selectContract = (id: string) => {
    setContractId(id);
    setTaskInput(SAMPLE_INPUTS[id] ?? '');
    setFailureMode(id === 'support.refund_decision' ? 'out_of_range' : 'none');
  };

  const submit = async () => {
    setPending(true);
    setError(null);
    try {
      const result = await startRun({
        task_input: taskInput,
        contract_id: contractId,
        local_provider: localProvider,
        remote_provider: remoteProvider,
        confirm_spend: confirmSpend,
        failure_mode: failureMode === 'none' ? null : failureMode,
        remote_failure_mode: remoteFailureMode === 'none' ? null : remoteFailureMode,
        export_artifacts: exportArtifacts,
        session_id: sessionId,
        // The Flight Deck is an inspection surface: receipts show every
        // attempt verbatim, so it explicitly opts in to seeing unverified
        // output. Integrations default to the fail-closed behavior.
        include_unverified_raw: true,
      });
      setSessionId(result.session.session_id);
      onRunComplete(result);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'request failed');
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
      // clear session and response in parent? We can just clear the local state.
      // Or we can just let the next run create a new session if we clear sessionId.
      // But resetSession endpoint preserves the ID and returns a fresh session.
      // To show it's cleared, we should clear the run output.
      onRunComplete(null); // clear the run output.
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'reset failed');
    } finally {
      setIsResetting(false);
    }
  };

  const selectCls =
    'bg-elevated border border-border rounded px-2 py-1 text-[11px] font-mono text-foreground w-full';

  return (
    <div className="space-y-3">
      <div className="panel panel-sweep">
        <div className="panel-header">
          <span className="panel-title flex items-center gap-1.5">
            <Radio className="w-3 h-3 text-accent" />
            Live Assurance Run
          </span>
          <span className="text-[10px] font-mono text-muted">
            executes the real pipeline server-side · credentials never reach the browser
          </span>
        </div>
        <div className="panel-body space-y-2">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            <label className="block text-[10px] font-mono text-muted space-y-1">
              <span className="uppercase tracking-wider">Task contract</span>
              <select className={selectCls} value={contractId} onChange={(e) => selectContract(e.target.value)}>
                {CONTRACTS.map((c) => (
                  <option key={c.id} value={c.id}>{c.label} — {c.id}</option>
                ))}
              </select>
            </label>
            <label className="block text-[10px] font-mono text-muted space-y-1">
              <span className="uppercase tracking-wider">Failure injection (mock local only)</span>
              <select
                className={selectCls}
                value={failureMode}
                onChange={(e) => setFailureMode(e.target.value)}
                disabled={localProvider !== 'mock'}
              >
                {FAILURE_MODES.map((m) => <option key={m} value={m}>{m}</option>)}
              </select>
            </label>
          </div>

          <label className="block text-[10px] font-mono text-muted space-y-1">
            <span className="uppercase tracking-wider">Task input (synthetic sample; edit freely)</span>
            <textarea
              className={`${selectCls} min-h-[64px] resize-y`}
              value={taskInput}
              onChange={(e) => setTaskInput(e.target.value)}
              maxLength={4000}
            />
          </label>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            <label className="block text-[10px] font-mono text-muted space-y-1">
              <span className="uppercase tracking-wider">Local provider</span>
              <select className={selectCls} value={localProvider} onChange={(e) => { setLocalProvider(e.target.value as typeof localProvider); if (e.target.value !== 'mock') setFailureMode('none'); }}>
                <option value="mock">mock — deterministic stand-in</option>
                <option value="ollama">ollama — local OpenAI-compatible endpoint</option>
                <option value="vllm">vllm — ROCm + vLLM endpoint (AMD target)</option>
              </select>
            </label>
            <label className="block text-[10px] font-mono text-muted space-y-1">
              <span className="uppercase tracking-wider">Remote provider</span>
              <select className={selectCls} value={remoteProvider} onChange={(e) => { setRemoteProvider(e.target.value as typeof remoteProvider); if (e.target.value !== 'mock') setRemoteFailureMode('none'); }}>
                <option value="mock">mock — no network</option>
                <option value="fireworks">fireworks — spends API credits</option>
              </select>
            </label>
          </div>

          <label className="block text-[10px] font-mono text-muted space-y-1">
            <span className="uppercase tracking-wider">Remote failure injection (mock remote only) — the double-failure path: the expensive answer is contract-checked too</span>
            <select
              className={selectCls}
              value={remoteFailureMode}
              onChange={(e) => setRemoteFailureMode(e.target.value)}
              disabled={remoteProvider !== 'mock'}
            >
              {FAILURE_MODES.map((m) => <option key={m} value={m}>{m}</option>)}
            </select>
          </label>

          {remoteProvider === 'fireworks' && (
            <label className="flex items-center gap-2 px-2 py-1.5 rounded border border-warning/40 bg-warning/5 text-[10px] font-mono text-warning cursor-pointer">
              <input type="checkbox" checked={confirmSpend} onChange={(e) => setConfirmSpend(e.target.checked)} />
              I confirm this run may spend Fireworks credits (the server operator must also enable paid remote execution)
            </label>
          )}

          <label className="flex items-center gap-2 text-[10px] font-mono text-muted cursor-pointer">
            <input type="checkbox" checked={exportArtifacts} onChange={(e) => setExportArtifacts(e.target.checked)} />
            Export to an isolated per-run directory (requires the server operator export gate)
          </label>

          <div className="flex items-center gap-3">
            <button
              onClick={submit}
              disabled={pending || !taskInput.trim()}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-accent text-white text-[11px] font-mono font-semibold hover:bg-accent/90 transition-colors disabled:opacity-50 active:scale-95"
            >
              {pending ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Radio className="w-3.5 h-3.5" />}
              {pending ? 'Executing pipeline (synchronous)…' : 'Run assurance pipeline'}
            </button>
            {error && (
              <span className="flex items-center gap-1 text-[10px] font-mono text-destructive">
                <AlertTriangle className="w-3 h-3" />
                {error}
              </span>
            )}
          </div>

          {run?.session && (
            <div className="mt-4 p-2 rounded bg-elevated border border-border/50 text-[10px] font-mono space-y-1 text-muted">
              <div className="flex items-center justify-between">
                <span className="text-foreground font-semibold">Active Session: {run.session.session_id}</span>
                <button 
                  onClick={handleReset} 
                  disabled={isResetting}
                  className="flex items-center gap-1 hover:text-foreground disabled:opacity-50"
                >
                  <RefreshCw className={`w-3 h-3 ${isResetting ? 'animate-spin' : ''}`} />
                  Reset live session
                </button>
              </div>
              <div>Category: {run.session.category}</div>
              <div>Online EWMA drift: {run.session.online_ewma_drift.toFixed(2)}</div>
              <div>Current routing policy: {run.session.current_policy_action}</div>
              <div className="truncate">Reason: {run.session.current_policy_reason}</div>
            </div>
          )}
        </div>
      </div>

      {run && (
        <>
          <div className="panel panel-sweep">
            <div className="panel-header">
              <span className="panel-title">Result — run {run.run_id}</span>
              <span className="text-[10px] font-mono text-muted">{run.generated_at}</span>
            </div>
            <div className="panel-body space-y-2 text-[11px] font-mono">
              <div className="flex items-center gap-2 flex-wrap">
                {run.result.verified ? (
                  <span className="flex items-center gap-1 text-success"><CheckCircle className="w-3.5 h-3.5" />Layer-1 contract checks passed</span>
                ) : (
                  <span className="flex items-center gap-1 text-destructive"><XCircle className="w-3.5 h-3.5" />FAILED Layer-1 checks: {run.result.failures.join(', ')}</span>
                )}
                <span className="text-muted">·</span>
                <span className="text-foreground">{run.result.attempts} attempt{run.result.attempts === 1 ? '' : 's'}</span>
                <span className="text-muted">·</span>
                <span className={run.result.tier === 'local' ? 'text-success' : 'text-warning'}>
                  {run.result.escalated
                    ? 'escalated to remote tier'
                    : run.result.tier === 'local'
                      ? 'resolved locally'
                      : 'pre-routed to remote tier'}
                </span>
                <span className="text-muted">·</span>
                <span className="text-muted">{run.result.checks_run} deterministic checks</span>
              </div>
              <div className="text-[10px] text-muted">routing: {run.result.routing_reason}</div>
              {run.result.answer ? (
                <pre className="px-2 py-1.5 rounded bg-elevated border border-border/50 text-[10px] overflow-x-auto">
                  {JSON.stringify(run.result.answer, null, 2)}
                </pre>
              ) : (
                <pre className="px-2 py-1.5 rounded bg-elevated border border-destructive/30 text-[10px] overflow-x-auto text-destructive">
                  {run.result.raw_text || 'no output'}
                </pre>
              )}
              {run.artifacts_written.length > 0 && (
                <div className="text-[10px] text-success">
                  exported as captured evidence: {run.artifacts_written.join(', ')}
                </div>
              )}
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
            <TrajectoryReplay
              rows={run.trajectory}
              label="LIVE RUN"
              escalationReason={run.result.escalated ? run.result.routing_reason : null}
              autoPlay
            />
            <TelemetryTruth telemetry={run.telemetry} usedSample={false} />
          </div>
        </>
      )}
    </div>
  );
}
