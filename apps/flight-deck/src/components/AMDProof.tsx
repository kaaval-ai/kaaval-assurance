import { Cpu, Clock } from 'lucide-react';
import type { AmdEvidence, Provenance, RuntimeProbeReport, TelemetrySummary } from '../types';
import { NotAvailable, SourceChip } from './Tags';
import type { SourceTag } from '../types';

/* AMD Runtime Evidence — consumes runtime-probe artifacts only.
   No attestations, signatures, digests, or firmware claims of any kind:
   evidence here means measured host facts from the probe (rocm-smi, vLLM
   version, served model) plus configured serving parameters, each with its
   source tag. */

function Row({ label, value, tag }: { label: string; value: string | null; tag: SourceTag }) {
  return (
    <div className="flex items-center justify-between gap-2 text-[10px] font-mono">
      <span className="text-muted">{label}</span>
      <span className="flex items-center gap-1.5 min-w-0">
        {value ? <span className="text-foreground truncate" title={value}>{value}</span> : <NotAvailable />}
        <SourceChip tag={tag} />
      </span>
    </div>
  );
}

const STATUS_BANNER: Record<AmdEvidence['status'], { cls: string; text: string }> = {
  measured: { cls: 'border-success/40 bg-success/5 text-success', text: 'MEASURED AMD RUN — probe artifact captured on AMD hardware' },
  configured: { cls: 'border-accent/40 bg-accent/5 text-accent', text: 'Serving settings configured — AMD GPU measured run pending.' },
  pending: { cls: 'border-warning/40 bg-warning/5 text-warning', text: 'AMD GPU measured run pending.' },
  unavailable: { cls: 'border-border bg-elevated/40 text-muted', text: 'No runtime evidence available.' },
};

export default function AMDProof({
  probe,
  provenance,
  amd,
  telemetry,
}: {
  probe: RuntimeProbeReport | null;
  provenance: Provenance;
  amd: AmdEvidence;
  telemetry: TelemetrySummary | null;
}) {
  const banner = STATUS_BANNER[amd.status];
  const commands = probe?.commands ?? {};
  const rocmProduct = commands['rocm_smi_product'];
  const rocmVram = commands['rocm_smi_vram'];
  const vllmCli = commands['vllm_version'];
  const endpoint = probe?.endpoint ?? null;
  const profile = telemetry?.runtime.profile ?? null;
  const cmdTag = (c?: { available: boolean }): SourceTag =>
    c?.available ? 'measured' : 'not_available';
  const cmdValue = (c?: { available: boolean; output: string | null; error: string | null }) =>
    c?.available ? (c.output || '').split('\n')[0] : null;

  return (
    <div className="panel panel-sweep">
      <div className="panel-header">
        <span className="panel-title flex items-center gap-1.5">
          <Cpu className="w-3 h-3 text-accent" />
          AMD Runtime Evidence
        </span>
        <span className="text-[10px] font-mono text-muted">
          probe: {provenance.available ? provenance.origin : 'not captured'}
        </span>
      </div>
      <div className="panel-body space-y-2">
        <div className={`px-2 py-1.5 rounded border text-[10px] font-mono ${banner.cls}`}>
          {banner.text}
          <div className="text-muted mt-0.5">{amd.reason}</div>
        </div>

        <div className="space-y-1">
          <span className="text-[9px] font-mono text-muted uppercase tracking-wider">Probe facts</span>
          {probe ? (
            <>
              <Row label="GPU product (rocm-smi)" value={cmdValue(rocmProduct)} tag={cmdTag(rocmProduct)} />
              <Row label="VRAM (rocm-smi)" value={cmdValue(rocmVram)} tag={cmdTag(rocmVram)} />
              <Row label="vLLM CLI version" value={cmdValue(vllmCli)} tag={cmdTag(vllmCli)} />
              <Row
                label="Endpoint / served model"
                value={
                  endpoint
                    ? endpoint.reachable
                      ? endpoint.served_models.join(', ') || 'reachable, none reported'
                      : 'endpoint unreachable at probe time'
                    : null
                }
                tag={endpoint?.reachable ? 'measured' : 'not_available'}
              />
              <Row label="Model family" value={endpoint?.model_family ?? null} tag="configured" />
              <Row
                label="Under /workspace"
                value={probe.system ? String(probe.system.under_workspace) : null}
                tag="measured"
              />
              {provenance.modified_at && (
                <div className="flex items-center gap-1 text-[9px] font-mono text-muted pt-1">
                  <Clock className="w-2.5 h-2.5" />
                  probe captured {new Date(provenance.modified_at).toLocaleString('en-GB')}
                  {provenance.origin === 'sample' && ' · sample data, not an AMD run'}
                </div>
              )}
            </>
          ) : (
            <div className="py-2">
              <NotAvailable note="no runtime-probe artifact — run python -m kaaval_assurance.runtime_probe on the AMD pod" />
            </div>
          )}
        </div>

        <div className="space-y-1 pt-1 border-t border-border/30">
          <span className="text-[9px] font-mono text-muted uppercase tracking-wider">
            Configured serving parameters
          </span>
          {profile ? (
            <>
              <Row label="Hardware target" value={profile.hardware_target} tag="configured" />
              <Row label="Served model id" value={profile.model_id} tag="configured" />
              <Row label="Model family" value={profile.model_family ?? null} tag="configured" />
              <Row label="Endpoint type" value={profile.endpoint_type ?? null} tag="configured" />
              <Row label="ROCm version" value={profile.rocm_version ?? null} tag={profile.rocm_version ? 'configured' : 'not_available'} />
              <Row label="vLLM version" value={profile.vllm_version ?? null} tag={profile.vllm_version ? 'configured' : 'not_available'} />
              <Row label="dtype / KV cache" value={`${profile.dtype || 'n/a'} / ${profile.kv_cache_dtype || 'n/a'}`} tag="configured" />
              <Row label="Tensor parallel / GPU mem util" value={`${profile.tensor_parallel_size ?? 'n/a'} / ${profile.gpu_memory_utilization ?? 'n/a'}`} tag="configured" />
              <Row label="Structured output" value={profile.structured_output_mode ?? null} tag="configured" />
            </>
          ) : (
            <div className="text-[10px] font-mono text-muted flex items-center gap-1.5">
              <span>mock local tier in this run — Gemma via ROCm + vLLM is the planned AMD target</span>
              <SourceChip tag="planned" />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
