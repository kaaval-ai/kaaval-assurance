import { useState, useRef, useEffect, useCallback } from 'react';
import { Play, Pause, SkipBack, SkipForward, RotateCcw, ChevronRight, Clock, Zap, AlertTriangle, CheckCircle } from 'lucide-react';
import type { TrajectoryStep } from '../types';

function formatTime(ts: string): string {
  return new Date(ts).toLocaleTimeString('en-GB', { hour12: false, minute: '2-digit', second: '2-digit' });
}

function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

function StepIcon({ step }: { step: TrajectoryStep }) {
  switch (step.status) {
    case 'success': return <CheckCircle className="w-3 h-3 text-success" />;
    case 'warning': return <AlertTriangle className="w-3 h-3 text-warning" />;
    case 'error': return <AlertTriangle className="w-3 h-3 text-destructive" />;
    case 'running': return <span className="w-2.5 h-2.5 rounded-full border-2 border-accent border-t-transparent animate-spin" />;
    default: return <ChevronRight className="w-3 h-3 text-muted" />;
  }
}

export default function TrajectoryReplay({ steps }: { steps: TrajectoryStep[] }) {
  const [currentIndex, setCurrentIndex] = useState<number>(0);
  const [playing, setPlaying] = useState(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  const stop = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    setPlaying(false);
  }, []);

  const play = useCallback(() => {
    if (steps.length === 0) return;
    setPlaying(true);
  }, [steps.length]);

  useEffect(() => {
    if (!playing) return;
    intervalRef.current = setInterval(() => {
      setCurrentIndex(prev => {
        if (prev >= steps.length - 1) {
          clearInterval(intervalRef.current!);
          intervalRef.current = null;
          setPlaying(false);
          return prev;
        }
        return prev + 1;
      });
    }, 800);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [playing, steps.length]);

  // Auto-scroll
  useEffect(() => {
    if (scrollRef.current) {
      const child = scrollRef.current.children[currentIndex];
      if (child) {
        child.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
      }
    }
  }, [currentIndex]);

  const reset = useCallback(() => {
    stop();
    setCurrentIndex(0);
  }, [stop]);

  const stepForward = useCallback(() => {
    stop();
    setCurrentIndex(prev => Math.min(prev + 1, steps.length - 1));
  }, [stop, steps.length]);

  const stepBack = useCallback(() => {
    stop();
    setCurrentIndex(prev => Math.max(prev - 1, 0));
  }, [stop]);

  const currentStep = steps[currentIndex];

  return (
    <div className="panel panel-sweep">
      <div className="panel-header">
        <span className="panel-title">Trajectory Replay</span>
        <span className="text-[10px] font-mono text-muted">
          {currentIndex + 1}/{steps.length} steps
        </span>
      </div>

      <div className="panel-body space-y-2">
        {steps.length === 0 ? (
          <div className="py-6 text-center text-muted text-xs">
            No trajectory data. Submit an inference request to trace its path.
          </div>
        ) : (
          <>
            {/* Step timeline */}
            <div
              ref={scrollRef}
              className="space-y-1 max-h-[180px] overflow-y-auto pr-1 scrollbar-thin scrollbar-thumb-border scrollbar-track-transparent"
            >
              {steps.map((step, i) => {
                const isActive = i === currentIndex;
                const isPast = i < currentIndex;
                return (
                  <div
                    key={step.id}
                    onClick={() => { stop(); setCurrentIndex(i); }}
                    className={`flex items-center gap-2 px-2 py-1 rounded border transition-all duration-200 cursor-pointer select-none ${
                      isActive
                        ? 'border-accent bg-accent/5'
                        : isPast
                        ? 'border-border/30 bg-elevated/30'
                        : 'border-border/50 hover:border-accent/20 hover:bg-elevated/50'
                    }`}
                  >
                    <StepIcon step={step} />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-1.5">
                        <span className={`text-[10px] font-mono font-medium truncate ${
                          isActive ? 'text-foreground' : 'text-muted'
                        }`}>
                          {step.action}
                        </span>
                        <span className="text-[9px] font-mono text-muted flex-shrink-0">
                          {formatTime(step.timestamp)}
                        </span>
                      </div>
                      {isActive && (
                        <div className="text-[9px] font-mono text-muted mt-0.5 flex items-center gap-1.5">
                          {step.durationMs !== undefined && (
                            <span className="flex items-center gap-0.5">
                              <Clock className="w-2 h-2" />
                              {formatDuration(step.durationMs)}
                            </span>
                          )}
                          {step.status === 'error' && (
                            <span className="text-destructive">{step.detail || 'Error'}</span>
                          )}
                          {step.detail && step.status !== 'error' && (
                            <span>{step.detail}</span>
                          )}
                        </div>
                      )}
                    </div>
                    {step.status === 'running' && (
                      <span className="text-[9px] font-mono text-accent animate-pulse">running</span>
                    )}
                  </div>
                );
              })}
            </div>

            {/* Controls */}
            <div className="flex items-center justify-center gap-2 pt-1 border-t border-border/30">
              <button
                onClick={reset}
                disabled={currentIndex === 0}
                className="p-1 rounded text-muted hover:text-foreground hover:bg-elevated transition-colors duration-150 disabled:opacity-40 disabled:cursor-not-allowed active:scale-95"
                title="Reset"
              >
                <RotateCcw className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={stepBack}
                disabled={currentIndex === 0}
                className="p-1 rounded text-muted hover:text-foreground hover:bg-elevated transition-colors duration-150 disabled:opacity-40 disabled:cursor-not-allowed active:scale-95"
                title="Step back"
              >
                <SkipBack className="w-3.5 h-3.5" />
              </button>

              <button
                onClick={playing ? stop : play}
                disabled={steps.length === 0}
                className="p-1.5 rounded bg-accent text-white hover:bg-accent/90 transition-colors duration-150 disabled:opacity-40 disabled:cursor-not-allowed active:scale-95"
                title={playing ? 'Pause' : 'Play'}
              >
                {playing ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
              </button>

              <button
                onClick={stepForward}
                disabled={currentIndex >= steps.length - 1}
                className="p-1 rounded text-muted hover:text-foreground hover:bg-elevated transition-colors duration-150 disabled:opacity-40 disabled:cursor-not-allowed active:scale-95"
                title="Step forward"
              >
                <SkipForward className="w-3.5 h-3.5" />
              </button>
            </div>

            {/* Current step detail */}
            {currentStep && (
              <div className="px-2 py-1.5 rounded bg-elevated border border-border/50 text-[10px] font-mono animate-[metric-up_0.2s_ease-out]">
                <div className="grid grid-cols-2 gap-x-3 gap-y-1">
                  <div>
                    <span className="text-muted">Action</span>
                    <div className="text-foreground">{currentStep.action}</div>
                  </div>
                  <div>
                    <span className="text-muted">Timestamp</span>
                    <div className="text-foreground tabular-nums">{formatTime(currentStep.timestamp)}</div>
                  </div>
                  {currentStep.durationMs !== undefined && (
                    <div>
                      <span className="text-muted">Duration</span>
                      <div className="text-foreground tabular-nums">{formatDuration(currentStep.durationMs)}</div>
                    </div>
                  )}
                  <div>
                    <span className="text-muted">Status</span>
                    <div className={`capitalize ${
                      currentStep.status === 'success' ? 'text-success' :
                      currentStep.status === 'warning' ? 'text-warning' :
                      currentStep.status === 'error' ? 'text-destructive' :
                      'text-muted'
                    }`}>
                      {currentStep.status}
                    </div>
                  </div>
                </div>
                {currentStep.detail && (
                  <div className="mt-1 pt-1 border-t border-border/30 text-muted">
                    {currentStep.detail}
                  </div>
                )}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}