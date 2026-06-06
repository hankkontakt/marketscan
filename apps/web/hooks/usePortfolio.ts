"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { ScanRow } from "@/types/scan";
import type { Portfolio, Holding, PortfolioHistory, PortfolioRisk } from "@/types/portfolio";
export type { Portfolio, Holding, PortfolioHistory, PeriodReturn, PortfolioRisk } from "@/types/portfolio";

export function usePortfolio() {
  return useQuery<Portfolio>({
    queryKey: ["portfolio"],
    queryFn: () => api<Portfolio>("/api/portfolio"),
    staleTime: 2 * 60_000,
  });
}

export function useAddHolding() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { ticker: string; shares: number; cost_basis?: number }) =>
      api("/api/portfolio/holdings", { method: "POST", body: JSON.stringify(body) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["portfolio"] }),
  });
}

export function useRemoveHolding() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api(`/api/portfolio/holdings/${id}`, { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["portfolio"] }),
  });
}

export function useWatchlist() {
  return useQuery({
    queryKey: ["watchlist"],
    queryFn: () => api<Holding[]>("/api/watchlist"),
    staleTime: 2 * 60_000,
  });
}

// ─── Portfolio history ────────────────────────────────────────────

export function usePortfolioHistory(periods = "1M,3M,6M,12M") {
  return useQuery<PortfolioHistory>({
    queryKey: ["portfolio-history", periods],
    queryFn: () => api<PortfolioHistory>(`/api/portfolio/history?periods=${encodeURIComponent(periods)}`),
    staleTime: 5 * 60_000,
    retry: 1,
  });
}


// ─── Portfolio risk ────────────────────────────────────────────

export function usePortfolioRisk() {
  return useQuery<PortfolioRisk>({
    queryKey: ["portfolio-risk"],
    queryFn: () => api<PortfolioRisk>("/api/portfolio/risk"),
    staleTime: 5 * 60_000,
    retry: 1,
  });
}
