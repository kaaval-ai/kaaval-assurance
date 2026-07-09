import { useState, Fragment } from 'react';
import { BarChart3, TrendingUp, TrendingDown, ChevronDown, ChevronRight, AlertTriangle } from 'lucide-react';
import type { ModelEntry } from '../types';

function formatCost(c: number): string {
  if (c < 0.001) return `$${(c * 1000).toFixed(1)}/K`;
  return `$${c.toFixed(3)}`;
}

function formatSeconds(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

export default function ModelComparison({ models }: { models: ModelEntry[] }) {
  const [expanded, setExpanded] = useState<string | null>(null);

  return (
    <div className="panel panel-sweep">
      <div className="panel-header">
        <span className="panel-title">Model Comparison</span>
        <span className="text-[10px] font-mono text-muted">{models.filter(m => m.status === 'active').length} active</span>
      </div>
      <div className="panel-body overflow-x-auto">
        {models.length === 0 ? (
          <div className="py-6 text-center text-muted text-xs">
            No models loaded. Connect a provider to start benchmarking.
          </div>
        ) : (
          <table className="w-full text-[10px] font-mono">
            <thead>
              <tr className="text-muted border-b border-border">
                <th className="text-left py-1.5 pr-2 font-semibold">Model</th>
                <th className="text-right px-1.5 py-1.5 font-semibold">P50</th>
                <th className="text-right px-1.5 py-1.5 font-semibold">P95</th>
                <th className="text-right px-1.5 py-1.5 font-semibold">Throughput</th>
                <th className="text-right px-1.5 py-1.5 font-semibold">Cost</th>
                <th className="text-right px-1.5 py-1.5 font-semibold">Accuracy</th>
                <th className="text-right px-1.5 py-1.5 font-semibold">Hallucination</th>
                <th className="text-right pl-1.5 py-1.5 font-semibold">Status</th>
                <th className="w-5" />
              </tr>
            </thead>
            <tbody>
              {models.map((m) => {
                const isExpanded = expanded === m.id;
                return (
                  <Fragment key={m.id}>
                    <tr
                      onClick={() => setExpanded(isExpanded ? null : m.id)}
                      className="border-b border-border/50 hover:bg-elevated/50 transition-colors duration-150 cursor-pointer select-none"
                    >
                      <td className="py-1.5 pr-2">
                        <div className="flex items-center gap-1.5">
                          <BarChart3 className="w-3 h-3 text-accent flex-shrink-0" />
                          <span className="text-foreground font-medium">{m.name}</span>
                          <span className="text-muted ml-0.5">({m.provider})</span>
                        </div>
                      </td>
                      <td className="text-right px-1.5 py-1.5 tabular-nums text-foreground">{m.metrics.latencyP50}ms</td>
                      <td className="text-right px-1.5 py-1.5 tabular-nums text-muted">{m.metrics.latencyP95}ms</td>
                      <td className="text-right px-1.5 py-1.5 tabular-nums text-foreground">{m.metrics.throughput}/s</td>
                      <td className="text-right px-1.5 py-1.5 tabular-nums text-foreground">{formatCost(m.metrics.costPerToken)}</td>
                      <td className="text-right px-1.5 py-1.5 tabular-nums">
                        <span className={m.metrics.accuracy >= 0.95 ? 'text-success' : m.metrics.accuracy >= 0.90 ? 'text-warning' : 'text-destructive'}>
                          {(m.metrics.accuracy * 100).toFixed(0)}%
                        </span>
                      </td>
                      <td className="text-right px-1.5 py-1.5 tabular-nums">
                        <span className="flex items-center justify-end gap-0.5">
                          {m.metrics.hallucinationRate < 0.02 ? (
                            <TrendingDown className="w-2.5 h-2.5 text-success" />
                          ) : (
                            <TrendingUp className="w-2.5 h-2.5 text-warning" />
                          )}
                          {(m.metrics.hallucinationRate * 100).toFixed(1)}%
                        </span>
                      </td>
                      <td className="text-right pl-1.5 py-1.5">
                        <span className={`inline-block px-1.5 py-0.5 rounded text-[9px] font-semibold uppercase ${
                          m.status === 'active' ? 'bg-success/10 text-success' :
                          m.status === 'staging' ? 'bg-warning/10 text-warning' :
                          'bg-muted/10 text-muted'
                        }`}>
                          {m.status}
                        </span>
                      </td>
                      <td className="text-right pl-1 py-1.5">
                        <span className="text-muted">
                          {isExpanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
                        </span>
                      </td>
                    </tr>

                    {/* Expanded detail — sibling row */}
                    {isExpanded && (
                      <tr>
                        <td colSpan={9} className="p-0 border-b border-border/50">
                          <div className="mx-2 mb-1.5 px-2 py-1.5 rounded bg-elevated border border-border/50 text-[10px] font-mono animate-[metric-up_0.2s_ease-out]">
                            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                              <div className="space-y-0.5">
                                <span className="text-muted text-[9px] uppercase tracking-wider">Latency</span>
                                <div className="text-foreground tabular-nums">
                                  <span className="text-muted">P50: </span>{m.metrics.latencyP50}ms
                                  <span className="text-muted ml-1.5">P95: </span>{formatSeconds(m.metrics.latencyP95)}
                                </div>
                              </div>
                              <div className="space-y-0.5">
                                <span className="text-muted text-[9px] uppercase tracking-wider">Throughput</span>
                                <div className="text-foreground tabular-nums">{m.metrics.throughput} req/s</div>
                              </div>
                              <div className="space-y-0.5">
                                <span className="text-muted text-[9px] uppercase tracking-wider">Cost</span>
                                <div className="text-foreground tabular-nums">{formatCost(m.metrics.costPerToken)} per token</div>
                              </div>
                              <div className="space-y-0.5">
                                <span className="text-muted text-[9px] uppercase tracking-wider">Quality</span>
                                <div className="text-foreground tabular-nums flex items-center gap-1.5">
                                  <span>Accuracy: {(m.metrics.accuracy * 100).toFixed(0)}%</span>
                                  <span className="text-muted">|</span>
                                  <span className={m.metrics.hallucinationRate < 0.02 ? 'text-success' : 'text-warning'}>
                                    Hall: {(m.metrics.hallucinationRate * 100).toFixed(1)}%
                                  </span>
                                </div>
                              </div>
                            </div>
                            {m.status === 'staging' && (
                              <div className="mt-1.5 pt-1.5 border-t border-border/30 flex items-center gap-1 text-warning">
                                <AlertTriangle className="w-2.5 h-2.5 flex-shrink-0" />
                                <span>Staging — not yet promoted to production. Monitor accuracy before release.</span>
                              </div>
                            )}
                            {m.status === 'active' && m.metrics.hallucinationRate >= 0.025 && (
                              <div className="mt-1.5 pt-1.5 border-t border-border/30 flex items-center gap-1 text-warning">
                                <AlertTriangle className="w-2.5 h-2.5 flex-shrink-0" />
                                <span>Hallucination rate above 2.5% — consider evaluation or fallback.</span>
                              </div>
                            )}
                          </div>
                        </td>
                      </tr>
                    )}
                  </Fragment>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}