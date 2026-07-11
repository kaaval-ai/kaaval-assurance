/* ── Typed API layer for the Flight Deck ──
   All backend access goes through here. No component parses raw `any`. */

import type { DashboardPayload, LiveRunRequest, LiveRunResponse } from './types';

export class ApiError extends Error {
  status: number;
  constructor(status: number, detail: string) {
    super(detail);
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, init);
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try {
      const body = await res.json();
      if (typeof body?.detail === 'string') detail = body.detail;
    } catch {
      /* keep status text */
    }
    throw new ApiError(res.status, detail);
  }
  return (await res.json()) as T;
}

export function fetchDashboard(): Promise<DashboardPayload> {
  return request<DashboardPayload>('/api/dashboard');
}

export function fetchHealth(): Promise<{
  status: string;
  live_runs_enabled: boolean;
  paid_remote_allowed: boolean;
  artifact_export_allowed: boolean;
}> {
  return request('/api/health');
}

export function startRun(body: LiveRunRequest): Promise<LiveRunResponse> {
  return request<LiveRunResponse>('/api/runs', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
}

export function resetSession(sessionId: string): Promise<{ status: string; session_id: string }> {
  return request<{ status: string; session_id: string }>(`/api/live-sessions/${sessionId}/reset`, {
    method: 'POST',
  });
}
