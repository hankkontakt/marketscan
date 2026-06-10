"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

export interface EarningsMemo {
  ticker: string;
  published_date: string | null;
  created_at: string | null;
  memo: {
    nyckeltal_kommentar?: string;
    ledningston?: "positiv" | "neutral" | "defensiv";
    tre_citat?: string[];
    implicit_guidning?: string;
    sektor_jamforelse?: string;
    sammanfattning?: string;
    _grounding_warning?: boolean;
  };
}

export function useEarningsMemo(ticker: string) {
  return useQuery<EarningsMemo | null>({
    queryKey: ["earnings-memo", ticker],
    // 404 = inget memo → returnera null istället för att kasta
    queryFn: () => api<EarningsMemo>(`/api/stocks/${ticker}/earnings-memo`).catch(() => null),
    staleTime: 60 * 60_000,
    enabled: !!ticker,
    retry: false,
  });
}
