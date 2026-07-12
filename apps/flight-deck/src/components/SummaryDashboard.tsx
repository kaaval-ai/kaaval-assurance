import { useState } from 'react';
import { Shield, Activity, ChevronDown, Target, Eye, GitBranch, ScrollText, BarChart3, Server, Cpu, ListChecks } from 'lucide-react';
import type { DashboardPayload } from '../types';
import { DataLabelBadge, NotAvailable, SourceChip, pct, usd } from './Tags';
import ProofStrip from './ProofStrip';
import CostAvoidanceReceipt from './CostAvoidanceReceipt';
import DemoScriptRail from './DemoScriptRail';
import PipelinePanel from './PipelinePanel';
import ProviderSwitchboard from './ProviderSwitchboard';
import ContractGate from './ContractGate';
import ModelComparison from './ModelComparison';
import TelemetryTruth from './TelemetryTruth';
import TrajectoryReplay from './TrajectoryReplay';
import AMDProof from './AMDProof';

/* Every number on this view derives from the dashboard payload. Missing data
   renders as not available — never as a hardcoded placeholder. */

function StatCard({ label, value, sub, color }: { label: string; value: string; sub?: string; color?: string }) {
  return (
    <div className="flex flex-col gap-0.5 px-3 py-2.5 rounded-lg border border-border/50 bg-surface/50">
      <div className="text-[10px] font-mono text-muted uppercase tracking-wider">{label}</div>
      <div className={`text-base font-semibold font-heading tabular-nums ${color || 'text-foreground'}`}>{value}</div>
      {sub && <div className="text-[10px] font-mono text-muted">{sub}</div>}
    </div>
  );
}

const PANELS = [
  { icon: <GitBranch className="w-3 h-3" />, label: 'Assurance Pipeline', desc: 'One request traced through router, local tier, Layer-1 verification, and (when needed) escalation.', neon: '#00D4FF' },
  { icon: <Server className="w-3 h-3" />, label: 'Provider Switchboard', desc: 'Providers that actually served attempts in the captured run, with measured latency and contract-conformance rates.', neon: '#34C759' },
  { icon: <ScrollText className="w-3 h-3" />, label: 'Contract Gate', desc: 'The four telecom task contracts and their deterministic Layer-1 checks — shape and constraints, not semantic truth.', neon: '#FFB000' },
  { icon: <BarChart3 className="w-3 h-3" />, label: 'Tier Comparison', desc: 'Local Gemma-first tier vs Fireworks escalation, from captured measurements only.', neon: '#FF6B9D' },
  { icon: <Activity className="w-3 h-3" />, label: 'Telemetry Truth', desc: 'Every claim with its source tag: measured, configured, planned, or honestly not available.', neon: '#7CFF7C' },
  { icon: <ListChecks className="w-3 h-3" />, label: 'Trajectory Replay', desc: 'Replayable stored attempts: exact inputs, outputs, failed check IDs, cost.', neon: '#A78BFA' },
  { icon: <Cpu className="w-3 h-3" />, label: 'AMD Runtime Evidence', desc: 'Runtime-probe facts (rocm-smi, vLLM, served model) plus configured serving parameters. Pending until a real AMD probe artifact exists.', neon: '#FF8C42' },
] as const;

export default function SummaryDashboard({ payload }: { payload: DashboardPayload | null }) {
  const [introOpen, setIntroOpen] = useState(false);
  const [deepDiveOpen, setDeepDiveOpen] = useState(false);
  const t = payload?.telemetry ?? null;

  return (
    <div className="space-y-3">
      <ProofStrip payload={payload} />
      <DemoScriptRail payload={payload} />
      <DemoScriptRail payload={payload} />



      {/* Deep Dive Accordion */}
      <div className="panel panel-sweep overflow-hidden mt-6 border-accent/30">
        <button
          onClick={() => setDeepDiveOpen(!deepDiveOpen)}
          className="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-surface/50 transition-colors"
        >
          <div className="flex items-center gap-2 text-accent">
            <BarChart3 className="w-4 h-4" />
            <span className="text-sm font-heading font-semibold tracking-wider">DEEP DIVE: TELEMETRY & AUDIT</span>
          </div>
          <ChevronDown className={`w-4 h-4 text-muted transition-transform ${deepDiveOpen ? 'rotate-180' : ''}`} />
        </button>

        {deepDiveOpen && (
          <div className="p-3 md:p-4 space-y-4 border-t border-border/40 bg-surface/30">
            {/* Mission intro — truthful copy */}
            <div className="panel panel-sweep overflow-hidden">
              <button
                onClick={() => setIntroOpen(!introOpen)}
                className="w-full flex items-center gap-2 px-3 py-2.5 text-left hover:opacity-80 transition-opacity"
              >
                <Shield className="w-4 h-4 flex-shrink-0 text-accent" />
                <span className="text-sm font-heading font-semibold text-foreground tracking-wide truncate">
                  Kaaval Assurance — Inference Flight Deck
                </span>
                {payload && <DataLabelBadge label={payload.label} />}
                <span className="ml-auto text-muted" style={{ transform: introOpen ? 'rotate(0deg)' : 'rotate(-90deg)' }}>
                  <ChevronDown className="w-3.5 h-3.5" />
                </span>
              </button>

              {introOpen && (
                <div className="px-3 pb-3 space-y-3 border-t border-border/40 pt-2.5 animate-[fadeSlideIn_0.25s_ease-out]">
                  <div>
                    <div className="flex items-center gap-1.5 mb-1.5">
                      <Target className="w-3 h-3 text-accent" />
                      <span className="text-sm font-heading font-semibold text-foreground uppercase tracking-wider">What this shows</span>
                    </div>
                    <p className="text-sm font-mono text-muted leading-relaxed">
                      A captured-run observability surface for the Kaaval Assurance inference plane:
                      a Gemma-first local tier is checked against explicit task contracts (Layer 1),
                      escalates to Fireworks only when verification fails, and feeds per-category
                      drift tracking (Layer 2) and a calibrated sampled audit (Layer 3). Every value
                      on screen carries a source tag; sample data is labeled as sample, and AMD
                      runtime claims stay pending until a real probe artifact exists.
                    </p>
                  </div>
                  <div>
                    <div className="flex items-center gap-1.5 mb-1.5">
                      <Eye className="w-3 h-3 text-accent" />
                      <span className="text-sm font-heading font-semibold text-foreground uppercase tracking-wider">Dashboard panels</span>
                    </div>
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-1.5">
                      {PANELS.map((item) => (
                        <div key={item.label} className="flex items-start gap-1.5 px-2 py-1.5 rounded bg-surface/30 border border-border/20" style={{ borderColor: `${item.neon}20` }}>
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

            {/* KPI row — payload-derived only */}
            {t ? (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                <StatCard label="Requests / attempts" value={`${t.requests} / ${t.attempts}`} sub="captured run" />
                <StatCard label="Final contract-conformance" value={pct(t.verification.final_verified_rate)} color="text-success" sub={`local: ${pct(t.verification.local_verified_rate)}`} />
                <StatCard label="Escalation rate" value={pct(t.routing.escalation_rate)} color={t.routing.escalation_rate > 0.2 ? 'text-warning' : 'text-foreground'} sub={`pre-route remote: ${pct(t.routing.preroute_remote_rate)}`} />
                <StatCard label="Cost / conformant answer" value={usd(t.cost.cost_per_verified_answer_usd)} sub="configured pricing" />
              </div>
            ) : (
              <div className="panel px-3 py-4 text-center text-muted text-xs font-mono">
                No telemetry artifact loaded — KPIs <NotAvailable />
              </div>
            )}

            <CostAvoidanceReceipt
              comparison={payload?.comparison ?? null}
              provenance={payload?.comparison_provenance ?? null}
            />
            
            {t && (
              <>
                {/* Row 2: provider mix + drift + audit */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                  <div className="panel panel-sweep">
                    <div className="panel-header">
                      <span className="panel-title">Provider Mix</span>
                      <SourceChip tag={payload?.used_sample ? 'sample' : 'measured'} />
                    </div>
                    <div className="panel-body space-y-1.5">
                      {Object.entries(t.provider_mix.attempts_by_provider).map(([provider, attempts]) => (
                        <div key={provider} className="flex items-center justify-between text-[11px] font-mono">
                          <span className="text-foreground">{provider}</span>
                          <span className="text-muted tabular-nums">{attempts} attempt{attempts === 1 ? '' : 's'}</span>
                        </div>
                      ))}
                      <div className="pt-1 border-t border-border/30 flex items-center justify-between text-[10px] font-mono text-muted">
                        <span>local / remote attempts</span>
                        <span className="tabular-nums">{t.provider_mix.local_attempts} / {t.provider_mix.remote_attempts}</span>
                      </div>
                    </div>
                  </div>

                  <div className="panel panel-sweep">
                    <div className="panel-header">
                      <span className="panel-title">Layer-2 Drift</span>
                      <SourceChip tag={payload?.used_sample ? 'sample' : 'measured'} />
                    </div>
                    <div className="panel-body space-y-1.5">
                      {Object.entries(t.routing.ewma_drift_by_category).map(([category, drift]) => (
                        <div key={category} className="flex items-center gap-2 text-[10px] font-mono">
                          <span className="text-foreground flex-1 truncate">{category}</span>
                          <div className="w-16 bg-elevated rounded-full h-1.5 overflow-hidden">
                            <div
                              className={`h-full rounded-full ${drift >= 0.5 ? 'bg-destructive' : drift >= 0.2 ? 'bg-warning' : 'bg-success'}`}
                              style={{ width: `${Math.min(drift * 100, 100)}%` }}
                            />
                          </div>
                          <span className="text-muted tabular-nums w-8 text-right">{drift.toFixed(2)}</span>
                        </div>
                      ))}
                      {Object.keys(t.routing.ewma_drift_by_category).length === 0 && <NotAvailable />}
                    </div>
                  </div>

                  <div className="panel panel-sweep">
                    <div className="panel-header">
                      <span className="panel-title">Layer-3 Audit</span>
                      <SourceChip tag={t.audit.enabled ? (payload?.used_sample ? 'sample' : 'measured') : 'not_available'} />
                    </div>
                    <div className="panel-body space-y-1.5 text-[10px] font-mono">
                      {t.audit.enabled ? (
                        <>
                          <div className="flex justify-between"><span className="text-muted">sampled</span><span className="text-foreground tabular-nums">{t.audit.sampled}/{t.audit.accepted_answers} accepted</span></div>
                          <div className="flex justify-between"><span className="text-muted">signal</span><span className={t.audit.trusted ? 'text-success' : 'text-warning'}>{t.audit.trusted ? 'trusted' : 'untrusted (display only)'}</span></div>
                          <div className="flex justify-between"><span className="text-muted">calibration FP rate</span><span className="text-foreground tabular-nums">{pct(t.audit.calibration_fp_rate)} / {pct(t.audit.calibration_threshold)}</span></div>
                          <div className="flex justify-between"><span className="text-muted">pass / fail / errors</span><span className="text-foreground tabular-nums">{t.audit.passed} / {t.audit.failed} / {t.audit.errors}</span></div>
                          <p className="pt-1 border-t border-border/30 text-muted leading-relaxed">
                            Detection is model-generated; aggregation, calibration, and thresholds are deterministic.
                          </p>
                        </>
                      ) : (
                        <NotAvailable note="no audit in this captured run" />
                      )}
                    </div>
                  </div>
                </div>

                {/* Claims preview */}
                {t.claims.length > 0 && (
                  <div className="panel panel-sweep">
                    <div className="panel-header">
                      <span className="panel-title">Claims — every value with its source</span>
                      <span className="text-[10px] font-mono text-muted">{t.claims.length} claims</span>
                    </div>
                    <div className="panel-body">
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5">
                        {t.claims.map((c) => {
                          const claimLabel = {
                            'Local verified rate': 'Local Layer-1 contract-conformance rate',
                            'Final verified rate': 'Final Layer-1 contract-conformance rate',
                            'Cost per verified answer': 'Cost per contract-conformant answer',
                          }[c.claim] ?? c.claim;
                          const claimSource = c.field.startsWith('cost.') ? 'configured' : c.source;
                          return (
                          <div key={c.claim} className="flex items-center gap-2 px-2 py-1 rounded border border-border/40 text-[10px] font-mono">
                            <span className="text-muted flex-1 truncate">{claimLabel}</span>
                            <span className="text-foreground truncate max-w-[45%]" title={c.value}>{c.value}</span>
                            <SourceChip tag={claimSource === 'measured' && payload?.used_sample ? 'sample' : claimSource} />
                          </div>
                          );
                        })}
                      </div>
                    </div>
                  </div>
                )}

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
                  <PipelinePanel trajectory={payload?.trajectory ?? null} telemetry={t} />
                  <ProviderSwitchboard telemetry={t} usedSample={payload?.used_sample ?? false} />
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
                  <div className="lg:col-span-1">
                    <ContractGate telemetry={t} />
                  </div>
                  <div className="lg:col-span-2">
                    <TelemetryTruth telemetry={t} usedSample={payload?.used_sample ?? false} />
                  </div>
                </div>

                <ModelComparison telemetry={t} usedSample={payload?.used_sample ?? false} />

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
                  <div className="lg:col-span-2">
                    <TrajectoryReplay rows={payload?.trajectory ?? []} label={payload?.label ?? 'UNAVAILABLE'} />
                  </div>
                  <div className="lg:col-span-1">
                    {payload && (
                      <AMDProof
                        probe={payload.runtime_probe}
                        provenance={payload.provenance.runtime_probe}
                        amd={payload.amd}
                        telemetry={t}
                      />
                    )}
                  </div>
                </div>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
