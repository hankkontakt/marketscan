"use client";

import Link from "next/link";
import { ArrowRight, Star } from "lucide-react";
import { useWatchlist } from "@/hooks/usePortfolio";
import { useScoreMovers } from "@/hooks/useAlerts";
import { cn } from "@/lib/utils";
import { scoreColorClass, formatScore, signalBadgeClass, signalShortLabel, changeClass, formatPctChange } from "@/lib/format";
import type { ScoreMover } from "@/types/alerts";

/**
 * WatchlistStrip — dina bevakade aktier, sorterade på kvalitet (Totalbetyg),
 * med "NY"-markering för de som rört sig i betyg senaste 7 dagarna.
 * (Watchlist-endpointen exponerar inte ml_rank ännu → sorterar på score_total.)
 */
export function WatchlistStrip() {
  const { data: watchlist = [], isLoading } = useWatchlist();
  const { data: moversUp = [] } = useScoreMovers(7, "up", 50);

  const movedTickers = new Set((moversUp as ScoreMover[]).map(m => m.ticker));

  const sorted = [...watchlist].sort(
    (a, b) => (b.score_total ?? -1) - (a.score_total ?? -1),
  );

  return (
    <div className="rounded-xl border bg-[var(--color-bg-surface)] border-[var(--color-border)] flex flex-col overflow-hidden">
      <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--color-border)]">
        <div className="flex items-center gap-2">
          <Star size={14} strokeWidth={1.5} className="text-[var(--color-warn)]" />
          <h2 className="text-sm font-semibold text-[var(--color-text-primary)]">Dina bevakningar</h2>
        </div>
        <Link href="/bevakningar" className="flex items-center gap-1 text-[11px] text-[var(--color-text-muted)] hover:text-[var(--color-accent)] transition-colors">
          Visa alla <ArrowRight size={10} strokeWidth={1.5} />
        </Link>
      </div>

      <div className="flex-1 px-1 py-1">
        {isLoading ? (
          <div className="space-y-1 p-2">
            {[1, 2, 3].map(i => <div key={i} className="h-9 rounded-lg skeleton" />)}
          </div>
        ) : sorted.length === 0 ? (
          <div className="py-8 text-center">
            <p className="text-xs text-[var(--color-text-muted)]">Inga bevakade aktier ännu.</p>
            <Link href="/screener" className="text-xs text-[var(--color-accent)] hover:underline mt-1 inline-block">
              Hitta aktier att bevaka →
            </Link>
          </div>
        ) : (
          sorted.slice(0, 8).map(w => (
            <Link
              key={w.ticker}
              href={`/aktie/${w.ticker}`}
              className="flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-[var(--color-bg-elevated)] transition-colors group"
            >
              <div className="min-w-0 flex-1 flex items-center gap-2">
                <span className="text-sm font-semibold text-[var(--color-text-primary)] group-hover:text-[var(--color-accent)] transition-colors">
                  {w.ticker}
                </span>
                {movedTickers.has(w.ticker) && (
                  <span className="text-[9px] font-bold px-1 py-0.5 rounded bg-[var(--color-up-soft)] text-[var(--color-up)]">NY</span>
                )}
                {w.name && (
                  <span className="text-xs text-[var(--color-text-muted)] truncate hidden sm:inline max-w-[110px]">{w.name}</span>
                )}
              </div>
              <div className="flex items-center gap-2 shrink-0">
                {w.change_pct != null && (
                  <span className={cn("text-xs font-mono tabular hidden sm:inline", changeClass(w.change_pct))}>
                    {formatPctChange(w.change_pct)}
                  </span>
                )}
                {w.score_total != null && (
                  <span className={cn("text-xs font-bold tabular font-mono", scoreColorClass(w.score_total))}>
                    {formatScore(w.score_total)}
                  </span>
                )}
                <span className={cn("text-[10px] font-medium px-1.5 py-0.5 rounded-md", signalBadgeClass(w.entry_signal))}>
                  {signalShortLabel(w.entry_signal)}
                </span>
              </div>
            </Link>
          ))
        )}
      </div>
    </div>
  );
}
