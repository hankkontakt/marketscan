"use client";

import { useState } from "react";
import { Star, Briefcase, TrendingUp, TrendingDown, Minus } from "lucide-react";
import { cn } from "@/lib/utils";
import {
  formatPrice, formatPctChange, signalLabel, signalClass,
  scoreColorClass, formatScore, changeClass,
} from "@/lib/format";
import type { ScanRow } from "@/types/scan";

interface Props {
  stock: ScanRow;
}

export function VerdictHeader({ stock }: Props) {
  const [watching, setWatching] = useState(false);
  const [inPortfolio, setInPortfolio] = useState(stock.has_holding);

  const TrendIcon =
    stock.trend_signal === "Upptrend" ? TrendingUp :
    stock.trend_signal === "Nedtrend" ? TrendingDown :
    Minus;

  const trendColor =
    stock.trend_signal === "Upptrend" ? "var(--color-up)" :
    stock.trend_signal === "Nedtrend" ? "var(--color-down)" :
    "var(--color-text-muted)";

  return (
    <div
      className="sticky top-0 z-30 border-b px-6 py-4"
      style={{
        background: "var(--color-bg-surface)",
        borderColor: "var(--color-border)",
      }}
    >
      {/* Row 1: Name + price */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <div className="flex items-center gap-3">
            <span className="font-mono font-bold text-lg text-[var(--color-text-primary)]">
              {stock.ticker}
            </span>
            <span className="text-[var(--color-text-secondary)] text-sm">
              {stock.name}
            </span>
          </div>
          <div className="flex items-center gap-3 mt-1.5 flex-wrap">
            {/* Köpläge */}
            <span className={cn("px-2.5 py-1 rounded-md text-xs font-medium", signalClass(stock.entry_signal))}>
              {signalLabel(stock.entry_signal)}
            </span>

            {/* Totalbetyg */}
            <div className="flex items-center gap-1.5">
              <span className="text-xs text-[var(--color-text-muted)]">Totalbetyg</span>
              <span className={cn("font-mono font-bold text-base tabular", scoreColorClass(stock.score_total))}>
                {formatScore(stock.score_total)}
              </span>
            </div>

            {/* Trend */}
            <div className="flex items-center gap-1 text-xs" style={{ color: trendColor }}>
              <TrendIcon size={13} strokeWidth={1.5} />
              <span>{stock.trend_signal ?? "—"}</span>
            </div>

            {/* AI-prognos */}
            {stock.predicted_return != null && (
              <div className="flex items-center gap-1 text-xs">
                <span className="text-[var(--color-text-muted)]">AI-prognos 30d</span>
                <span className={cn("font-mono tabular", changeClass(stock.predicted_return))}>
                  {stock.predicted_return > 0 ? "+" : ""}{(stock.predicted_return * 100).toFixed(1)}%
                </span>
              </div>
            )}
          </div>
        </div>

        {/* Price */}
        <div className="flex flex-col items-end gap-1">
          <span className="font-mono tabular text-2xl font-bold text-[var(--color-text-primary)]">
            {formatPrice(stock.price)}
          </span>
          <span className={cn("font-mono tabular text-sm font-medium", changeClass(stock.change_pct))}>
            {formatPctChange(stock.change_pct)} idag
          </span>
        </div>
      </div>

      {/* Row 2: Actions */}
      <div className="flex items-center gap-2 mt-3">
        <button
          onClick={() => setWatching(!watching)}
          className={cn(
            "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors border",
            watching
              ? "border-[var(--color-warn)] text-[var(--color-warn)] bg-[var(--color-warn-soft)]"
              : "border-[var(--color-border)] text-[var(--color-text-secondary)] hover:border-[var(--color-border-strong)]",
          )}
          aria-label={watching ? "Ta bort bevakning" : "Lägg till bevakning"}
        >
          <Star size={13} strokeWidth={1.5} fill={watching ? "currentColor" : "none"} />
          {watching ? "Bevakad" : "Bevaka"}
        </button>

        <button
          onClick={() => setInPortfolio(!inPortfolio)}
          className={cn(
            "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors border",
            inPortfolio
              ? "border-[var(--color-up)] text-[var(--color-up)] bg-[var(--color-up-soft)]"
              : "border-[var(--color-border)] text-[var(--color-text-secondary)] hover:border-[var(--color-border-strong)]",
          )}
          aria-label={inPortfolio ? "Ta bort ur portfölj" : "Lägg i portfölj"}
        >
          <Briefcase size={13} strokeWidth={1.5} />
          {inPortfolio ? "I portfölj" : "Lägg i portfölj"}
        </button>

        <span className="ml-auto text-xs text-[var(--color-text-muted)]">
          Tillförlitlighet: {stock.confidence_label ?? "—"}
        </span>
      </div>
    </div>
  );
}
