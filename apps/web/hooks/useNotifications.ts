"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

export interface NotificationItem {
  id: string;
  type: string;
  title: string;
  body: string | null;
  link: string | null;
  read_at: string | null;
  created_at: string;
}

export function useNotifications() {
  return useQuery<NotificationItem[]>({
    queryKey: ["notifications"],
    queryFn: () => api<NotificationItem[]>("/api/notifications"),
    staleTime: 30_000,
    refetchInterval: 60_000,
  });
}

export function useUnreadCount() {
  return useQuery<{ count: number }>({
    queryKey: ["notifications-unread"],
    queryFn: () => api<{ count: number }>("/api/notifications/unread"),
    staleTime: 15_000,
    refetchInterval: 30_000,
  });
}

export function useMarkRead() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      api(`/api/notifications/${id}/read`, { method: "POST" }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["notifications"] });
      qc.invalidateQueries({ queryKey: ["notifications-unread"] });
    },
  });
}

export function useMarkAllRead() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () =>
      api("/api/notifications/read-all", { method: "POST" }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["notifications"] });
      qc.invalidateQueries({ queryKey: ["notifications-unread"] });
    },
  });
}
