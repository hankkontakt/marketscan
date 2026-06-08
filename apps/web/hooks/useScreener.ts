"use client";

import { useQuery } from "@tanstack/react-query";
import { api, buildScanUrl, type ScanParams } from "@/lib/api";
import type { ScanRow } from "@/types/scan";

export function useScreener(params: ScanParams) {
  return useQuery<ScanRow[]>({
    queryKey: ["scan", params],
    queryFn: () => api<ScanRow[]>(buildScanUrl(params)),
    staleTime: 5 * 60_000,
    gcTime: 1 * 60_000,
  });
}

export function useScanMeta() {
  return useQuery({
    queryKey: ["scan-meta"],
    queryFn: () => api<{ scan_date: string; total: number; by_segment: Record<string, number> }>("/api/scan/meta"),
    staleTime: 10 * 60_000,
  });
}

export function useSectors() {
  return useQuery<string[]>({
    queryKey: ["sectors"],
    queryFn: () => api<string[]>("/api/scan/sectors"),
    staleTime: 30 * 60_000,
  });
}

export function useCountries() {
  return useQuery<string[]>({
    queryKey: ["countries"],
    queryFn: () => api<string[]>("/api/scan/countries"),
    staleTime: 30 * 60_000,
  });
}
