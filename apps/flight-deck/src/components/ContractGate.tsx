import { useState } from 'react';
import { ShieldCheck, ShieldX, ChevronDown, ChevronRight, Scale, Globe, Cpu, Eye, Lock, AlertTriangle } from 'lucide-react';
import type { Policy, PolicyStatus } from '../types';

const policyIcons: Record<string, React.ReactNode> = {
  'geo-fence': <Globe className="w-3 h-3" />,
  'jurisdiction': <Scale className="w-3 h-3" />,
  'data-residency': <Cpu className="w-3 h-3" />,
  'compliance': <Eye className="w-3 h-3" />,
  'encryption': <Lock className="w-3 h-3" />,
};

const statusIcon = (status: PolicyStatus) => {
  switch (status) {
    case 'pass': return <ShieldCheck className="w-3 h-3 text-success" />;
    case 'warn': return <AlertTriangle className="w-3 h-3 text-warning" />;
    case 'fail': return <ShieldX className="w-3 h-3 text-destructive" />;
    case 'pending': return <span className="w-3 h-3 rounded-full border border-border animate-pulse" />;
  }
};

const statusBarClass = (status: PolicyStatus) => {
  switch (status) {
    case 'pass': return 'bg-success';
    case 'warn': return 'bg-warning';
    case 'fail': return 'bg-destructive';
    case 'pending': return 'bg-muted';
  }
};

export default function ContractGate({ policies }: { policies: Policy[] }) {
  const [expanded, setExpanded] = useState<string | null>(null);
  const passCount = policies.filter(p => p.status === 'pass').length;
  const failCount = policies.filter(p => p.status === 'fail').length;

  return (
    <div className="panel panel-sweep">
      <div className="panel-header">
        <span className="panel-title">Contract Gate</span>
        <span className="text-[10px] font-mono text-muted">
          {failCount > 0 ? (
            <span className="text-destructive">{failCount} failed</span>
          ) : (
            <span className="text-success">{passCount} passed</span>
          )}
          {' | '}{policies.length} policies
        </span>
      </div>
      <div className="panel-body space-y-1.5">
        {policies.length === 0 ? (
          <div className="py-6 text-center text-muted text-xs">
            No policies defined. Create a compliance policy to enforce contract gates.
          </div>
        ) : (
          policies.map((p) => {
            const isExpanded = expanded === p.id;
            return (
              <div key={p.id}>
                <div
                  onClick={() => setExpanded(isExpanded ? null : p.id)}
                  className={`flex items-center gap-2 px-2 py-1.5 rounded border transition-colors duration-200 cursor-pointer select-none active:scale-[0.99] ${
                    p.status === 'fail'
                      ? 'border-destructive/30 bg-destructive/5'
                      : p.status === 'warn'
                      ? 'border-warning/20 bg-warning/5'
                      : 'border-border hover:border-accent/20'
                  }`}
                >
                  {/* Policy icon */}
                  <span className="flex-shrink-0 text-accent">
                    {policyIcons[p.icon] || <Scale className="w-3 h-3" />}
                  </span>

                  {/* Name */}
                  <span className="font-mono text-[11px] flex-1 truncate text-foreground">
                    {p.name}
                  </span>

                  {/* Verifier chips */}
                  <div className="hidden sm:flex items-center gap-1">
                    {p.verifiers.slice(0, 3).map((v, i) => (
                      <span
                        key={`${v}-${i}`}
                        className="inline-block px-1 py-0.5 rounded bg-elevated border border-border/50 text-[9px] font-mono text-muted leading-none"
                      >
                        {v}
                      </span>
                    ))}
                    {p.verifiers.length > 3 && (
                      <span className="text-[9px] font-mono text-muted">+{p.verifiers.length - 3}</span>
                    )}
                  </div>

                  {/* Status */}
                  <span className="flex-shrink-0">{statusIcon(p.status)}</span>

                  {/* Expand icon */}
                  <span className="text-muted flex-shrink-0">
                    {isExpanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
                  </span>
                </div>

                {/* Expanded detail */}
                {isExpanded && (
                  <div className="mx-2 mt-1 mb-1.5 px-2 py-1.5 rounded bg-elevated border border-border/50 text-[10px] font-mono space-y-1 animate-[metric-up_0.2s_ease-out]">
                    <div className="flex items-center justify-between">
                      <span className="text-muted">All verifiers</span>
                      <div className="flex items-center gap-1.5">
                        {p.verifiers.map((v, i) => (
                          <span
                            key={`${v}-${i}`}
                            className="inline-block px-1.5 py-0.5 rounded bg-elevated border border-border/50 text-[9px] text-muted"
                          >
                            {v}
                          </span>
                        ))}
                      </div>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-muted">Status</span>
                      <span className={`capitalize ${
                        p.status === 'pass' ? 'text-success' : p.status === 'warn' ? 'text-warning' : 'text-destructive'
                      }`}>
                        {p.status}
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-muted">Last verified</span>
                      <span className="text-foreground tabular-nums">
                        {new Date(p.lastVerified).toLocaleTimeString('en-GB', { hour12: false })}
                      </span>
                    </div>

                    {/* Status detail messages */}
                    {p.status === 'fail' && (
                      <div className="pt-1 border-t border-border/30 flex items-start gap-1 text-destructive">
                        <ShieldX className="w-2.5 h-2.5 flex-shrink-0 mt-0.5" />
                        <span>{p.name} — policy violation detected. Requests matching this gate will be blocked.</span>
                      </div>
                    )}
                    {p.status === 'warn' && (
                      <div className="pt-1 border-t border-border/30 flex items-start gap-1 text-warning">
                        <AlertTriangle className="w-2.5 h-2.5 flex-shrink-0 mt-0.5" />
                        <span>{p.name} — near threshold. Review verifier configuration.</span>
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