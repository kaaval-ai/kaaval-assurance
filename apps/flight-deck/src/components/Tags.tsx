/* Shared truth-labeling atoms: source tags, data labels, formatters. */

import type { DataLabel, SourceTag } from '../types';

export const TAG_STYLES: Record<SourceTag, string> = {
  measured: 'text-success border-success/40 bg-success/5',
  configured: 'text-accent border-accent/40 bg-accent/5',
  planned: 'text-warning border-warning/40 bg-warning/5',
  not_available: 'text-muted border-border bg-elevated/40',
};

export function SourceChip({ tag }: { tag: SourceTag }) {
  return (
    <span
      className={`inline-block px-1.5 py-0.5 rounded border text-[9px] font-mono leading-none uppercase tracking-wider ${TAG_STYLES[tag]}`}
    >
      {tag}
    </span>
  );
}

export const LABEL_STYLES: Record<DataLabel | 'LIVE RUN', string> = {
  'SAMPLE': 'text-warning border-warning/50 bg-warning/10',
  'CAPTURED LOCAL RUN': 'text-accent border-accent/50 bg-accent/10',
  'CAPTURED FIREWORKS RUN': 'text-accent border-accent/50 bg-accent/10',
  'MEASURED AMD RUN': 'text-success border-success/50 bg-success/10',
  'UNAVAILABLE': 'text-destructive border-destructive/50 bg-destructive/10',
  'LIVE RUN': 'text-success border-success/50 bg-success/10',
};

export function DataLabelBadge({ label }: { label: DataLabel | 'LIVE RUN' }) {
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded border text-[10px] font-mono font-bold uppercase tracking-widest ${LABEL_STYLES[label]}`}
    >
      {label}
    </span>
  );
}

export function NotAvailable({ note }: { note?: string }) {
  return (
    <span className="text-muted text-[10px] font-mono italic">
      {note || 'not available'}
    </span>
  );
}

export const pct = (v: number | null | undefined): string =>
  v === null || v === undefined ? 'n/a' : `${(v * 100).toFixed(1)}%`;

export const usd = (v: number | null | undefined): string =>
  v === null || v === undefined ? 'n/a' : `$${v.toFixed(4)}`;

export const ms = (v: number | null | undefined): string =>
  v === null || v === undefined ? 'n/a' : v >= 1000 ? `${(v / 1000).toFixed(1)}s` : `${v.toFixed(0)}ms`;
