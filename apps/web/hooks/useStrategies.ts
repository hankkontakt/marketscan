"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type {
  Strategy, StrategyRun, BacktestResult, CompareResult,
  SignalAnalytics, SignalAnalyticsDetail,
} from "@/types/strategy";

export type {
  Strategy, StrategyRun, BacktestResult, CompareResult,
  SignalAnalytics, SignalAnalyticsDetail,
} from "@/types/strategy";

// ─── Strategies CRUD ─────────────────────────────────────────────────────────

export function useStrategies(includePublic = true) {
  return useQuery<Strategy[]>({
    queryKey: ["strategies", includePublic],
    queryFn: () =>
      api<Strategy[]>(`/api/strategies?include_public=${includePublic}`),
    staleTime: 2 * 60_000,
  });
}

export function useCreateStrategy() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: Omit<Strategy, "id" | "user_id" | "created_at" | "updated_at" | "_is_own" | "strategy_runs">) =>
      api<Strategy>("/api/strategies", { method: "POST", body: JSON.stringify(body) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["strategies"] }),
  });
}

export function useUpdateStrategy() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...body }: Partial<Strategy> & { id: string }) =>
      api<Strategy>(`/api/strategies/${id}`, { method: "PUT", body: JSON.stringify(body) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["strategies"] }),
  });
}

export function useDeleteStrategy() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api(`/api/strategies/${id}`, { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["strategies"] }),
  });
}

// ─── Backtest ─────────────────────────────────────────────────────────────────

export function useTriggerBacktest() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (strategyId: string) =>
      api<{ run_id: string; status: string }>(`/api/strategies/${strategyId}/run`, {
        method: "POST",
      }),
    onSuccess: (_data, strategyId) => {
      qc.invalidateQueries({ queryKey: ["backtest-results", strategyId] });
      qc.invalidateQueries({ queryKey: ["strategies"] });
    },
  });
}

export function useBacktestResults(strategyId: string, runId?: string) {
  const params = runId ? `?run_id=${runId}` : "";
  return useQuery<BacktestResult>({
    queryKey: ["backtest-results", strategyId, runId],
    queryFn: () =>
      api<BacktestResult>(`/api/strategies/${strategyId}/results${params}`),
    staleTime: 5 * 60_000,
    enabled: !!strategyId,
    retry: 1,
    refetchInterval: (query) => {
      // Poll every 5s while run is pending/running
      const run = (query.state.data as BacktestResult | undefined)?.run;
      return run && ["pending", "running"].includes(run.status) ? 5_000 : false;
    },
  });
}

export function useCompareStrategies(runIds: string[]) {
  return useQuery<CompareResult[]>({
    queryKey: ["strategies-compare", runIds],
    queryFn: () =>
      api<CompareResult[]>(`/api/strategies/compare?run_ids=${runIds.join(",")}`),
    staleTime: 5 * 60_000,
    enabled: runIds.length >= 2,
  });
}

// ─── Signal Analytics ─────────────────────────────────────────────────────────

export function useSignalAnalytics(field?: "entry_signal" | "trend_signal", minSamples = 5) {
  const params = new URLSearchParams({ min_samples: String(minSamples) });
  if (field) params.set("field", field);

  return useQuery<SignalAnalytics[]>({
    queryKey: ["signal-analytics", field, minSamples],
    queryFn: () => api<SignalAnalytics[]>(`/api/signal-analytics?${params.toString()}`),
    staleTime: 30 * 60_000,
    retry: 1,
  });
}

export function useSignalAnalyticsDetail(
  field: string,
  fromSignal: string,
  toSignal: string,
) {
  return useQuery<SignalAnalyticsDetail>({
    queryKey: ["signal-analytics-detail", field, fromSignal, toSignal],
    queryFn: () =>
      api<SignalAnalyticsDetail>(
        `/api/signal-analytics/${field}/${encodeURIComponent(fromSignal)}/${encodeURIComponent(toSignal)}`,
      ),
    staleTime: 30 * 60_000,
    enabled: !!field && !!fromSignal && !!toSignal,
  });
}
