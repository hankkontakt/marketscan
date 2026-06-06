"use client";

import { useState, useEffect, useCallback } from "react";
import { Search, X, Loader2, Plus, AlertCircle } from "lucide-react";
import { api } from "@/lib/api";
import {
  formatScore,
  formatPrice,
  formatPctChange,
  formatMarketCap,
  formatPct,
  scoreColorClass,
  changeClass,
} from "@/lib/format";
import { cn } from "@/lib/utils";
import type { ScanRow } from "@/types/scan";

interface SearchResult {
  ticker: string;
  name: string | null;
  score_total: number | null;
  entry_signal: string | null;
  price: number | null;
  change_pct: number | null;
}

interface CompareMetric {
  label: string;
  values: Record<string, number | string | null>;
}

interface CompareResponse {
  tickers: string[];
  metrics: CompareMetric[];
}

// ─── Metric display helpers ──────────────────────────────────────────────

function formatMetricValue(label: string, val: number | string | null): string {
  if (val === null || val === undefined) return "—";
  if (typeof val === "string") return val;
  if (label === "Score" || label === "Totalbetyg") return Math.round(val).toString();
  return String(val);
}

function isPositiveDirection(label: string): boolean {
  const upIsGood = [
    "Totalbetyg", "score_total",
    "Värdering", "score_value",
    "Kvalitet", "score_quality",
    "Momentum", "score_momentum",
    "Tillväxt", "score_growth",
    "Utdelning", "score_dividend",
    "Sentiment", "score_sentiment",
    "ROE",
    "Piotroski",
    "Dir.avk",
  ];
  return upIsGood.includes(label);
}

function isPctMetric(label: string): boolean {
  return ["ROE", "Dir.avk"].includes(label);
}

function getValueClass(label: string, val: number | string | null): string {
  if (val === null || val === undefined || typeof val === "string") return "";
  const upGood = isPositiveDirection(label);
  if (upGood) return val >= 0 ? "text-[var(--color-up)]" : "text-[var(--color-down)]";
  return val <= 0 ? "text-[var(--color-up)]" : "text-[var(--color-down)]";
}

// ─── Debounced search hook ───────────────────────────────────────────────

function useStockSearch(query: string) {
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!query.trim() || query.length < 2) {
      setResults([]);
      return;
    }
    const timer = setTimeout(async () => {
      setLoading(true);
      try {
        const data = await api<SearchResult[]>(
          `/api/stocks?q=${encodeURIComponent(query)}&limit=6`
        );
        setResults(data);
      } catch {
        setResults([]);
      } finally {
        setLoading(false);
      }
    }, 250);
    return () => clearTimeout(timer);
  }, [query]);

  return { results, loading };
}

// ─── Main view ───────────────────────────────────────────────────────────

export function JamforView() {
  const [tickers, setTickers] = useState<string[]>([]);
  const [query, setQuery] = useState("");
  const [compareData, setCompareData] = useState<CompareResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { results, loading: searchLoading } = useStockSearch(query);

  const addTicker = useCallback((ticker: string) => {
    setTickers((prev) => {
      const upper = ticker.toUpperCase();
      if (prev.includes(upper) || prev.length >= 5) return prev;
      return [...prev, upper];
    });
    setQuery("");
  }, []);

  const removeTicker = useCallback((ticker: string) => {
    setTickers((prev) => prev.filter((t) => t !== ticker));
    setCompareData(null);
    setError(null);
  }, []);

  const handleCompare = useCallback(async () => {
    if (tickers.length < 2) return;
    setLoading(true);
    setError(null);
    try {
      const data = await api<CompareResponse>("/api/stocks/compare", {
        method: "POST",
        body: JSON.stringify({ tickers }),
      });
      setCompareData(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Kunde inte hämta jämförelsedata");
    } finally {
      setLoading(false);
    }
  }, [tickers]);

  // Auto-run when tickers change to 2+
  useEffect(() => {
    if (tickers.length >= 2) {
      handleCompare();
    } else {
      setCompareData(null);
    }
  }, [tickers.length, handleCompare]);

  // ─── Render ──────────────────────────────────────────────────────────

  return (
    <div className="max-w-4xl mx-auto px-4 py-8 sm:py-12">
      <h1 className="text-2xl sm:text-3xl font-bold text-[var(--color-text-primary)] mb-2">
        Jämför aktier
      </h1>
      <p className="text-sm text-[var(--color-text-secondary)] mb-6">
        Välj upp till 5 aktier för att jämföra deras nyckeltal sida vid sida.
      </p>

      {/* Selected tickers + search */}
      <div
        className="rounded-2xl p-4 sm:p-6 mb-6 bg-[var(--color-bg-surface)]"
        style={{ border: "1px solid var(--color-border-strong)" }}
      >
        {/* Active ticker pills */}
        <div className="flex flex-wrap gap-2 mb-3">
          {tickers.map((t) => (
            <span
              key={t}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-mono font-medium
                         bg-[var(--color-accent-soft)] text-[var(--color-accent)]"
            >
              {t}
              <button
                onClick={() => removeTicker(t)}
                className="hover:opacity-70 transition-opacity"
                aria-label={`Ta bort ${t}`}
              >
                <X size={14} strokeWidth={2} />
              </button>
            </span>
          ))}
          {tickers.length === 0 && (
            <span className="text-xs text-[var(--color-text-muted)] py-1">
              Lägg till minst 2 aktier för att jämföra
            </span>
          )}
        </div>

        {/* Search input */}
        <div className="relative">
          <Search
            size={16}
            strokeWidth={1.5}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)]"
          />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Sök på ticker eller namn..."
            disabled={tickers.length >= 5}
            className="w-full h-10 pl-9 pr-3 rounded-xl text-sm bg-[var(--color-bg-elevated)]
                       text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)]
                       outline-none transition-shadow
                       focus:ring-2 focus:ring-[var(--color-accent)] focus:ring-offset-0
                       disabled:opacity-40 disabled:cursor-not-allowed"
            style={{ border: "1px solid var(--color-border)" }}
          />

          {/* Search dropdown */}
          {query.length >= 2 && (
            <div
              className="absolute top-full left-0 right-0 mt-1 rounded-xl overflow-hidden shadow-lg z-10
                         bg-[var(--color-bg-surface)]"
              style={{ border: "1px solid var(--color-border-strong)" }}
            >
              {searchLoading && (
                <div className="flex items-center justify-center gap-2 py-4 text-xs text-[var(--color-text-muted)]">
                  <Loader2 size={14} className="animate-spin" />
                  Söker...
                </div>
              )}
              {!searchLoading && results.length === 0 && (
                <div className="py-4 text-center text-xs text-[var(--color-text-muted)]">
                  Inga träffar
                </div>
              )}
              {!searchLoading &&
                results.map((stock) => {
                  const added = tickers.includes(stock.ticker);
                  return (
                    <button
                      key={stock.ticker}
                      onClick={() => !added && addTicker(stock.ticker)}
                      disabled={added}
                      className={cn(
                        "w-full flex items-center gap-3 px-4 py-2.5 text-sm transition-colors",
                        added
                          ? "opacity-40 cursor-not-allowed text-[var(--color-text-secondary)] bg-[var(--color-bg-elevated)]"
                          : "hover:bg-[var(--color-bg-elevated)] text-[var(--color-text-primary)] cursor-pointer"
                      )}
                    >
                      <div className="flex flex-col flex-1 min-w-0 text-left">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-xs font-semibold">{stock.ticker}</span>
                          <span className="text-[var(--color-text-secondary)] truncate text-xs">
                            {stock.name}
                          </span>
                        </div>
                      </div>
                      {stock.score_total != null && (
                        <span className={`tabular text-xs font-mono font-semibold ${scoreColorClass(stock.score_total)}`}>
                          {formatScore(stock.score_total)}
                        </span>
                      )}
                      {!added && <Plus size={14} className="text-[var(--color-text-muted)] shrink-0" />}
                      {added && <span className="text-[10px] text-[var(--color-text-muted)] shrink-0">Tillagd</span>}
                    </button>
                  );
                })}
            </div>
          )}
        </div>

        {tickers.length < 5 && query.length < 2 && (
          <p className="text-[11px] text-[var(--color-text-muted)] mt-2">
            {tickers.length === 0
              ? "Börja skriv för att söka efter aktier"
              : `Du kan lägga till ${5 - tickers.length} till`}
          </p>
        )}
      </div>

      {/* Loading state */}
      {loading && (
        <div className="flex items-center justify-center py-16">
          <div className="flex items-center gap-3 text-sm text-[var(--color-text-secondary)]">
            <Loader2 size={18} className="animate-spin" />
            Hämtar jämförelsedata...
          </div>
        </div>
      )}

      {/* Error state */}
      {error && !loading && (
        <div
          className="rounded-2xl p-4 flex items-start gap-3 text-sm"
          style={{
            background: "color-mix(in srgb, var(--color-down) 10%, transparent)",
            border: "1px solid color-mix(in srgb, var(--color-down) 30%, transparent)",
          }}
        >
          <AlertCircle size={16} className="text-[var(--color-down)] shrink-0 mt-0.5" />
          <span className="text-[var(--color-text-secondary)]">{error}</span>
        </div>
      )}

      {/* Comparison table */}
      {compareData && !loading && (
        <div
          className="rounded-2xl overflow-hidden bg-[var(--color-bg-surface)]"
          style={{ border: "1px solid var(--color-border-strong)" }}
        >
          {/* Table header */}
          <div
            className="grid gap-px"
            style={{
              gridTemplateColumns: `180px repeat(${compareData.tickers.length}, 1fr)`,
            }}
          >
            {/* Empty corner */}
            <div className="p-3 bg-[var(--color-bg-elevated)]" />

            {/* Ticker headers */}
            {compareData.tickers.map((t) => (
              <div
                key={t}
                className="p-3 text-center font-mono text-sm font-semibold bg-[var(--color-bg-elevated)]
                           text-[var(--color-text-primary)]"
              >
                {t}
              </div>
            ))}

            {/* Metric rows */}
            {compareData.metrics.map((metric) => {
              const values = compareData.tickers.map((t) => metric.values[t]);
              const numericValues = values.filter(
                (v): v is number => typeof v === "number" && !Number.isNaN(v)
              );

              let bestIdx: number | null = null;
              let worstIdx: number | null = null;
              if (numericValues.length > 0) {
                const upGood = isPositiveDirection(metric.label);
                const sorted = [...numericValues].sort((a, b) => (upGood ? b - a : a - b));
                const bestVal = sorted[0];
                const worstVal = sorted[sorted.length - 1];
                bestIdx = values.findIndex(
                  (v) => typeof v === "number" && v === bestVal
                );
                worstIdx = values.findIndex(
                  (v) => typeof v === "number" && v === worstVal
                );
              }

              return (
                <>
                  {/* Label */}
                  <div className="p-3 text-xs font-medium text-[var(--color-text-secondary)] bg-[var(--color-bg)]">
                    {metric.label}
                  </div>

                  {/* Values */}
                  {compareData.tickers.map((t, idx) => {
                    const v = metric.values[t];
                    const isBest = idx === bestIdx;
                    const isWorst = idx === worstIdx;
                    const formatted = formatMetricValue(metric.label, v);

                    return (
                      <div
                        key={`${metric.label}-${t}`}
                        className={cn(
                          "p-3 text-center text-xs font-mono tabular bg-[var(--color-bg)]",
                          isBest && "bg-[var(--color-up)]/10",
                          isWorst && "bg-[var(--color-down)]/10",
                          metric.label === "Signal" && typeof v === "string"
                            ? "font-semibold"
                            : "",
                          metric.label === "Signal" && v === "STARK"
                            ? "text-[var(--color-score-high)]"
                            : metric.label === "Signal" && v === "OK"
                            ? "text-[var(--color-score-mid)]"
                            : metric.label === "Signal" && v === "VÄNTA"
                            ? "text-[var(--color-score-low)]"
                            : metric.label === "Signal" && v === "EJ_AKTUELL"
                            ? "text-[var(--color-text-muted)]"
                            : typeof v === "number"
                            ? getValueClass(metric.label, v)
                            : "text-[var(--color-text-primary)]"
                        )}
                      >
                        {formatted}
                      </div>
                    );
                  })}
                </>
              );
            })}
          </div>
        </div>
      )}

      {/* Empty (no data) */}
      {!compareData && !loading && !error && tickers.length >= 2 && (
        <div className="py-16 text-center text-sm text-[var(--color-text-muted)]">
          <Search size={24} className="mx-auto mb-3 opacity-40" />
          Kunde inte hitta data för de valda aktierna. Försök med andra tickers.
        </div>
      )}
    </div>
  );
}
