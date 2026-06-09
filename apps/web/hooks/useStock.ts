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

// U-11: Include is_synthetic in response type so UI can show "Exempeldata" label
export function usePriceHistory(ticker: string, enabled = true) {
  return useQuery({
    queryKey: ["price-history", ticker],
    queryFn: () => api<{ ticker: string; candles: unknown[]; is_synthetic?: boolean }>(`/api/stocks/${ticker}/price-history`),
    staleTime: 30 * 60_000,
    enabled: !!ticker && enabled,
  });
}

export function useScoreHistory(ticker: string, enabled = true) {
  return useQuery({
    queryKey: ["score-history", ticker],
    queryFn: () => api<{ ticker: string; history: { date: string; score: number; signal: string }[]; is_synthetic?: boolean }>(
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

// ── Company profile ───────────────────────────────────────────────────────────

export interface CompanyProfile {
  ticker: string;
  description: string | null;
  employees: number | null;
  website: string | null;
  industry: string | null;
  country: string | null;
  beta: number | null;
  week_52_high: number | null;
  week_52_low: number | null;
  updated_at: string | null;
}

export function useCompanyProfile(ticker: string, enabled = true) {
  return useQuery<CompanyProfile>({
    queryKey: ["company-profile", ticker],
    queryFn: () => api<CompanyProfile>(`/api/stocks/${ticker}/profile`),
    staleTime: 60 * 60_000,   // 1 hour — updated weekly by pipeline
    enabled: !!ticker && enabled,
    retry: false,             // don't retry 404 — profile may not exist yet
  });
}

// ── Similar stocks ────────────────────────────────────────────────────────────

export interface SimilarStockItem {
  ticker: string;
  name: string | null;
  score_total: number | null;
  sector: string | null;
  similarity_pct: number;
  price: number | null;
  change_pct: number | null;
  entry_signal: string | null;
  ml_rank: number | null;
}

export interface SimilarStocksResponse {
  ticker: string;
  similar: SimilarStockItem[];
}

export function useSimilarStocks(ticker: string, enabled = true) {
  return useQuery<SimilarStocksResponse>({
    queryKey: ["similar-stocks", ticker],
    queryFn: () => api<SimilarStocksResponse>(`/api/stocks/${ticker}/similar`),
    staleTime: 30 * 60_000,  // 30 min — likheter ändras inte ofta
    enabled: !!ticker && enabled,
  });
}
