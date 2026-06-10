"use client";

import { TrendingUp, Zap, Info, ArrowUp, ArrowDown } from "lucide-react";
import { useMangdubblare } from "@/hooks/useMangdubblare";
import { cn } from "@/lib/utils";
import { formatPrice, formatPctChange, signalLabel, signalClass, formatMarketCap } from "@/lib/format";
import { useRouter } from "next/navigation";

const FACTOR_LABELS: Record<string, string> = {
  mews_fcf_yield: "FCF-yield",
  mews_small_size: "Litet bolag",
  mews_low_ps: "Lågt P/S",
  mews_operating_leverage: "Operativ hävstång",
  mews_revenue_accel: "Intäktsacceleration",
  mews_clean_accruals: "Rena accruals",
};

const FACTOR_DESCS: Record<string, string> = {
  mews_fcf_yield: "Kassaflöde ÷ börsvärde — starkaste prediktorn för 10x-avkastning",
  mews_small_size: "Mindre bolag har större potential att mångdubblas",
  mews_low_ps: "Lågt pris/sales ger större uppsida vid förbättring",
  mews_operating_leverage: "Rörelsevinst växer snabbare än intäkter — expanderande marginal",
  mews_revenue_accel: "Intäkterna accelererar jämfört med föregående period",
  mews_clean_accruals: "Vinsten är av hög kvalitet (låg Sloan-accrual)",
};

function FactorBar({ value, factor }: { value: number | null; factor: string }) {
  const pct = Math.min((value ?? 50) / 100 * 100, 100);
  const color = pct >= 70 ? "var(--color-up)" : pct >= 40 ? "var(--color-accent)" : "var(--color-text-muted)";
  const label = FACTOR_LABELS[factor] ?? factor;
  const desc = FACTOR_DESCS[factor] ?? "";

  return (
    <div className="space-y-0.5">
      <div className="flex items-center justify-between text-xs">
        <span className="text-[var(--color-text-secondary)]">{label}</span>
        <span className="tabular-nums text-[var(--color-text-muted)]" style={{ color }}>{value?.toFixed(0) ?? "―"}</span>
      </div>
      <div className="w-full h-1 rounded-full bg-[var(--color-bg-elevated)] overflow-hidden">
        <div className="h-full rounded-full transition-all" style={{ width: `${pct}%`, background: color }} />
      </div>
    </div>
  );
}

export function MangdubblareView() {
  const router = useRouter();
  const { data = [], isLoading } = useMangdubblare();

  if (isLoading) {
    return (
      <div className="p-6 space-y-4">
        <div className="h-8 w-48 rounded bg-[var(--color-bg-elevated)] animate-pulse" />
        {[1, 2, 3].map((i) => <div key={i} className="h-24 rounded-xl bg-[var(--color-bg-elevated)] animate-pulse" />)}
      </div>
    );
  }

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-[var(--color-accent-soft)] flex items-center justify-center">
            <Zap size={20} className="text-[var(--color-accent)]" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-[var(--color-text-primary)]">Mångdubblar-kandidater</h1>
            <p className="text-xs text-[var(--color-text-muted)]">
              MEWS (Multi-Bagger Early Warning Score) — {data.length} kandidater
            </p>
          </div>
        </div>
      </div>

      {data.length === 0 ? (
        <div className="text-center py-12 text-sm text-[var(--color-text-muted)]">
          <Zap size={32} className="mx-auto mb-3 opacity-30" />
          <p>Inga mångdubblar-kandidater just nu.</p>
          <p className="text-xs mt-1">MEWS identifierar småbolag med potential att mångdubblas enligt Yartseva (2025).</p>
        </div>
      ) : (
        <div className="space-y-3">
          {data.map((stock) => {
            const factorCols = [
              "mews_fcf_yield", "mews_small_size", "mews_low_ps",
              "mews_operating_leverage", "mews_revenue_accel", "mews_clean_accruals",
            ] as const;

            return (
              <div
                key={stock.ticker}
                onClick={() => router.push(`/aktie/${stock.ticker}`)}
                className="rounded-xl border border-[var(--color-border)] bg-[var(--color-bg-surface)] p-4
                           hover:border-[var(--color-accent)] transition-colors cursor-pointer space-y-3"
              >
                {/* Row 1: Ticker + name + score */}
                <div className="flex items-start justify-between gap-4">
                  <div className="flex items-center gap-2.5 min-w-0">
                    <span className="font-mono text-sm font-bold text-[var(--color-text-primary)]">{stock.ticker}</span>
                    <span className="text-sm text-[var(--color-text-secondary)] truncate">{stock.name}</span>
                    {stock.entry_signal && (
                      <span className={cn("px-2 py-0.5 rounded text-[10px] font-medium shrink-0", signalClass(stock.entry_signal))}>
                        {signalLabel(stock.entry_signal)}
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-4 shrink-0">
                    {stock.price != null && (
                      <span className="text-right">
                        <div className="font-mono text-sm font-medium">{formatPrice(stock.price)}</div>
                        {stock.change_pct != null && (
                          <div className={cn("font-mono text-[11px]", stock.change_pct >= 0 ? "text-[var(--color-up)]" : "text-[var(--color-down)]")}>
                            {stock.change_pct >= 0 ? <ArrowUp size={10} className="inline" /> : <ArrowDown size={10} className="inline" />}
                            {formatPctChange(stock.change_pct)}
                          </div>
                        )}
                      </span>
                    )}
                    <div className="text-right min-w-[48px]">
                      <div className="font-mono text-lg font-bold text-[var(--color-accent)]">{stock.mews_score?.toFixed(0) ?? "―"}</div>
                      <div className="text-[10px] text-[var(--color-text-muted)]">MEWS</div>
                    </div>
                  </div>
                </div>

                {/* Row 2: Factor bars */}
                <div className="grid grid-cols-2 md:grid-cols-3 gap-x-6 gap-y-2">
                  {factorCols.map((f) => (
                    <FactorBar key={f} factor={f} value={stock[f as keyof typeof stock] as number | null} />
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Evidensbox */}
      <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-bg-elevated)] p-4 text-xs text-[var(--color-text-muted)] leading-relaxed">
        <p className="font-medium text-[var(--color-text-secondary)] mb-1">Om MEWS</p>
        <p>
          Multi-Bagger Early Warning Score baseras på forskning av Yartseva (2025, BCU CAFÉ WP#33)
          som studerade 464 verkliga 10x-aktier 2009–2024. Starkaste prediktorerna var FCF-yield,
          litet bolag (~$348M), lågt P/S (~0.6), och operativ hävstång — vinsttillväxt vid köpet
          predikterade INTE, men operativ hävstång gjorde.
        </p>
      </div>
    </div>
  );
}
