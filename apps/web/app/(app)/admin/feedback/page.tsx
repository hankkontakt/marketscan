"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ThumbsUp, ThumbsDown, Minus, Download } from "lucide-react";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

interface FeedbackItem {
  id: string;
  user_id: string;
  component: string;
  context: string | null;
  rating: number;
  comment: string | null;
  created_at: string;
}

interface FeedbackData {
  feedback: FeedbackItem[];
  count: number;
  stats: { positive: number; negative: number; neutral: number };
  by_component: Record<string, { total: number; positive: number; negative: number; neutral: number }>;
}

const COMPONENTS = ["verdict_card", "explain_text", "theme_card", ""];

export default function AdminFeedbackPage() {
  const [filter, setFilter] = useState("");
  const { data, isLoading } = useQuery<FeedbackData>({
    queryKey: ["admin-feedback", filter],
    queryFn: () => {
      const params = new URLSearchParams({ limit: "200" });
      if (filter) params.set("component", filter);
      return api(`/api/admin/feedback?${params}`);
    },
    refetchInterval: 30_000,
  });

  function exportJSON() {
    if (!data) return;
    const blob = new Blob([JSON.stringify(data.feedback, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `feedback-${new Date().toISOString().split("T")[0]}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }

  if (isLoading) return <div className="p-8 text-sm text-[var(--color-text-muted)]">Laddar...</div>;

  const s = data?.stats ?? { positive: 0, negative: 0, neutral: 0 };
  const total = s.positive + s.negative + s.neutral;

  return (
    <div className="max-w-5xl mx-auto p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold">Feedback</h1>
        <button onClick={exportJSON}
          className="flex items-center gap-1 text-xs px-3 py-1.5 rounded-lg border border-[var(--color-border)] hover:bg-[var(--color-bg-elevated)]">
          <Download size={14} /> Exportera JSON
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-3">
        <StatCard label="Totalt" value={total} />
        <StatCard label="Positiva" value={s.positive} color="text-[var(--color-up)]" />
        <StatCard label="Negativa" value={s.negative} color="text-[var(--color-down)]" />
        <StatCard label="Neutrala" value={s.neutral} color="text-[var(--color-text-muted)]" />
      </div>

      {/* Filter */}
      <div className="flex gap-1 flex-wrap">
        {COMPONENTS.map((c) => (
          <button key={c}
            onClick={() => setFilter(c)}
            className={cn(
              "text-xs px-3 py-1 rounded-full border transition-colors",
              filter === c
                ? "bg-[var(--color-accent)] text-white border-[var(--color-accent)]"
                : "border-[var(--color-border)] text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-elevated)]",
            )}>
            {c || "Alla"}
          </button>
        ))}
      </div>

      {/* Per-component breakdown */}
      {data?.by_component && Object.keys(data.by_component).length > 0 && (
        <table className="w-full text-xs">
          <thead>
            <tr className="text-left text-[var(--color-text-muted)] border-b border-[var(--color-border)]">
              <th className="py-1 font-medium">Komponent</th>
              <th className="py-1 font-medium text-right">Totalt</th>
              <th className="py-1 font-medium text-right">Positiva</th>
              <th className="py-1 font-medium text-right">Negativa</th>
            </tr>
          </thead>
          <tbody>
            {Object.entries(data.by_component).map(([name, stats]) => (
              <tr key={name} className="border-b border-[var(--color-border-subtle)]">
                <td className="py-1.5">{name}</td>
                <td className="py-1.5 text-right">{stats.total}</td>
                <td className="py-1.5 text-right text-[var(--color-up)]">{stats.positive}</td>
                <td className="py-1.5 text-right text-[var(--color-down)]">{stats.negative}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {/* Feedback list */}
      <div className="space-y-1">
        {data?.feedback.map((item) => (
          <div key={item.id} className="flex items-start gap-3 p-2 rounded-lg bg-[var(--color-bg-surface)] border border-[var(--color-border-subtle)]">
            <span className="mt-0.5">
              {item.rating === 1 ? <ThumbsUp size={14} className="text-[var(--color-up)]" /> :
               item.rating === -1 ? <ThumbsDown size={14} className="text-[var(--color-down)]" /> :
               <Minus size={14} className="text-[var(--color-text-muted)]" />}
            </span>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-xs font-medium">{item.component}</span>
                {item.context && <span className="text-[10px] text-[var(--color-text-muted)]">{item.context}</span>}
                <span className="text-[10px] text-[var(--color-text-muted)] ml-auto">
                  {new Date(item.created_at).toLocaleDateString("sv-SE")}
                </span>
              </div>
              {item.comment && (
                <p className="text-xs text-[var(--color-text-secondary)] mt-0.5 break-words">
                  {item.comment}
                </p>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function StatCard({ label, value, color }: { label: string; value: number; color?: string }) {
  return (
    <div className="p-3 rounded-xl bg-[var(--color-bg-surface)] border border-[var(--color-border-subtle)] text-center">
      <div className={cn("text-2xl font-semibold", color || "text-[var(--color-text-primary)]")}>{value}</div>
      <div className="text-[10px] text-[var(--color-text-muted)]">{label}</div>
    </div>
  );
}
