"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type {
  AlertRule, TriggeredAlert, ScoreHistoryPoint, ScoreMover, SignalTransition,
} from "@/types/alerts";

export type { AlertRule, TriggeredAlert, ScoreHistoryPoint, ScoreMover, SignalTransition } from "@/types/alerts";

// ─── Alert Rules ──────────────────────────────────────────────────────────────

export function useAlertRules() {
  return useQuery<AlertRule[]>({
    queryKey: ["alert-rules"],
    queryFn: () => api<AlertRule[]>("/api/alerts"),
    staleTime: 2 * 60_000,
  });
}

export function useCreateAlertRule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: Omit<AlertRule, "id" | "user_id" | "created_at" | "last_triggered" | "trigger_count">) =>
      api<AlertRule>("/api/alerts", { method: "POST", body: JSON.stringify(body) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["alert-rules"] }),
  });
}

export function useUpdateAlertRule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...body }: Partial<AlertRule> & { id: string }) =>
      api<AlertRule>(`/api/alerts/${id}`, { method: "PUT", body: JSON.stringify(body) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["alert-rules"] }),
  });
}

export function useDeleteAlertRule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api(`/api/alerts/${id}`, { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["alert-rules"] }),
  });
}

// ─── Triggered Alerts ─────────────────────────────────────────────────────────

export function useTriggeredAlerts(options?: { ruleType?: string; ticker?: string; limit?: number }) {
  const params = new URLSearchParams();
  if (options?.ruleType) params.set("rule_type", options.ruleType);
  if (options?.ticker)   params.set("ticker", options.ticker);
  if (options?.limit)    params.set("limit", String(options.limit));
  const qs = params.toString() ? `?${params.toString()}` : "";

  return useQuery<TriggeredAlert[]>({
    queryKey: ["triggered-alerts", options],
    queryFn: () => api<TriggeredAlert[]>(`/api/alerts/triggered${qs}`),
    staleTime: 2 * 60_000,
    retry: 1,
  });
}

// ─── Score History ─────────────────────────────────────────────────────────────

export function useScoreHistory(ticker: string, days = 90) {
  return useQuery<ScoreHistoryPoint[]>({
    queryKey: ["score-history", ticker, days],
    queryFn: () => api<ScoreHistoryPoint[]>(`/api/score-history/${ticker}?days=${days}`),
    staleTime: 30 * 60_000,
    enabled: !!ticker,
    retry: 1,
  });
}

export function useScoreMovers(
  days = 7,
  direction: "up" | "down" | "both" = "both",
  limit = 20,
) {
  return useQuery<ScoreMover[]>({
    queryKey: ["score-movers", days, direction, limit],
    queryFn: () =>
      api<ScoreMover[]>(
        `/api/score-history/movers?days=${days}&direction=${direction}&limit=${limit}`,
      ),
    staleTime: 10 * 60_000,
    retry: 1,
  });
}

export function useSignalTransitions(ticker: string, days = 90) {
  return useQuery<SignalTransition[]>({
    queryKey: ["signal-transitions", ticker, days],
    queryFn: () => api<SignalTransition[]>(`/api/signal-transitions/${ticker}?days=${days}`),
    staleTime: 30 * 60_000,
    enabled: !!ticker,
  });
}
