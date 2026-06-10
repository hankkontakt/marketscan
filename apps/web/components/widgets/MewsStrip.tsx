"use client";

import Link from "next/link";
import { ArrowRight, Zap } from "lucide-react";
import { useMangdubblare } from "@/hooks/useMangdubblare";
import { scoreColorClass } from "@/lib/format";

const FACTORS: { key: keyof FactorRow; label: string }[] = [
  { key: "mews_fcf_yield", label: "FCF" },
  { key: "mews_small_size", label: "Storlek" },
  { key: "mews_low_ps", label: "P/S" },
  { key: "mews_operating_leverage", label: "Hävst." },
  { key: "mews_revenue_accel", label: "Accel." },
  { key: "mews_clean_accruals", label: "Accruals" },
];

type FactorRow = {
  mews_fcf_yield: number | null;
  mews_small_size: number | null;
  mews_low_ps: number | null;
  mews_operating_leverage: number | null;
  mews_revenue_accel: number | null;
  mews_clean_accruals: number | null;
};

/**
 * MewsStrip — topp mångdubblar-kandidater (MEWS-flaggade) med faktornedbrytning.
 * Döljs helt om inga kandidater finns.
 */
export function MewsStrip() {
  const { data = [], isLoading } = useMangdubblare();

  const top = [...data]
    .filter(s => s.mews_flag && s.mews_score != null)
    .sort((a, b) => (b.mews_score ?? 0) - (a.mews_score ?? 0))
    .slice(0, 5);

  if (!isLoading && top.length === 0) return null;

  return (
    <div className="rounded-xl border bg-[var(--color-bg-surface)] border-[var(--color-border)] overflow-hidden">
      <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--color-border)]">
        <div className="flex items-center gap-2">
          <Zap size={14} strokeWidth={1.5} className="text-[var(--color-up)]" />
          <h2 className="text-sm font-semibold text-[var(--color-text-primary)]">Mångdubblar-kandidater</h2>
        </div>
        <Link href="/mangdubblare" className="flex items-center gap-1 text-[11px] text-[var(--color-text-muted)] hover:text-[var(--color-accent)] transition-colors">
          Visa alla <ArrowRight size={10} strokeWidth={1.5} />
        </Link>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3 p-3">
        {isLoading
          ? [1, 2, 3, 4, 5].map(i => <div key={i} className="h-28 rounded-lg skeleton" />)
          : top.map(s => (
              <Link
                key={s.ticker}
                href={`/aktie/${s.ticker}`}
                className="rounded-lg border border-[var(--color-border)] p-3 hover:border-[var(--color-border-strong)] transition-colors"
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-semibold text-[var(--color-text-primary)]">{s.ticker}</span>
                  <span className={`text-sm font-bold font-mono tabular ${scoreColorClass(s.mews_score)}`}>
                    {s.mews_score != null ? s.mews_score.toFixed(0) : "—"}
                  </span>
                </div>
                <div className="space-y-1">
                  {FACTORS.map(f => {
                    const v = (s as unknown as FactorRow)[f.key];
                    const pct = v != null ? Math.max(0, Math.min(100, v)) : 0;
                    return (
                      <div key={f.key} className="flex items-center gap-1.5">
                        <span className="text-[9px] text-[var(--color-text-muted)] w-12 shrink-0">{f.label}</span>
                        <div className="flex-1 h-1 rounded-full overflow-hidden bg-[var(--color-bg-elevated)]">
                          <div className="h-full rounded-full" style={{
                            width: `${pct}%`,
                            background: pct >= 70 ? "var(--color-score-high)" : pct >= 50 ? "var(--color-score-mid)" : "var(--color-score-low)",
                          }} />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </Link>
            ))}
      </div>
    </div>
  );
}
