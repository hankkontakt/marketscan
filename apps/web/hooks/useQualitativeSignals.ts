"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

export interface QualitativeSignals {
  ticker: string;
  qualitative_score: number | null;
  outlook_direction: string | null;
  hedging_density: number | null;
  capital_intent: string | null;
  tone_change: number | null;
  summary: string | null;
}

export function useQualitativeSignals(ticker: string) {
  return useQuery<QualitativeSignals>({
    queryKey: ["qualitative", ticker],
    queryFn: () => api(`/api/stocks/${ticker}/qualitative`),
    staleTime: 60_000,
    retry: false,
  });
}
