"use client";

import { useState, useRef, useEffect } from "react";
import Link from "next/link";
import { Bell, CheckCheck, Clock, TrendingUp, AlertTriangle, Calendar, Newspaper } from "lucide-react";
import { useNotifications, useUnreadCount, useMarkRead, useMarkAllRead } from "@/hooks/useNotifications";
import { cn } from "@/lib/utils";

const TYPE_ICONS: Record<string, typeof Bell> = {
  price_alert: TrendingUp,
  earnings: Calendar,
  score_change: TrendingUp,
  system: AlertTriangle,
  insider: Newspaper,
};

export function NotificationBell() {
  const { data: unread } = useUnreadCount();
  const [panelOpen, setPanelOpen] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);

  const count = unread?.count ?? 0;

  // Close on outside click
  useEffect(() => {
    function handler(e: MouseEvent) {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        setPanelOpen(false);
      }
    }
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  return (
    <div className="relative" ref={panelRef}>
      <button
        onClick={() => setPanelOpen(!panelOpen)}
        className="relative flex items-center justify-center w-8 h-8 rounded-lg transition-colors
                   text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]
                   hover:bg-[var(--color-bg-elevated)]"
        aria-label="Notiser"
      >
        <Bell size={16} strokeWidth={1.5} />
        {count > 0 && (
          <span className="absolute -top-0.5 -right-0.5 w-3.5 h-3.5 rounded-full
                           bg-[var(--color-accent)] text-white text-[8px] font-bold
                           flex items-center justify-center">
            {count > 9 ? "9+" : count}
          </span>
        )}
      </button>

      {panelOpen && (
        <div className="absolute right-0 top-10 w-80 rounded-xl border shadow-xl z-50 overflow-hidden
                        bg-[var(--color-bg-surface)] border-[var(--color-border-strong)]">
          <NotificationPanel onClose={() => setPanelOpen(false)} />
        </div>
      )}
    </div>
  );
}

function NotificationPanel({ onClose }: { onClose: () => void }) {
  const { data: notifications = [] } = useNotifications();
  const markRead = useMarkRead();
  const markAllRead = useMarkAllRead();

  const unread = notifications.filter((n) => !n.read_at);

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--color-border)]">
        <span className="text-xs font-semibold text-[var(--color-text-primary)]">
          Notiser
        </span>
        {unread.length > 0 && (
          <button
            onClick={() => markAllRead.mutate()}
            className="flex items-center gap-1 text-[11px] text-[var(--color-accent)]
                       hover:underline transition-colors"
          >
            <CheckCheck size={12} strokeWidth={1.5} />
            Markera alla som lästa
          </button>
        )}
      </div>

      {/* List */}
      <div className="max-h-80 overflow-y-auto">
        {notifications.length === 0 ? (
          <div className="py-8 text-center">
            <Bell size={20} strokeWidth={1.5} className="text-[var(--color-border-strong)] mx-auto mb-2" />
            <p className="text-xs text-[var(--color-text-muted)]">Inga notiser ännu</p>
          </div>
        ) : (
          notifications.slice(0, 20).map((n) => {
            const Icon = TYPE_ICONS[n.type] ?? Bell;
            const isUnread = !n.read_at;
            return (
              <div
                key={n.id}
                className={cn(
                  "px-4 py-3 border-b last:border-b-0 border-[var(--color-border)] transition-colors",
                  isUnread ? "bg-[var(--color-accent-soft)]/30" : "",
                )}
              >
                <div className="flex items-start gap-3">
                  <Icon size={13} strokeWidth={1.5}
                        className={cn("mt-0.5 shrink-0", isUnread ? "text-[var(--color-accent)]" : "text-[var(--color-text-muted)]")} />
                  <div className="flex-1 min-w-0">
                    {n.link ? (
                      <Link
                        href={n.link}
                        onClick={() => {
                          if (isUnread) markRead.mutate(n.id);
                          onClose();
                        }}
                        className="text-xs font-medium text-[var(--color-text-primary)] hover:text-[var(--color-accent)] transition-colors"
                      >
                        {n.title}
                      </Link>
                    ) : (
                      <span className="text-xs font-medium text-[var(--color-text-primary)]">{n.title}</span>
                    )}
                    {n.body && (
                      <p className="text-[11px] text-[var(--color-text-muted)] mt-0.5 leading-relaxed">{n.body}</p>
                    )}
                    <div className="flex items-center gap-1 mt-1">
                      <Clock size={9} strokeWidth={1.5} className="text-[var(--color-text-muted)]" />
                      <span className="text-[10px] text-[var(--color-text-muted)]">
                        {timeAgo(n.created_at)}
                      </span>
                    </div>
                  </div>
                  {isUnread && (
                    <button
                      onClick={() => markRead.mutate(n.id)}
                      className="shrink-0 text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]"
                      aria-label="Markera som läst"
                    >
                      <CheckCheck size={12} strokeWidth={1.5} />
                    </button>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}

function timeAgo(dateStr: string): string {
  const now = Date.now();
  const d = new Date(dateStr).getTime();
  const diff = now - d;
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "precis nu";
  if (mins < 60) return `${mins}m sedan`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h sedan`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days}d sedan`;
  return new Date(dateStr).toLocaleDateString("sv-SE");
}
