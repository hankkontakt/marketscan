"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

export interface CompareMetric {
  label: string;
  values: Record<string, number | string | null>;
}

export interface CompareResponse {
  tickers: string[];
  metrics: CompareMetric[];
  /** Tickers fetched live from yfinance — not in the scored universe, factor scores will be null */
  external_tickers: string[];
}

export function useCompare(tickers: string[]) {
  return useQuery<CompareResponse>({
    queryKey: ["compare", tickers],
    queryFn: () =>
      api<CompareResponse>("/api/stocks/compare", {
        method: "POST",
        body: JSON.stringify({ tickers }),
      }),
    enabled: tickers.length >= 2,
    staleTime: 5 * 60_000,
  });
}

export interface SearchResult {
  ticker: string;
  name: string | null;
  sector: string | null;
  segment: string | null;
  score_total: number | null;
  entry_signal: string | null;
  price: number | null;
  change_pct: number | null;
  market_cap: number | null;
  in_universe: boolean;
}

export function useStockSearch(query: string, limit = 6) {
  return useQuery<SearchResult[]>({
    queryKey: ["stock-search", query, limit],
    queryFn: () =>
      api<SearchResult[]>(`/api/stocks/search?q=${encodeURIComponent(query)}&limit=${limit}`),
    enabled: query.trim().length >= 2,
    staleTime: 60_000,
  });
}

export interface AICompareResponse {
  ticker: string;
  recommendation: string;
  reasoning: string;
  strengths: Record<string, string>;
  weaknesses: Record<string, string>;
  summary: string;
  cached_date: string;
}

export function useAICompare(tickers: string[], stockDatas: any[]) {
  return useQuery<AICompareResponse>({
    queryKey: ["ai-compare", tickers],
    queryFn: () =>
      api<AICompareResponse>("/api/ai/compare", {
        method: "POST",
        body: JSON.stringify({ tickers, stock_datas: stockDatas }),
      }),
    enabled: tickers.length >= 2 && stockDatas.length >= 2,
    staleTime: 8 * 60 * 60_000,
  });
}

export function useStockDetail(ticker: string) {
  return useQuery<any>({
    queryKey: ["stock-detail", ticker],
    queryFn: () => api<any>(`/api/stocks/${ticker}`),
    enabled: !!ticker,
    staleTime: 5 * 60_000,
  });
}
