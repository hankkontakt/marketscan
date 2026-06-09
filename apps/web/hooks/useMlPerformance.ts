/**
 * Hooks för AI/ML prestanda-dashboard (admin-only).
 * Alla endpoints kräver admin-JWT — anrop misslyckas med 403 för icke-admins.
 */

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

// ── Types ─────────────────────────────────────────────────────────────────────

export interface MlModelSummary {
  model_version: string;
  trained_at: string | null;
  n_rows: number | null;
  ic: number | null;
  hit_rate: number | null;
  decile_spread: number | null;
  n_folds: number | null;
  model_type: string | null;
  n_features: number | null;
  outcomes_total: number;
  outcomes_evaluated: number;
  live_ic: number | null;
  live_hit_rate: number | null;
}

export interface OutcomeRow {
  ticker: string;
  predicted_at: string;
  predicted_return: number | null;
  ml_rank: number | null;
  score_total: number | null;
  price_at: number | null;
  realized_return_30d: number | null;
  price_30d: number | null;
  evaluated_at: string | null;
  error: number | null;
}

export interface DecileRow {
  decile: number;
  avg_return: number;
  n_dates: number;
  label: string;
}

export interface IcPoint {
  month: string;
  ic: number;
  n: number;
}

export interface TopPickRow {
  ticker: string;
  predicted_at: string;
  ml_rank: number;
  predicted_return: number;
  realized_return_30d: number | null;
  outcome_status: "pending" | "win" | "loss" | "evaluated";
}

// ── Hooks ─────────────────────────────────────────────────────────────────────

export function useMlSummary() {
  return useQuery<MlModelSummary>({
    queryKey: ["ml-performance", "summary"],
    queryFn: () => api<MlModelSummary>("/api/ml-performance/summary"),
    staleTime: 5 * 60_000,   // 5 min — modell-metrics ändras inte ofta
    retry: false,
  });
}

export function useMlOutcomes(days = 90, evaluatedOnly = false) {
  return useQuery<OutcomeRow[]>({
    queryKey: ["ml-performance", "outcomes", days, evaluatedOnly],
    queryFn: () =>
      api<OutcomeRow[]>(
        `/api/ml-performance/outcomes?days=${days}&evaluated_only=${evaluatedOnly}`,
      ),
    staleTime: 10 * 60_000,
    retry: false,
  });
}

export function useMlDeciles(days = 90) {
  return useQuery<DecileRow[]>({
    queryKey: ["ml-performance", "deciles", days],
    queryFn: () =>
      api<DecileRow[]>(`/api/ml-performance/deciles?days=${days}`),
    staleTime: 10 * 60_000,
    retry: false,
  });
}

export function useMlIcTrend(months = 12) {
  return useQuery<IcPoint[]>({
    queryKey: ["ml-performance", "ic-trend", months],
    queryFn: () =>
      api<IcPoint[]>(`/api/ml-performance/ic-trend?months=${months}`),
    staleTime: 15 * 60_000,
    retry: false,
  });
}

export function useMlTopPicks(days = 30) {
  return useQuery<TopPickRow[]>({
    queryKey: ["ml-performance", "top-picks", days],
    queryFn: () =>
      api<TopPickRow[]>(`/api/ml-performance/top-picks?days=${days}`),
    staleTime: 5 * 60_000,
    retry: false,
  });
}
