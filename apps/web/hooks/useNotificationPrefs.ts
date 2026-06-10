"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

export interface NotificationPrefs {
  on_new_stark: boolean;
  on_score_move: boolean;
  on_insider_cluster: boolean;
  on_mews_flag: boolean;
  on_earnings_memo: boolean;
  score_move_threshold: number;
  email_enabled: boolean;
}

export function useNotificationPrefs() {
  return useQuery<NotificationPrefs>({
    queryKey: ["notification-prefs"],
    queryFn: () => api<NotificationPrefs>("/api/notifications/prefs"),
    staleTime: 60_000,
  });
}

export function useSaveNotificationPrefs() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (prefs: NotificationPrefs) =>
      api<NotificationPrefs>("/api/notifications/prefs", {
        method: "PUT",
        body: JSON.stringify(prefs),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["notification-prefs"] }),
  });
}
