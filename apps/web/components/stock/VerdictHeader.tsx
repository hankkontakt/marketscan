"use client";

import { useState } from "react";
import { Star, TrendingUp, TrendingDown, Minus, Plus, X, Check, Zap } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { cn } from "@/lib/utils";
import {
  formatPrice, formatPctChange, signalLabel, signalClass,
  scoreColorClass, formatScore, changeClass,
} from "@/lib/format";
import { InfoTooltip } from "@/components/ui/InfoTooltip";
import { api } from "@/lib/api";
import { toast } from "sonner";
import type { ScanRow } from "@/types/scan";

interface Props {
  stock: ScanRow;
}

export function VerdictHeader({ stock }: Props) {
  const qc = useQueryClient();
  const [showAddForm, setShowAddForm] = useState(false);
  const [shares, setShares] = useState("");
  const [costBasis, setCostBasis] = useState("");

  // Fallback: if scan_results.price is null (pipeline hasn't updated yet),
  // use the most recent candle close from price history
  const needsPriceFallback = stock.price == null;
  const { data: priceHistory } = useQuery<{ candles: { close: number; time: number }[] }>({
    queryKey: ["price-history", stock.ticker],
    queryFn: () => api(`/api/stocks/${stock.ticker}/price-history`),
    staleTime: 5 * 60_000,
    enabled: needsPriceFallback,
  });
  const fallbackPrice = needsPriceFallback && priceHistory?.candles?.length
    ? priceHistory.candles[priceHistory.candles.length - 1].close
    : null;
  const displayPrice = stock.price ?? fallbackPrice;

  const TrendIcon =
    stock.trend_signal === "Upptrend" ? TrendingUp :
    stock.trend_signal === "Nedtrend" ? TrendingDown :
    Minus;

  const trendColor =
    stock.trend_signal === "Upptrend" ? "var(--color-up)" :
    stock.trend_signal === "Nedtrend" ? "var(--color-down)" :
    "var(--color-text-muted)";

  // Check if already in watchlist
  const { data: watchlist = [] } = useQuery<{ ticker: string }[]>({
    queryKey: ["watchlist"],
    queryFn: () => api("/api/watchlist"),
    staleTime: 60_000,
  });
  const isWatching = watchlist.some((w) => w.ticker === stock.ticker);

  const addWatch = useMutation({
    mutationFn: () => api(`/api/watchlist/${stock.ticker}`, { method: "POST" }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["watchlist"] }); toast.success("Bevakning tillagd"); },
    onError: () => toast.error("Logga in för att bevaka aktier"),
  });

  const removeWatch = useMutation({
    mutationFn: () => api(`/api/watchlist/${stock.ticker}`, { method: "DELETE" }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["watchlist"] }); toast.success("Bevakning borttagen"); },
  });

  const addHolding = useMutation({
    mutationFn: () => api("/api/portfolio/holdings", {
      method: "POST",
      body: JSON.stringify({
        ticker: stock.ticker,
        shares: parseFloat(shares),
        cost_basis: costBasis ? parseFloat(costBasis) : null,
      }),
    }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["portfolio"] });
      toast.success(`${shares} aktier i ${stock.ticker} tillagda`);
      setShowAddForm(false);
      setShares("");
      setCostBasis("");
    },
    onError: () => toast.error("Logga in för att lägga till innehav"),
  });

  return (
    <div
      className="border-b px-6 py-4 bg-[var(--color-bg-surface)] border-[var(--color-border)]"
    >
      {/* Row 1: Name + price */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <div className="flex items-center gap-3">
            <span className="text-lg font-bold text-[var(--color-text-primary)]">
              {stock.name}
            </span>
            <span className="font-mono text-sm text-[var(--color-text-secondary)]">
              {stock.ticker}
            </span>
          </div>
          <div className="flex items-center gap-3 mt-1.5 flex-wrap">
            {/* Köpläge */}
            <span className={cn("px-2.5 py-1 rounded-md text-xs font-medium", signalClass(stock.entry_signal))}>
              {signalLabel(stock.entry_signal)}
            </span>

            {/* Totalbetyg */}
            <div className="flex items-center gap-1.5">
              <span className="flex items-center text-xs text-[var(--color-text-muted)]">
                Totalbetyg
                <InfoTooltip
                  text="Systemets samlade betyg (0–100) baserat på 8 faktorer: Värde, Kvalitet, Momentum, Tillväxt, Risk, Storlek, Utdelning och Sentiment. Över 70 är starkt."
                  side="bottom"
                />
              </span>
              <span className={cn("font-mono font-bold text-base tabular", scoreColorClass(stock.score_total))}>
                {formatScore(stock.score_total)}
              </span>
            </div>

            {/* Trend */}
            <div className="flex items-center gap-1 text-xs" style={{ color: trendColor }}>
              <TrendIcon size={13} strokeWidth={1.5} />
              <span>{stock.trend_signal ?? "—"}</span>
            </div>

            {/* MEWS badge (#3) */}
            {stock.mews_flag && (
              <span className="flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-medium bg-[var(--color-accent-soft)] text-[var(--color-accent)] border border-[var(--color-accent-soft)]">
                <Zap size={10} strokeWidth={2} />
                Mångdubblar-kandidat
                <InfoTooltip
                  text="MEWS (Multi-Bagger Early Warning Score) — evidensbaserad signal baserad på FCF-yield, bolagsstorlek, P/S-tal, operativ hävstång, intäktsacceleration och accrual-kvalitet. ≥70 = potentiell mångdubblare."
                  side="bottom"
                />
              </span>
            )}

            {/* AI-prognos */}
            {stock.predicted_return != null && (
              <div className="flex items-center gap-1 text-xs">
                <span className="flex items-center text-[var(--color-text-muted)]">
                  AI-prognos 30d
                  <InfoTooltip text="Maskinlärd prognos för förväntad prisutveckling de närmaste 30 dagarna. OBS: Prognoser är osäkra — använd som ett av flera underlag, aldrig ensamt." side="bottom" />
                </span>
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
            {formatPrice(displayPrice)}
          </span>
          {stock.change_pct != null ? (
            <span className={cn("font-mono tabular text-sm font-medium", changeClass(stock.change_pct))}>
              {formatPctChange(stock.change_pct)} idag
            </span>
          ) : fallbackPrice != null ? (
            <span className="text-xs text-[var(--color-text-muted)]">senaste stängning</span>
          ) : null}
        </div>
      </div>

      {/* Row 2: Actions */}
      <div className="flex items-center gap-2 mt-3 flex-wrap">
        {/* Bevaka */}
        <button
          onClick={() => isWatching ? removeWatch.mutate() : addWatch.mutate()}
          disabled={addWatch.isPending || removeWatch.isPending}
          className={cn(
            "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors border",
            isWatching
              ? "border-[var(--color-warn)] text-[var(--color-warn)] bg-[var(--color-warn-soft)]"
              : "border-[var(--color-border)] hover:border-[var(--color-border-strong)] text-[var(--color-text-secondary)]",
          )}
        >
          <Star size={13} strokeWidth={1.5} fill={isWatching ? "currentColor" : "none"} />
          {isWatching ? "Bevakad" : "Bevaka"}
        </button>

        {/* Lägg i portfölj */}
        {!showAddForm ? (
          <button
            onClick={() => setShowAddForm(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors border
                       border-[var(--color-border)] hover:border-[var(--color-border-strong)] text-[var(--color-text-secondary)]"
          >
            <Plus size={13} strokeWidth={1.5} />
            Lägg i portfölj
          </button>
        ) : (
          <div className="flex items-center gap-2 flex-wrap">
            <input
              autoFocus
              type="number"
              min="0"
              step="1"
              value={shares}
              onChange={(e) => setShares(e.target.value)}
              placeholder="Antal aktier"
              className="w-32 h-7 px-2 rounded-lg text-xs border focus:outline-none bg-[var(--color-bg-elevated)] border-[var(--color-accent)] text-[var(--color-text-primary)]"
            />
            <input
              type="number"
              min="0"
              step="0.01"
              value={costBasis}
              onChange={(e) => setCostBasis(e.target.value)}
              placeholder={`Inköpskurs (valfri, ~${stock.price ? Math.round(stock.price) : ""})`}
              className="w-44 h-7 px-2 rounded-lg text-xs border focus:outline-none bg-[var(--color-bg-elevated)] border-[var(--color-border)] text-[var(--color-text-primary)]"
            />
            <button
              onClick={() => shares && parseFloat(shares) > 0 && addHolding.mutate()}
              disabled={!shares || parseFloat(shares) <= 0 || addHolding.isPending}
              className="flex items-center gap-1 h-7 px-3 rounded-lg text-xs font-medium
                         bg-[var(--color-accent)] text-white disabled:opacity-40"
            >
              <Check size={12} strokeWidth={2} />
              {addHolding.isPending ? "Sparar..." : "Spara"}
            </button>
            <button
              onClick={() => { setShowAddForm(false); setShares(""); setCostBasis(""); }}
              className="h-7 px-2 rounded-lg text-xs text-[var(--color-text-muted)]"
            >
              <X size={12} strokeWidth={1.5} />
            </button>
          </div>
        )}

        {stock.confidence_label === "Hög" || stock.confidence_label === "Medel" ? (
          <span className="ml-auto text-xs text-[var(--color-text-muted)]">
            Tillförlitlighet
            <InfoTooltip text="Modellens förtroende för sin 30-dagars prisprognos. Hög = stark signal. Låg = osäker prognos (påverkar inte övrig analys)." side="bottom" />
            : {stock.confidence_label}
          </span>
        ) : null}
      </div>
    </div>
  );
}
