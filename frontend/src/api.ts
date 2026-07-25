const API_BASE = '/api';

async function apiFetch<T>(path: string, body?: unknown): Promise<T> {
  const opts: RequestInit = body
    ? {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      }
    : { method: 'GET' };
  const res = await fetch(`${API_BASE}${path}`, opts);
  if (!res.ok) {
    // Surface the FastAPI `detail` message when present, so the UI shows the
    // real reason (e.g. "Select at least one material…") instead of a bare code.
    let message = `Request failed (${res.status})`;
    try {
      const data = await res.json();
      if (typeof data?.detail === 'string') message = data.detail;
      else if (data?.detail) message = JSON.stringify(data.detail);
    } catch {
      /* non-JSON error body — keep the status message */
    }
    throw new Error(message);
  }
  return res.json() as Promise<T>;
}

export const api = {
  getMaterials: () => apiFetch<unknown>('/materials'),
  getSections: () => apiFetch<unknown>('/sections'),
  getLoadCases: () => apiFetch<unknown>('/load-cases'),
  beamEvaluate: (body: unknown) => apiFetch<unknown>('/beam/evaluate', body),
  beamRecommend: (body: unknown) => apiFetch<unknown>('/beam/recommend', body),
  beamRank: (body: unknown) => apiFetch<unknown>('/beam/rank', body),
  beamPareto: (body: unknown) => apiFetch<unknown>('/beam/pareto', body),
  beamDesignReview: (body: unknown) => apiFetch<unknown>('/beam/design-review', body),
  beamMonteCarlo: (body: unknown) => apiFetch<unknown>('/beam/monte-carlo', body),
  beamEnvelope: (body: unknown) => apiFetch<unknown>('/beam/envelope', body),
  bracketEvaluate: (body: unknown) => apiFetch<unknown>('/bracket/evaluate', body),
  bracketCompareGussets: (body: unknown) => apiFetch<unknown>('/bracket/compare-gussets', body),
  stockNearestBuyable: (body: unknown) => apiFetch<unknown>('/stock/nearest-buyable', body),
  exportReport: (body: unknown) => apiFetch<unknown>('/export', body),
};
