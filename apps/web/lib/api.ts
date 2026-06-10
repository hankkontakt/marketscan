/**
 * Typed fetch wrapper against FastAPI backend.
 * Automatically attaches Supabase JWT when available.
 */

import { createClient } from "@/lib/supabase/client";

// The FastAPI backend is a SEPARATE Vercel project on its own domain
// (marketscan-api.vercel.app). We MUST always call it with an absolute URL.
//
// Why not fall back to "" (same-origin)?  The frontend's own deployment
// (web-…-hankkontakts-projects.vercel.app) has Vercel Deployment Protection,
// which redirects any request to an SSO challenge. A same-origin /api/* POST
// then gets redirected cross-origin → fetch() throws TypeError → "Nätverksfel".
// Calling the API host directly bypasses that entirely (CORS is configured for it).
//
// NOTE: `|| ` not `?? ` on purpose — Vercel can inject NEXT_PUBLIC_API_URL="" (an
// empty string), and `?? ""` would keep the empty string. `|| ` falls through to
// the absolute default for both unset AND empty values.
//
// For local dev, set NEXT_PUBLIC_API_URL=http://localhost:8000 in .env.local.
const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "https://marketscan-api.vercel.app";

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export async function api<T>(
  path: string,
  init?: RequestInit,
  timeoutMs = 55_000,
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(init?.headers as Record<string, string>),
  };

  // Attach JWT from Supabase session if available
  try {
    const supabase = createClient();
    const { data } = await supabase.auth.getSession();
    const token = data.session?.access_token;
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
  } catch {
    // supabase client may not be available (e.g. SSR)
  }

  // AbortController so we can time out fetch independently of the service
  // worker.  55 s is just under Vercel's 60 s maxDuration, giving the server
  // the full window while still showing a human-readable error instead of a
  // cryptic "Failed to fetch".
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers,
      signal: controller.signal,
    });
  } catch (err: unknown) {
    clearTimeout(timer);
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new ApiError(408, "Begäran tog för lång tid — försök igen");
    }
    // Generic network failure (service worker timeout, no connectivity, etc.)
    throw new ApiError(0, "Nätverksfel — kontrollera anslutningen och försök igen");
  } finally {
    clearTimeout(timer);
  }

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
  country?: string;
  entry_signal?: string;
  trend_signal?: string;
  piotroski_min?: number;
  pe_max?: number;
  roe_min?: number;
  dividend_yield_min?: number;
  exclude_low_liquidity?: boolean;
  mews_flag?: boolean;
  sort_by?: string;
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
