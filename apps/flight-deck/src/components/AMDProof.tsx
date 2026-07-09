import { useState } from 'react';
import { Shield, ShieldCheck, ShieldAlert, ChevronDown, ChevronRight, Fingerprint, Cpu, Hash, QrCode, RefreshCw } from 'lucide-react';
import type { AMDMeasurement } from '../types';

function HashDisplay({ label, value, color }: { label: string; value: string; color: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <div className="flex items-center gap-1.5">
      <span className="text-muted text-[9px] whitespace-nowrap">{label}</span>
      <code
        onClick={() => { navigator.clipboard.writeText(value); setCopied(true); setTimeout(() => setCopied(false), 1500); }}
        className="text-[9px] font-mono truncate px-1 py-0.5 rounded bg-elevated border border-border/30 cursor-pointer hover:border-accent/30 transition-colors"
        style={{ color, maxWidth: 140 }}
        title={value}
      >
        {copied ? 'copied!' : value.length > 20 ? `${value.slice(0, 16)}...` : value}
      </code>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  switch (status) {
    case 'verified':
      return (
        <span className="flex items-center gap-1 text-[9px] font-mono text-success">
          <ShieldCheck className="w-2.5 h-2.5" />
          Verified
        </span>
      );
    case 'pending':
      return (
        <span className="flex items-center gap-1 text-[9px] font-mono text-warning">
          <ShieldAlert className="w-2.5 h-2.5" />
          Pending
        </span>
      );
    case 'failed':
      return (
        <span className="flex items-center gap-1 text-[9px] font-mono text-destructive">
          <ShieldAlert className="w-2.5 h-2.5" />
          Failed
        </span>
      );
    default:
      return (
        <span className="flex items-center gap-1 text-[9px] font-mono text-muted">
          <Shield className="w-2.5 h-2.5" />
          Unknown
        </span>
      );
  }
}

export default function AMDProof({ measurements }: { measurements: AMDMeasurement[] }) {
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const verifiedCount = measurements.filter(m => m.status === 'verified').length;

  return (
    <div className="panel panel-sweep">
      <div className="panel-header">
        <span className="panel-title">AMD Proof</span>
        <span className="text-[10px] font-mono text-muted">
          {verifiedCount}/{measurements.length} verified
        </span>
      </div>
      <div className="panel-body space-y-1.5">
        {measurements.length === 0 ? (
          <div className="py-6 text-center text-muted text-xs">
            No attestation measurements. Run on AMD SEV-SNP hardware to enable.
          </div>
        ) : (
          measurements.map((m) => {
            const isExpanded = expandedId === m.id;
            return (
              <div key={m.id}>
                <div
                  onClick={() => setExpandedId(isExpanded ? null : m.id)}
                  className={`flex items-center gap-2 px-2 py-1.5 rounded border transition-colors duration-200 cursor-pointer select-none active:scale-[0.99] ${
                    m.status === 'failed'
                      ? 'border-destructive/30 bg-destructive/5'
                      : m.status === 'pending'
                      ? 'border-warning/20 bg-warning/5'
                      : 'border-border hover:border-accent/20'
                  }`}
                >
                  <span className="flex-shrink-0 text-accent">
                    <Cpu className="w-3 h-3" />
                  </span>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1.5">
                      <span className="font-mono text-[11px] text-foreground truncate">
                        {m.measurementId}
                      </span>
                      <StatusBadge status={m.status} />
                    </div>
                    <div className="text-[9px] font-mono text-muted mt-0.5">
                      SNP{fw(m.firmwareVersion)} · {m.tcbVersion}
                    </div>
                  </div>

                  <span className="text-muted flex-shrink-0">
                    {isExpanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
                  </span>
                </div>

                {isExpanded && (
                  <div className="mx-2 mt-1 mb-1.5 px-2 py-1.5 rounded bg-elevated border border-border/50 text-[10px] font-mono space-y-1.5 animate-[metric-up_0.2s_ease-out]">
                    <HashDisplay label="LAUNCH_DIGEST:" value={m.launchDigest} color="var(--color-accent)" />
                    <HashDisplay label="REPORT_ID:" value={m.reportId} color="var(--color-success)" />
                    <HashDisplay label="SIGNATURE:" value={m.signature} color="var(--color-warning)" />

                    <div className="flex items-center justify-between pt-1 border-t border-border/30">
                      <div className="flex items-center gap-1 text-muted">
                        <Hash className="w-2.5 h-2.5" />
                        <span className="text-[9px]">MEASUREMENT_ID:</span>
                        <span className="text-foreground text-[9px]">{m.measurementId}</span>
                      </div>
                      <button
                        onClick={(e) => { e.stopPropagation(); }}
                        className="flex items-center gap-1 text-[9px] text-accent hover:text-accent/80 transition-colors"
                      >
                        <RefreshCw className="w-2.5 h-2.5" />
                        Re-verify
                      </button>
                    </div>

                    {m.status === 'failed' && (
                      <div className="pt-1 border-t border-border/30 flex items-start gap-1 text-destructive">
                        <ShieldAlert className="w-2.5 h-2.5 flex-shrink-0 mt-0.5" />
                        <span className="text-[9px]">
                          Attestation failed — TCB mismatch or hardware tamper detected.
                        </span>
                      </div>
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

function fw(v: number): string {
  return `v${Math.floor(v)}`;
}