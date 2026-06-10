"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { ScanRow } from "@/types/scan";

interface MangdubblareResponse {
  ticker: string;
  name: string;
  sector: string | null;
  score_total: number | null;
  mews_score: number | null;
  mews_flag: boolean;
  mews_fcf_yield: number | null;
  mews_small_size: number | null;
  mews_low_ps: number | null;
  mews_operating_leverage: number | null;
  mews_revenue_accel: number | null;
  mews_clean_accruals: number | null;
  price: number | null;
  change_pct: number | null;
  market_cap: number | null;
  entry_signal: string | null;
}

export function useMangdubblare() {
  return useQuery<MangdubblareResponse[]>({
    queryKey: ["mangdubblare"],
    queryFn: () => api("/api/scan?mews_flag=true&limit=50"),
    staleTime: 60_000,
  });
}
