"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { ScanRow } from "@/types/scan";

export interface Holding {
  id: string;
  portfolio_id: string;
  ticker: string;
  shares: number;
  cost_basis: number | null;
  added_at: string;
  name: string | null;
  price: number | null;
  change_pct: number | null;
  score_total: number | null;
  entry_signal: string | null;
}

export interface Portfolio {
  id: string;
  user_id: string;
  name: string;
  created_at: string;
  holdings: Holding[];
}

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
