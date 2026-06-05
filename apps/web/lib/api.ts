/**
 * Typed fetch wrapper against FastAPI backend.
 * Credentials included for JWT cookie auth.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });

  if (!res.ok) {
    let message = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      message = body.detail ?? message;
    } catch {
      // ignore parse error
    }
    throw new ApiError(res.status, message);
  }

  return res.json() as Promise<T>;
}

// ─── Typed endpoint helpers ──────────────────────────────────────────────────

export type ScanParams = {
  segments?: string[];
  score_min?: number;
  score_max?: number;
  sector?: string;
  entry_signal?: string;
  trend_signal?: string;
  piotroski_min?: number;
  pe_max?: number;
  roe_min?: number;
  dividend_yield_min?: number;
  exclude_low_liquidity?: boolean;
  search?: string;
  limit?: number;
};

export function buildScanUrl(params: ScanParams): string {
  const q = new URLSearchParams();
  const p = params as Record<string, unknown>;
  for (const [key, val] of Object.entries(p)) {
    if (val === undefined || val === null) continue;
    if (Array.isArray(val)) {
      val.forEach((v) => q.append(key, String(v)));
    } else {
      q.set(key, String(val));
    }
  }
  return `/api/scan?${q.toString()}`;
}
