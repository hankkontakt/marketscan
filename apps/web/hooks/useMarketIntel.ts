"use client";

import { useQuery } from "@tanstack/react-query";
import {
  marketIntelShorts,
  marketIntelQmjRank,
  marketIntelClusters,
  marketIntelRadar,
  marketIntelMasterRank,
  marketIntelMasterTicker,
  type ShortInfo,
  type QmjRankItem,
  type ClusterInfo,
  type RadarResponse,
  type MasterRankItem,
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

// ─── MasterRank (ROND 8) ──────────────────────────────────────────────────────
// Auktoritativ ranking. Data uppdateras fredags (master_rank.yml) → lång staleTime.

export function useMarketIntelMasterRank(limit = 50) {
  return useQuery<MasterRankItem[]>({
    queryKey: ["market-intel-master-rank", limit],
    queryFn: () => marketIntelMasterRank(limit),
    staleTime: 60 * 60_000,
    retry: false,
  });
}

export function useMarketIntelMasterTicker(ticker: string) {
  return useQuery<MasterRankItem>({
    queryKey: ["market-intel-master-ticker", ticker],
    queryFn: () => marketIntelMasterTicker(ticker),
    staleTime: 60 * 60_000,
    enabled: !!ticker,
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