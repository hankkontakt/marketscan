"use client";

import { useQuery } from "@tanstack/react-query";
import {
  marketIntelShorts,
  marketIntelQmjRank,
  marketIntelClusters,
  marketIntelRadar,
  type ShortInfo,
  type QmjRankItem,
  type ClusterInfo,
  type RadarResponse,
} from "@/lib/api";

// ─── Market Intel ─────────────────────────────────────────────────────────────
// Data uppdateras nattligen → lång staleTime. retry: false — saknad data
// (404/empty) ska resultera i "inget badge", inte upprepade försök.

export function useMarketIntelShorts(ticker: string) {
  return useQuery<ShortInfo[]>({
    queryKey: ["market-intel-shorts", ticker],
    queryFn: () => marketIntelShorts(ticker),
    staleTime: 30 * 60_000,
    enabled: !!ticker,
    retry: false,
  });
}

export function useMarketIntelQmjRank() {
  return useQuery<QmjRankItem[]>({
    queryKey: ["market-intel-qmj-rank"],
    queryFn: () => marketIntelQmjRank(),
    staleTime: 30 * 60_000,
    retry: false,
  });
}

export function useMarketIntelClusters(ticker: string) {
  return useQuery<ClusterInfo>({
    queryKey: ["market-intel-clusters", ticker],
    queryFn: () => marketIntelClusters(ticker),
    staleTime: 30 * 60_000,
    enabled: !!ticker,
    retry: false,
  });
}

// ─── Kandidatradar ────────────────────────────────────────────────────────────
// Data uppdateras nattligen → lång staleTime. retry: false — saknad data ska
// resultera i tom lista, inte upprepade försök.

export function useMarketIntelRadar(
  theme?: string,
  sort: "activity" | "rank" = "activity",
  limit = 40,
) {
  return useQuery<RadarResponse>({
    queryKey: ["market-intel-radar", theme ?? "", sort, limit],
    queryFn: () => marketIntelRadar(theme, sort, limit),
    staleTime: 15 * 60_000,
    retry: false,
  });
}