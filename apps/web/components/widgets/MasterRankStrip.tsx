"use client";

import Link from "next/link";
import { ArrowRight, Trophy } from "lucide-react";
import { useMarketIntelMasterRank } from "@/hooks/useMarketIntel";
import { scoreColorClass } from "@/lib/format";

/**
 * MasterRankStrip — topp-5 MasterRank-kandidater med block-nedbrytning.
 * Döljs helt om inga rankade aktier finns.
 */
export function MasterRankStrip() {
  const { data = [], isLoading } = useMarketIntelMasterRank(50);

  const top = data
    .filter(s => s.master_rank != null)
    .sort((a, b) => (b.master_rank ?? 0) - (a.master_rank ?? 0))
    .slice(0, 5);

  if (!isLoading && top.length === 0) return null;

  return (
    <div className="rounded-xl border bg-[var(--color-bg-surface)] border-[var(--color-border)] overflow-hidden">
      <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--color-border)]">
        <div className="flex items-center gap-2">
          <Trophy size={14} strokeWidth={1.5} className="text-[var(--color-accent)]" />
          <h2 className="text-sm font-semibold text-[var(--color-text-primary)]">Topplistor — MasterRank</h2>
        </div>
        <Link href="/topplistor" className="flex items-center gap-1 text-[11px] text-[var(--color-text-muted)] hover:text-[var(--color-accent)] transition-colors">
          Visa alla <ArrowRight size={10} strokeWidth={1.5} />
        </Link>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3 p-3">
        {isLoading
          ? [1, 2, 3, 4, 5].map(i => <div key={i} className="h-28 rounded-lg skeleton" />)
          : top.map(s => {
              const upside = s.analyst_upside;
              return (
                <Link
                  key={s.ticker}
                  href={`/aktie/${s.ticker}`}
                  className="rounded-lg border border-[var(--color-border)] p-3 hover:border-[var(--color-border-strong)] transition-colors"
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-semibold text-[var(--color-text-primary)]">{s.ticker}</span>
                    <span className={`text-sm font-bold font-mono tabular ${scoreColorClass(s.master_rank)}`}>
                      {s.master_rank != null ? s.master_rank.toFixed(0) : "—"}
                    </span>
                  </div>

                  <div className="space-y-1 text-[10px] text-[var(--color-text-muted)]">
                    <div className="flex justify-between">
                      <span>Tier</span>
                      <span className="font-medium text-[var(--color-text-primary)]">{s.tier ?? "—"}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Uppsida</span>
                      <span className={`font-medium ${upside != null && upside > 0 ? "text-[var(--color-up)]" : ""}`}>
                        {upside != null ? `${upside > 0 ? "+" : ""}${upside.toFixed(0)}%` : "—"}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span>RSI</span>
                      <span className="font-medium text-[var(--color-text-primary)]">
                        {s.rsi_14 != null ? s.rsi_14.toFixed(0) : "—"}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span>Katalysator</span>
                      <span className="font-medium text-[var(--color-text-primary)]">
                        {s.catalyst_days != null ? `om ${s.catalyst_days} d` : "—"}
                      </span>
                    </div>
                  </div>
                </Link>
              );
            })}
      </div>
    </div>
  );
}
