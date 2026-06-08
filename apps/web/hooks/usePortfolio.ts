"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { ScanRow } from "@/types/scan";
import type {
  Portfolio, Holding, PortfolioHistory, PortfolioRisk, Transaction, TWResponse,
  RiskMetrics, FactorExposure, CorrelationMatrix, OptimizeResult,
  RebalanceResult, RebalancingTarget,
} from "@/types/portfolio";
export type {
  Portfolio, Holding, PortfolioHistory, PeriodReturn, PortfolioRisk, Transaction, TWResponse,
  RiskMetrics, FactorExposure, CorrelationMatrix, OptimizeResult, RebalanceResult, RebalancingTarget,
} from "@/types/portfolio";

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


// ─── Transactions ──────────────────────────────────────────

export function useTransactions(ticker?: string) {
  const params = ticker ? `?ticker=${ticker}` : "";
  return useQuery<{ transactions: Transaction[]; total: number }>({
    queryKey: ["transactions", ticker],
    queryFn: () => api(`/api/transactions${params}`),
    staleTime: 30_000,
  });
}

export function useAddTransaction() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: {
      ticker: string; type: string; shares?: number;
      price?: number; amount?: number; note?: string;
    }) => api("/api/transactions", { method: "POST", body: JSON.stringify(body) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["transactions"] }),
  });
}

export function useDeleteTransaction() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api(`/api/transactions/${id}`, { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["transactions"] }),
  });
}

export function useTWR() {
  return useQuery<TWResponse>({
    queryKey: ["portfolio-twr"],
    queryFn: () => api<TWResponse>("/api/transactions/twr"),
    staleTime: 60_000,
    retry: 1,
  });
}

// ─── Risk Analytics (Mega-project 1) ──────────────────────────────────────────

export function useRiskAnalytics() {
  return useQuery<RiskMetrics>({
    queryKey: ["portfolio-risk-analytics"],
    queryFn: () => api<RiskMetrics>("/api/portfolio/analytics"),
    staleTime: 10 * 60_000,
    retry: 1,
  });
}

export function useFactorExposure() {
  return useQuery<FactorExposure>({
    queryKey: ["portfolio-factor-exposure"],
    queryFn: () => api<FactorExposure>("/api/portfolio/analytics/factor"),
    staleTime: 10 * 60_000,
    retry: 1,
  });
}

export function useCorrelationMatrix() {
  return useQuery<CorrelationMatrix>({
    queryKey: ["portfolio-correlation"],
    queryFn: () => api<CorrelationMatrix>("/api/portfolio/analytics/correlation"),
    staleTime: 10 * 60_000,
    retry: 1,
  });
}

export function useOptimizedWeights() {
  return useQuery<OptimizeResult[]>({
    queryKey: ["portfolio-optimize"],
    queryFn: () => api<OptimizeResult[]>("/api/portfolio/optimize"),
    staleTime: 10 * 60_000,
    retry: 1,
  });
}

export function useRebalanceSuggestions(targetName?: string) {
  const params = targetName ? `?target_name=${encodeURIComponent(targetName)}` : "";
  return useQuery<RebalanceResult>({
    queryKey: ["portfolio-rebalance", targetName],
    queryFn: () => api<RebalanceResult>(`/api/portfolio/rebalance${params}`),
    staleTime: 5 * 60_000,
    retry: 1,
  });
}

export function useRebalancingTargets() {
  return useQuery<RebalancingTarget[]>({
    queryKey: ["rebalancing-targets"],
    queryFn: () => api<RebalancingTarget[]>("/api/portfolio/rebalance/targets"),
    staleTime: 5 * 60_000,
  });
}

export function useSaveRebalancingTarget() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { name: string; targets: object[]; method: string }) =>
      api("/api/portfolio/rebalance/targets", { method: "POST", body: JSON.stringify(body) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["rebalancing-targets"] }),
  });
}

// ─── Fund Holdings ─────────────────────────────────────────────────────────────

export interface FundHolding {
  id: string;
  isin: string;
  name: string;
  shares: number;
  cost_basis: number | null;
  current_price: number | null;
  marknadsvarde: number | null;
  purchase_date: string | null;
  added_at: string | null;
  return_pct: number | null;
  current_value: number | null;
  cost_value: number | null;
}

export function useFundHoldings() {
  return useQuery<FundHolding[]>({
    queryKey: ["fund-holdings"],
    queryFn: () => api<FundHolding[]>("/api/portfolio/funds"),
    staleTime: 2 * 60_000,
    retry: 1,
  });
}

export function useRemoveFundHolding() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      api(`/api/portfolio/funds/${id}`, { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["fund-holdings"] }),
  });
}
