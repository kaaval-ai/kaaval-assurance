import { useState, useRef, useEffect, useCallback } from 'react';
import { Play, Pause, SkipBack, SkipForward, RotateCcw, Clock, AlertTriangle, CheckCircle } from 'lucide-react';
import type { TrajectoryRow } from '../types';
import { DataLabelBadge, ms, usd } from './Tags';

/* Replays real trajectory rows — each step is one stored model attempt with
   its exact verifier outcome, failed check IDs, tokens, and cost. */

interface TrajectoryReplayProps {
  rows: TrajectoryRow[];
  label: 'SAMPLE' | 'REPLAY' | 'LIVE RUN';
  escalationReason?: string | null;
  autoPlay?: boolean;
}

function formatTime(ts: string): string {
  const d = new Date(ts);
  return isNaN(d.getTime()) ? '—' : d.toLocaleTimeString('en-GB', { hour12: false });
}

export default function TrajectoryReplay({ rows, label, escalationReason, autoPlay }: TrajectoryReplayProps) {
  const [currentIndex, setCurrentIndex] = useState<number>(0);
  const [playing, setPlaying] = useState(Boolean(autoPlay && rows.length > 0));
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  const stop = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    setPlaying(false);
  }, []);

  useEffect(() => {
    if (!playing) return;
    intervalRef.current = setInterval(() => {
      setCurrentIndex((prev) => {
        if (prev >= rows.length - 1) {
          clearInterval(intervalRef.current!);
          intervalRef.current = null;
          setPlaying(false);
          return prev;
        }
        return prev + 1;
      });
    }, 900);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [playing, rows.length]);

  useEffect(() => {
    setCurrentIndex(0);
    setPlaying(Boolean(autoPlay && rows.length > 0));
  }, [rows, autoPlay]);

  useEffect(() => {
    const child = scrollRef.current?.children[currentIndex];
    child?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
  }, [currentIndex]);

  const current = rows[currentIndex];

  return (
    <div className="panel panel-sweep">
      <div className="panel-header">
        <span className="panel-title flex items-center gap-2">
          Trajectory Replay
          <DataLabelBadge label={label === 'REPLAY' ? 'CAPTURED LOCAL RUN' : label} />
        </span>
        <span className="text-[10px] font-mono text-muted">
          {rows.length > 0 ? `${currentIndex + 1}/${rows.length} attempts` : 'no rows'}
        </span>
      </div>

      <div className="panel-body space-y-2">
        {rows.length === 0 ? (
          <div className="py-6 text-center text-muted text-xs">
            No trajectory rows in the loaded artifact.
          </div>
        ) : (
          <>
            <div ref={scrollRef} className="space-y-1 max-h-[180px] overflow-y-auto pr-1">
              {rows.map((row, i) => {
                const isActive = i === currentIndex;
                const isPast = i < currentIndex;
                return (
                  <div
                    key={`${row.request_id}-${i}`}
                    onClick={() => { stop(); setCurrentIndex(i); }}
                    className={`flex items-center gap-2 px-2 py-1 rounded border transition-all duration-200 cursor-pointer select-none ${
                      isActive ? 'border-accent bg-accent/5'
                        : isPast ? 'border-border/30 bg-elevated/30'
                        : 'border-border/50 hover:border-accent/20 hover:bg-elevated/50'
                    }`}
                  >
                    {row.verifier_passed
                      ? <CheckCircle className="w-3 h-3 text-success flex-shrink-0" />
                      : <AlertTriangle className="w-3 h-3 text-destructive flex-shrink-0" />}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-1.5">
                        <span className={`text-[10px] font-mono font-medium truncate ${isActive ? 'text-foreground' : 'text-muted'}`}>
                          {row.tier} attempt — {row.provider}/{row.model_id}
                          {row.escalated ? ' (escalated)' : ''}
                        </span>
                        <span className="text-[9px] font-mono text-muted flex-shrink-0">{formatTime(row.ts)}</span>
                      </div>
                      {isActive && (
                        <div className="text-[9px] font-mono text-muted mt-0.5 flex items-center gap-1.5 flex-wrap">
                          <span className="flex items-center gap-0.5"><Clock className="w-2 h-2" />{ms(row.latency_ms)}</span>
                          <span>{row.prompt_tokens}+{row.completion_tokens} tok</span>
                          <span className={row.verifier_passed ? 'text-success' : 'text-destructive'}>
                            Layer 1 {row.verifier_passed ? 'passed' : `FAILED: ${row.verifier_failures.join(', ')}`}
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>

            <div className="flex items-center justify-center gap-2 pt-1 border-t border-border/30">
              <button onClick={() => { stop(); setCurrentIndex(0); }} disabled={currentIndex === 0}
                className="p-1 rounded text-muted hover:text-foreground hover:bg-elevated transition-colors duration-150 disabled:opacity-40 active:scale-95" title="Reset">
                <RotateCcw className="w-3.5 h-3.5" />
              </button>
              <button onClick={() => { stop(); setCurrentIndex((p) => Math.max(p - 1, 0)); }} disabled={currentIndex === 0}
                className="p-1 rounded text-muted hover:text-foreground hover:bg-elevated transition-colors duration-150 disabled:opacity-40 active:scale-95" title="Step back">
                <SkipBack className="w-3.5 h-3.5" />
              </button>
              <button onClick={() => (playing ? stop() : setPlaying(true))}
                className="p-1.5 rounded bg-accent text-white hover:bg-accent/90 transition-colors duration-150 active:scale-95" title={playing ? 'Pause' : 'Play'}>
                {playing ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
              </button>
              <button onClick={() => { stop(); setCurrentIndex((p) => Math.min(p + 1, rows.length - 1)); }} disabled={currentIndex >= rows.length - 1}
                className="p-1 rounded text-muted hover:text-foreground hover:bg-elevated transition-colors duration-150 disabled:opacity-40 active:scale-95" title="Step forward">
                <SkipForward className="w-3.5 h-3.5" />
              </button>
            </div>

            {current && (
              <div className="px-2 py-1.5 rounded bg-elevated border border-border/50 text-[10px] font-mono animate-[metric-up_0.2s_ease-out]">
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-x-3 gap-y-1">
                  <div><span className="text-muted">Request</span><div className="text-foreground truncate" title={current.request_id}>{current.request_id}</div></div>
                  <div><span className="text-muted">Contract</span><div className="text-foreground truncate">{current.contract_id} v{current.contract_version}</div></div>
                  <div><span className="text-muted">Category</span><div className="text-foreground">{current.category}</div></div>
                  <div><span className="text-muted">Tier / provider</span><div className="text-foreground">{current.tier} · {current.provider} · {current.model_id}</div></div>
                  <div><span className="text-muted">Latency / tokens</span><div className="text-foreground tabular-nums">{ms(current.latency_ms)} · {current.prompt_tokens}+{current.completion_tokens}</div></div>
                  <div><span className="text-muted">Cost</span><div className="text-foreground tabular-nums">{usd(current.cost_usd)}</div></div>
                  <div className="col-span-2 sm:col-span-3">
                    <span className="text-muted">Layer 1 outcome</span>
                    <div className={current.verifier_passed ? 'text-success' : 'text-destructive'}>
                      {current.verifier_passed ? 'passed' : `failed — check IDs: ${current.verifier_failures.join(', ')}`}
                    </div>
                  </div>
                  {current.escalated && (
                    <div className="col-span-2 sm:col-span-3">
                      <span className="text-muted">Escalation reason</span>
                      <div className="text-warning">{escalationReason || 'layer-1 verification failed on the local attempt'}</div>
                    </div>
                  )}
                  {current.audit_sampled && (
                    <div className="col-span-2 sm:col-span-3">
                      <span className="text-muted">Layer 3 audit</span>
                      <div className="text-foreground">sampled · result: {current.audit_result ?? 'n/a'}</div>
                    </div>
                  )}
                </div>
                <div className="mt-1 pt-1 border-t border-border/30 text-muted truncate" title={current.task_input}>
                  input: {current.task_input}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
