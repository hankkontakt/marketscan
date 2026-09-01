/**
 * V3 decision API client + runtime gate.
 * The backend contract lives in lib/types/decision_v3.ts (GENERATED from
 * OpenAPI by scripts/generate_v3_types.py — never edit by hand).
 *
 * The gate is a real runtime gate: when NEXT_PUBLIC_DECISIONS_V3 is not
 * "true", the V3 surfaces are not rendered at all and the V1 surfaces remain.
 * The backend flag (decision_v3_api) independently gates the routes.
 */

import { api } from "@/lib/api";
import type {
  ChangesProjectionV3,
  CompareProjectionV3,
  CurrentSnapshotV3,
  DecisionProjectionV3,
  ScreenerProjectionV3,
  TransitionEventV3,
} from "@/lib/types/decision_v3";

export const DECISIONS_V3_ENABLED =
  process.env.NEXT_PUBLIC_DECISIONS_V3 === "true";

export interface V3ScreenerParams {
  thesis_band?: string;
  setup_state?: string;
  risk_state?: string;
  data_grade?: string;
  segment?: string;
  limit?: number;
}

export function v3Screener(params: V3ScreenerParams = {}): Promise<ScreenerProjectionV3> {
  const q = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null) continue;
    q.set(key, String(value));
  }
  const suffix = q.toString() ? `?${q.toString()}` : "";
  return api<ScreenerProjectionV3>(`/api/v3/decisions/screener${suffix}`);
}

export function v3StockByTicker(ticker: string): Promise<DecisionProjectionV3> {
  return api<DecisionProjectionV3>(
    `/api/v3/decisions/stock/${encodeURIComponent(ticker)}`,
  );
}

export function v3CurrentSnapshot(): Promise<CurrentSnapshotV3> {
  return api<CurrentSnapshotV3>("/api/v3/decisions/system/current-snapshot");
}

export function v3Changes(limit = 50): Promise<ChangesProjectionV3> {
  return api<ChangesProjectionV3>(
    `/api/v3/decisions/changes?limit=${limit}`,
  );
}

export function v3Transitions(limit = 50): Promise<TransitionEventV3[]> {
  return api<TransitionEventV3[]>(
    `/api/v3/decisions/transitions?limit=${limit}`,
  );
}

export function v3Compare(tickers: string[]): Promise<CompareProjectionV3> {
  return api<CompareProjectionV3>("/api/v3/decisions/compare", {
    body: JSON.stringify({ tickers }),
    method: "POST",
  });
}