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

export interface NewsItem {
  date: string;
  headline: string;
  summary: string;
  source: string;
  url: string | null;
  sentiment: string | null;
  ticker: string | null;
}

export function useStockNews(ticker: string, enabled = true) {
  return useQuery<{ ticker: string; news: NewsItem[] }>({
    queryKey: ["stock-news", ticker],
    queryFn: () => api(`/api/stocks/${ticker}/news`),
    staleTime: 10 * 60_000,
    enabled: !!ticker && enabled,
  });
}

export function useStockEarnings(ticker: string, enabled = true) {
  return useQuery<{ ticker: string; earnings: unknown[] }>({
    queryKey: ["stock-earnings", ticker],
    queryFn: () => api(`/api/stocks/${ticker}/earnings`),
    staleTime: 60 * 60_000,
    enabled: !!ticker && enabled,
  });
}

export interface PiotroskiCriterion {
  name: string;
  passed: boolean;
  explanation: string;
}

export interface PiotroskiDetail {
  ticker: string;
  total_score: number;
  criteria: PiotroskiCriterion[];
}

export function usePiotroski(ticker: string, enabled = true) {
  return useQuery<PiotroskiDetail>({
    queryKey: ["piotroski", ticker],
    queryFn: () => api(`/api/stocks/${ticker}/piotroski`),
    staleTime: 10 * 60_000,
    enabled: !!ticker && enabled,
  });
}
