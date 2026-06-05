"use client";

import Link from "next/link";
import { Star, Bell, TrendingUp, TrendingDown, Minus, X } from "lucide-react";
import { useWatchlist } from "@/hooks/usePortfolio";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import {
  formatPrice, formatPctChange, formatScore, signalLabel, signalClass,
  scoreColorClass, changeClass,
} from "@/lib/format";
import { cn } from "@/lib/utils";

export function BevakninarView() {
  const { data: watchlist = [], isLoading } = useWatchlist();
  const qc = useQueryClient();

  const remove = useMutation({
    mutationFn: (ticker: string) => api(`/api/watchlist/${ticker}`, { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["watchlist"] }),
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-[var(--color-text-primary)]">Bevakningar</h1>
          <p className="text-xs mt-0.5 text-[var(--color-text-muted)]">
            {watchlist.length} aktier bevakade
          </p>
        </div>
      </div>

      {isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="skeleton h-16 rounded-xl" />
          ))}
        </div>
      ) : watchlist.length === 0 ? (
        <div className="rounded-xl p-12 text-center border"
             style={{ background: "var(--color-bg-surface)", borderColor: "var(--color-border)" }}>
          <Star size={32} strokeWidth={1} style={{ color: "var(--color-text-muted)", margin: "0 auto 12px" }} />
          <p className="text-sm text-[var(--color-text-secondary)]">Inga bevakningar än</p>
          <p className="text-xs mt-1 text-[var(--color-text-muted)]">
            Klicka Bevaka på ett aktiekort för att lägga till
          </p>
        </div>
      ) : (
        <div className="rounded-xl overflow-hidden border"
             style={{ borderColor: "var(--color-border)" }}>
          {watchlist.map((item, i) => (
            <div
              key={item.ticker}
              className="flex items-center gap-4 px-5 py-3 border-b transition-colors hover:bg-[var(--color-bg-elevated)]"
              style={{
                background: i % 2 === 0 ? "var(--color-bg-base)" : "var(--color-bg-surface)",
                borderColor: "var(--color-border)",
              }}
            >
              <Link href={`/aktie/${item.ticker}`} className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-xs font-semibold text-[var(--color-text-primary)]">
                    {item.ticker}
                  </span>
                  <span className="text-[11px] text-[var(--color-text-muted)] truncate">
                    {item.name}
                  </span>
                </div>
              </Link>

              <span className={cn("font-mono text-xs font-bold tabular", scoreColorClass(item.score_total))}>
                {item.score_total != null ? formatScore(item.score_total) : "—"}
              </span>

              {item.entry_signal && (
                <span className={cn("px-2 py-0.5 rounded text-[11px] font-medium hidden sm:inline", signalClass(item.entry_signal))}>
                  {signalLabel(item.entry_signal)}
                </span>
              )}

              <span className="font-mono tabular text-xs text-[var(--color-text-primary)]">
                {formatPrice(item.price)}
              </span>

              <span className={cn("font-mono tabular text-xs", changeClass(item.change_pct))}>
                {formatPctChange(item.change_pct)}
              </span>

              <button
                onClick={() => remove.mutate(item.ticker)}
                className="ml-2 text-[var(--color-text-muted)] hover:text-[var(--color-down)] transition-colors"
                aria-label={`Ta bort ${item.ticker} från bevakningar`}
              >
                <X size={14} strokeWidth={1.5} />
              </button>
            </div>
          ))}
        </div>
      )}

      <p className="text-xs text-center text-[var(--color-text-muted)]">
        Prisriktkurslarm &middot; Aktiveras via aktiekort →{" "}
        <Link href="/screener" className="text-[var(--color-accent)] hover:underline">
          Gå till screener
        </Link>
      </p>
    </div>
  );
}
