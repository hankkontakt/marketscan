"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { ScanRow } from "@/types/scan";

export function useStock(ticker: string) {
  return useQuery<ScanRow>({
    queryKey: ["stock", ticker],
    queryFn: () => api<ScanRow>(`/api/stocks/${ticker}`),
    staleTime: 5 * 60_000,
    enabled: !!ticker,
  });
}

export function usePriceHistory(ticker: string, enabled = true) {
  return useQuery({
    queryKey: ["price-history", ticker],
    queryFn: () => api<{ ticker: string; candles: unknown[] }>(`/api/stocks/${ticker}/price-history`),
    staleTime: 30 * 60_000,
    enabled: !!ticker && enabled,
  });
}

export function useScoreHistory(ticker: string, enabled = true) {
  return useQuery({
    queryKey: ["score-history", ticker],
    queryFn: () => api<{ ticker: string; history: { date: string; score: number; signal: string }[] }>(
      `/api/stocks/${ticker}/score-history`,
    ),
    staleTime: 30 * 60_000,
    enabled: !!ticker && enabled,
  });
}
