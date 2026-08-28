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

// ─── Market Intel ────────────────────────────────────────────────────────────
// Endpoints: GET /api/market-intel/shorts/{ticker}, /qmj/rank, /clusters/{ticker}.
// Fältnamn matchar apps/api/routers/market_intel.py (ShortPositionOut,
// QmjRankOut, InsiderClusterSignalOut).

export interface ShortInfo {
  scan_date: string;
  total_short_pct: number | null;      // summa rapporterade nettopositioner (%)
  is_new_discovery: boolean;           // första förekomst >0.5 % eller Δ≥+0.5 pp/90 d
  delta_pp: number | null;
}

export interface QmjRankItem {
  ticker: string;
  alpha_rank: number | null;           // komposit 0-100, NULL om hårt filter
  quality_z: number | null;            // 0-100 percentil inom storleksgrupp
  momentum_z: number | null;
  insider_z: number | null;
  value_z: number | null;
  payout_z: number | null;
  as_of_date: string | null;           // datum från vilket annual-data är giltig
  exclusion_reason: string | null;     // t.ex. "short_high(12.3%)" / "new_discovery"
  warning_flags: string[];             // t.ex. ["sell_cluster", "illiquid"]
}

export interface ClusterInfo {
  ticker: string;
  cluster_score: number | null;
  is_cluster: boolean;
  exec_buy_90d: boolean;
  unique_sellers_30d: number;          // unika säljare senaste 30 dagarna
  total_sell_amount_30d: number | null;
  updated_at: string | null;
}

export function marketIntelShorts(ticker: string): Promise<ShortInfo[]> {
  return api<ShortInfo[]>(`/api/market-intel/shorts/${encodeURIComponent(ticker)}`);
}

export function marketIntelQmjRank(): Promise<QmjRankItem[]> {
  return api<QmjRankItem[]>("/api/market-intel/qmj/rank");
}

export function marketIntelClusters(ticker: string): Promise<ClusterInfo> {
  return api<ClusterInfo>(`/api/market-intel/clusters/${encodeURIComponent(ticker)}`);
}

// ─── Kandidatradar ────────────────────────────────────────────────────────────
// Endpoint: GET /api/market-intel/radar?theme=<tema|tom>&sort=activity|rank&limit=40.
// Fältnamn matchar kontraktet i apps/api/routers/market_intel.py (RadarItemOut).

export type RadarBearing = "positive" | "negative" | "neutral" | "conditional" | null;

export interface RadarEvent {
  headline: string;
  bearing: RadarBearing;
  confidence: number | null;
  published_at: string | null;
  message_url: string | null;
}

export interface RadarItem {
  ticker: string;
  name: string | null;
  stratum: "established" | "growth_early" | "new_small" | "turnaround" | null;
  alpha_rank: number | null;
  quality_z: number | null;
  momentum_z: number | null;
  value_z: number | null;
  payout_z: number | null;
  insider_z: number | null;
  exclusion_reason: string | null;
  short_pct: number | null;
  new_disclosure: boolean;
  cluster_score: number | null;
  sellers_30d: number;
  news_48h: number;
  mention_surge: number | null;
  top_events: RadarEvent[];
  warnings: string[];
}

export interface RadarResponse {
  total: number;
  items: RadarItem[];
}

export function marketIntelRadar(
  theme?: string,
  sort: "activity" | "rank" = "activity",
  limit = 40,
): Promise<RadarResponse> {
  const params = new URLSearchParams({ sort, limit: String(limit) });
  if (theme) params.set("theme", theme);
  return api<RadarResponse>(`/api/market-intel/radar?${params.toString()}`);
}
