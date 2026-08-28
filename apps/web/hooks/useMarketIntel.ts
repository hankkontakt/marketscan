"use client";

import { useQuery } from "@tanstack/react-query";
import {
  marketIntelShorts,
  marketIntelQmjRank,
  marketIntelClusters,
  type ShortInfo,
  type QmjRankItem,
  type ClusterInfo,
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