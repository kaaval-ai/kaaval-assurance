import { useState } from 'react';
import { CheckCircle, Loader2, XCircle, Circle, ChevronDown, ChevronRight } from 'lucide-react';
import type { PipelineStage, StageStatus } from '../types';

const statusIcon = (status: StageStatus) => {
  switch (status) {
    case 'passed': return <CheckCircle className="w-3.5 h-3.5 text-success" />;
    case 'running': return <Loader2 className="w-3.5 h-3.5 text-accent animate-spin" />;
    case 'failed': return <XCircle className="w-3.5 h-3.5 text-destructive" />;
    case 'idle': return <Circle className="w-3.5 h-3.5 text-muted" />;
  }
};

const statusColor = (status: StageStatus) => {
  switch (status) {
    case 'passed': return 'border-success/30 bg-success/5';
    case 'running': return 'border-accent/30 bg-accent/5';
    case 'failed': return 'border-destructive/30 bg-destructive/5';
    case 'idle': return 'border-border bg-transparent';
  }
};

const stageDescription: Record<string, string> = {
  'Input Validation': 'Checks prompt format, token limits, and schema compliance before any processing begins.',
  'Policy Check': 'Scans for PII, toxic content, and policy violations. Every request is checked against active governance rules.',
  'Provider Routing': 'Selects the optimal provider based on latency, cost, and availability. Supports automatic failover.',
  'Inference': 'The model generates a response. Duration depends on token count and provider speed.',
  'Output Verification': 'Validates the response for hallucinations, bias, and factual grounding before delivery.',
  'Attestation': 'AMD SEV-SNP hardware attestation confirms the inference ran inside a trusted execution environment.',
};

export default function PipelinePanel({ stages }: { stages: PipelineStage[] }) {
  const [expanded, setExpanded] = useState<string | null>(null);

  return (
    <div className="panel panel-sweep">
      <div className="panel-header">
        <span className="panel-title">Live Pipeline</span>
        <span className="text-[10px] font-mono text-muted">
          {stages.filter(s => s.status === 'running').length > 0 ? (
            <span className="text-accent">In flight</span>
          ) : (
            <span className="text-success">All clear</span>
          )}
        </span>
      </div>
      <div className="panel-body space-y-1">
        {stages.length === 0 ? (
          <div className="py-6 text-center text-muted text-xs">
            No pipeline stages configured. Add a model contract to begin.
          </div>
        ) : (
          stages.map((stage, i) => {
            const isExpanded = expanded === stage.id;
            return (
              <div key={stage.id}>
                <div
                  onClick={() => setExpanded(isExpanded ? null : stage.id)}
                  className={`flex items-center gap-2 px-2 py-1.5 rounded border ${statusColor(stage.status)} transition-colors duration-200 cursor-pointer select-none active:scale-[0.99]`}
                >
                  <span className="flex-shrink-0">{statusIcon(stage.status)}</span>
                  <span className="font-mono text-[11px] text-foreground flex-1">{stage.label}</span>
                  {stage.durationMs > 0 && (
                    <span className="font-mono text-[10px] text-muted tabular-nums">
                      {stage.durationMs}ms
                    </span>
                  )}
                  <span className="text-muted">
                    {isExpanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
                  </span>
                  {i < stages.length - 1 && (
                    <div className="hidden sm:block w-px h-4 bg-border mx-1" />
                  )}
                </div>

                {/* Expanded detail */}
                {isExpanded && (
                  <div className="mx-2 mt-1 mb-1.5 px-2 py-1.5 rounded bg-elevated border border-border/50 text-[10px] font-mono space-y-1 animate-[metric-up_0.2s_ease-out]">
                    <p className="text-muted leading-relaxed">{stageDescription[stage.label]}</p>
                    {stage.logs.length > 0 && (
                      <div className="pt-1 border-t border-border/30">
                        {stage.logs.map((log, li) => (
                          <div key={li} className="text-muted/80 flex items-start gap-1">
                            <span className="text-border">▸</span>
                            <span>{log}</span>
                          </div>
                        ))}
                      </div>
                    )}
                    {stage.logs.length === 0 && stage.status === 'idle' && (
                      <div className="text-muted/60 italic">Waiting for previous stage to complete…</div>
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