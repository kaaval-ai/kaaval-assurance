import { useEffect, useState } from 'react';
import { AlertTriangle, KeyRound, Loader2, PlugZap, Server, X } from 'lucide-react';
import { ApiError, createRuntimeConnection } from '../api';
import type {
  RuntimeCapabilities,
  RuntimeConnection,
  RuntimeProvider,
  RuntimeRole,
} from '../types';

interface Props {
  open: boolean;
  role: RuntimeRole;
  capabilities: RuntimeCapabilities;
  onClose: () => void;
  onConnected: (connection: RuntimeConnection) => void;
}

const MODEL_DEFAULTS: Record<RuntimeProvider, string> = {
  fireworks: 'accounts/fireworks/models/glm-5p2',
  ollama: '',
  vllm: '',
  openai_compatible: '',
};

const PROVIDER_LABELS: Record<RuntimeProvider, string> = {
  fireworks: 'Fireworks AI — BYOK',
  ollama: 'Ollama — local Gemma',
  vllm: 'vLLM — OpenAI-compatible',
  openai_compatible: 'HTTPS OpenAI-compatible endpoint',
};

export default function RuntimeConnectionModal({
  open,
  role,
  capabilities,
  onClose,
  onConnected,
}: Props) {
  const firstProvider = capabilities.providers[0] ?? 'fireworks';
  const [provider, setProvider] = useState<RuntimeProvider>(firstProvider);
  const [modelId, setModelId] = useState(MODEL_DEFAULTS[firstProvider]);
  const [baseUrl, setBaseUrl] = useState(capabilities.default_endpoints[firstProvider] ?? '');
  const [apiKey, setApiKey] = useState('');
  const [modelFamily, setModelFamily] = useState(firstProvider === 'fireworks' ? 'unknown' : 'gemma');
  const [structuredOutputs, setStructuredOutputs] = useState(firstProvider !== 'ollama');
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) setApiKey('');
  }, [open]);

  if (!open) return null;

  const changeProvider = (next: RuntimeProvider) => {
    setProvider(next);
    setModelId(MODEL_DEFAULTS[next]);
    setBaseUrl(capabilities.default_endpoints[next] ?? '');
    setModelFamily(next === 'fireworks' || next === 'openai_compatible' ? 'unknown' : 'gemma');
    setStructuredOutputs(next !== 'ollama');
    setApiKey('');
    setError(null);
  };

  const connect = async () => {
    setPending(true);
    setError(null);
    try {
      const connection = await createRuntimeConnection({
        provider,
        role,
        model_id: modelId,
        api_key: apiKey,
        base_url: provider === 'fireworks' ? null : baseUrl,
        model_family: modelFamily,
        structured_outputs: structuredOutputs,
        hardware_target:
          provider === 'vllm'
            ? 'local-vllm'
            : provider === 'ollama'
              ? 'local-ollama'
              : undefined,
        timeout_seconds: provider === 'ollama' ? 120 : 60,
        max_tokens: 1024,
      });
      setApiKey('');
      onConnected(connection);
      onClose();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'runtime connection failed');
    } finally {
      setPending(false);
    }
  };

  const needsKey = provider === 'fireworks' || provider === 'openai_compatible';
  const canSubmit = modelId.trim() && (provider === 'fireworks' ? apiKey.trim() : true);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4 backdrop-blur-sm">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="runtime-dialog-title"
        className="panel w-full max-w-2xl border-accent/50 shadow-[0_0_50px_rgba(34,211,238,0.12)]"
      >
        <div className="panel-header px-4 py-3">
          <div>
            <p id="runtime-dialog-title" className="panel-title flex items-center gap-2 text-sm">
              <PlugZap className="h-4 w-4 text-accent" />
              Connect {role === 'primary' ? 'primary' : 'escalation'} runtime
            </p>
            <p className="mt-1 text-[10px] font-mono text-muted">
              Connection is tested before use · credentials stay in server memory for {Math.round(capabilities.connection_ttl_seconds / 60)} minutes
            </p>
          </div>
          <button onClick={onClose} aria-label="Close runtime connection" className="text-muted hover:text-foreground">
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="panel-body space-y-4 p-4">
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
            {capabilities.providers.map((item) => (
              <button
                key={item}
                type="button"
                onClick={() => changeProvider(item)}
                className={`rounded border px-3 py-2 text-left font-mono transition-colors ${
                  provider === item
                    ? 'border-accent bg-accent/10 text-foreground'
                    : 'border-border bg-elevated/40 text-muted hover:border-accent/50'
                }`}
              >
                <span className="flex items-center gap-2 text-[11px] font-semibold">
                  {item === 'fireworks' ? <KeyRound className="h-3.5 w-3.5" /> : <Server className="h-3.5 w-3.5" />}
                  {PROVIDER_LABELS[item]}
                </span>
              </button>
            ))}
          </div>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <label className="space-y-1 text-[10px] font-mono text-muted">
              <span className="uppercase tracking-wider">Model ID</span>
              <input
                value={modelId}
                onChange={(event) => setModelId(event.target.value)}
                placeholder={provider === 'ollama' ? 'exact tag from ollama list' : 'exact served model ID'}
                className="w-full rounded border border-border bg-elevated px-2 py-1.5 text-[11px] text-foreground"
              />
            </label>
            <label className="space-y-1 text-[10px] font-mono text-muted">
              <span className="uppercase tracking-wider">Model family</span>
              <input
                value={modelFamily}
                onChange={(event) => setModelFamily(event.target.value)}
                className="w-full rounded border border-border bg-elevated px-2 py-1.5 text-[11px] text-foreground"
              />
            </label>
          </div>

          {provider === 'ollama' && (
            <p className="text-[10px] font-mono text-muted">
              Use the exact installed tag reported by <code>ollama list</code>. Kaaval verifies it against the runtime before connecting.
            </p>
          )}
          {provider === 'vllm' && (
            <p className="text-[10px] font-mono text-muted">
              Use the exact model ID exposed by the endpoint&apos;s <code>/v1/models</code> response.
            </p>
          )}

          {provider !== 'fireworks' && (
            <label className="block space-y-1 text-[10px] font-mono text-muted">
              <span className="uppercase tracking-wider">OpenAI-compatible base URL</span>
              <input
                value={baseUrl}
                onChange={(event) => setBaseUrl(event.target.value)}
                placeholder="https://runtime.example/v1"
                className="w-full rounded border border-border bg-elevated px-2 py-1.5 text-[11px] text-foreground"
              />
            </label>
          )}

          {needsKey && (
            <label className="block space-y-1 text-[10px] font-mono text-muted">
              <span className="uppercase tracking-wider">API key {provider === 'openai_compatible' && '(optional)'}</span>
              <input
                type="password"
                autoComplete="off"
                value={apiKey}
                onChange={(event) => setApiKey(event.target.value)}
                placeholder="Held in memory only; never written to artifacts"
                className="w-full rounded border border-border bg-elevated px-2 py-1.5 text-[11px] text-foreground"
              />
            </label>
          )}

          <label className="flex items-center gap-2 text-[10px] font-mono text-muted">
            <input
              type="checkbox"
              checked={structuredOutputs}
              onChange={(event) => setStructuredOutputs(event.target.checked)}
            />
            Request JSON-object structured output; Layer 1 still decides contract conformance
          </label>

          {capabilities.deployment_mode === 'hosted' && provider !== 'fireworks' && (
            <p className="rounded border border-warning/30 bg-warning/5 px-2 py-1.5 text-[10px] font-mono text-warning">
              Hosted mode requires a public HTTPS endpoint. A laptop-local model needs an authenticated reverse tunnel.
            </p>
          )}

          {error && (
            <p className="flex items-center gap-1.5 rounded border border-destructive/40 bg-destructive/10 px-2 py-1.5 text-[10px] font-mono text-destructive">
              <AlertTriangle className="h-3.5 w-3.5" /> {error}
            </p>
          )}

          <div className="flex items-center justify-end gap-2">
            <button onClick={onClose} className="rounded border border-border px-3 py-1.5 text-[11px] font-mono text-muted hover:text-foreground">
              Cancel
            </button>
            <button
              onClick={connect}
              disabled={pending || !canSubmit}
              className="flex items-center gap-1.5 rounded bg-accent px-3 py-1.5 text-[11px] font-mono font-semibold text-white disabled:opacity-50"
            >
              {pending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <PlugZap className="h-3.5 w-3.5" />}
              {pending ? 'Testing connection…' : 'Test and connect'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
