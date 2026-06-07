"use client";

import React, { useState, useCallback, useMemo } from "react";
import { Search, X, Loader2, AlertCircle, TrendingUp, Brain, ChevronDown } from "lucide-react";
import { api } from "@/lib/api";
import {
  formatScore,
  formatPrice,
  formatPct,
  scoreColorClass,
  signalBadgeClass,
  signalShortLabel,
} from "@/lib/format";
import { cn } from "@/lib/utils";
import { MultiFactorRadar, tickerColor } from "@/components/charts/MultiFactorRadar";
import { useExperience } from "@/components/providers/ExperienceProvider";
import { useCompare, useStockSearch, useAICompare, type SearchResult, type CompareResponse } from "@/hooks/useCompare";
import {
  AreaChart, Area, XAxis, YAxis, Tooltip as RechartsTooltip,
  ResponsiveContainer, CartesianGrid, Legend,
} from "recharts";

// ─── Helpers ────────────────────────────────────────────────────────────────

function isUpGood(label: string): boolean {
  const upIsGood = [
    "Totalbetyg", "score_total", "Värdering", "score_value",
    "Kvalitet", "score_quality", "Momentum", "score_momentum",
    "Tillväxt", "score_growth", "Utdelning", "score_dividend",
    "Sentiment", "score_sentiment", "ROE", "Piotroski",
  ];
  return upIsGood.includes(label);
}

function formatMetric(val: number | string | null | undefined, label: string): string {
  if (val == null) return "—";
  const n = typeof val === "number" ? val : Number(val);
  if (isNaN(n)) return String(val);
  if (label === "P/E" || label === "Beta") return n.toFixed(1);
  if (label === "Piotroski") return `${n.toFixed(0)}/9`;
  if (label === "ROE") return formatPct(n);
  if (n > 100) return Math.round(n).toString();
  return n.toFixed(1);
}

// ─── Compare Chart (normalized price) ───────────────────────────────────────

function ComparePriceChart({ tickers }: { tickers: string[] }) {
  const [chartData, setChartData] = useState<any[] | null>(null);
  const [chartLoading, setChartLoading] = useState(false);
  const [chartError, setChartError] = useState<string | null>(null);

  React.useEffect(() => {
    if (tickers.length < 2) return;
    let cancelled = false;
    setChartLoading(true);
    setChartError(null);

    Promise.all(
      tickers.map(async (t, i) => {
        const data = await api<{ candles: { time: string; close: number }[] }>(
          `/api/stocks/${t}/price-history`
        );
        return { ticker: t, candles: data.candles || [], color: tickerColor(i) };
      })
    ).then((results) => {
      if (cancelled) return;
      const timeMap: Record<string, any> = {};
      for (const { ticker, candles } of results) {
        if (candles.length === 0) continue;
        const basePrice = candles[0]?.close || 1;
        for (const c of candles) {
          if (!timeMap[c.time]) timeMap[c.time] = { time: c.time };
          timeMap[c.time][ticker] = ((c.close - basePrice) / basePrice) * 100;
        }
      }
      const data = Object.values(timeMap)
        .sort((a: any, b: any) => a.time.localeCompare(b.time));
      setChartData(data as any[]);
    }).catch((err) => {
      if (!cancelled) setChartError(err instanceof Error ? err.message : "Kunde inte hämta prisdata");
    }).finally(() => {
      if (!cancelled) setChartLoading(false);
    });

    return () => { cancelled = true; };
  }, [tickers]);

  if (chartLoading) return <div className="skeleton h-52 rounded-xl" />;
  if (chartError) return <div className="text-xs text-[var(--color-down)] text-center py-8">{chartError}</div>;
  if (!chartData || chartData.length === 0) return null;

  return (
    <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-bg-surface)] p-4">
      <h3 className="text-sm font-semibold text-[var(--color-text-secondary)] mb-3">
        Prisutveckling (normaliserad, bas=0%)
      </h3>
      <ResponsiveContainer width="100%" height={220}>
        <AreaChart data={chartData} margin={{ top: 4, right: 4, bottom: 0, left: -10 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
          <XAxis dataKey="time" tick={{ fontSize: 10, fill: "var(--color-text-muted)" }} tickLine={false} axisLine={false} />
          <YAxis tick={{ fontSize: 10, fill: "var(--color-text-muted)" }} tickFormatter={(v) => `${v.toFixed(0)}%`} tickLine={false} axisLine={false} />
          <RechartsTooltip
            contentStyle={{ background: "var(--color-bg-elevated)", border: "1px solid var(--color-border)", borderRadius: 8, fontSize: 12 }}
          />
          <Legend wrapperStyle={{ fontSize: 11, color: "var(--color-text-secondary)" }} />
          {tickers.map((t, i) => (
            <Area
              key={t}
              type="monotone"
              dataKey={t}
              stroke={tickerColor(i)}
              fill="transparent"
              strokeWidth={1.5}
              dot={false}
              name={t}
            />
          ))}
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

// ─── AI Compare Card ────────────────────────────────────────────────────────

function AICompareCard({ tickers, stockDatas }: { tickers: string[]; stockDatas: any[] }) {
  const { data, isLoading, error } = useAICompare(tickers, stockDatas);

  if (isLoading) return <div className="skeleton h-40 rounded-xl" />;
  if (error || !data) {
    return (
      <div className="flex flex-col items-center py-8 gap-2 text-center">
        <AlertCircle size={18} className="text-[var(--color-text-muted)]" />
        <p className="text-xs text-[var(--color-text-muted)]">AI-jämförelse misslyckades</p>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-bg-surface)] p-4">
      <div className="flex items-center gap-2 mb-3">
        <Brain size={16} strokeWidth={1.5} className="text-[var(--color-accent)]" />
        <h3 className="text-sm font-semibold text-[var(--color-text-secondary)]">AI-jämförelse</h3>
      </div>

      <div className="space-y-3">
        <div className="flex items-center gap-2">
          <span className="text-xs text-[var(--color-text-muted)]">Rekommendation:</span>
          <span className="text-sm font-bold font-mono text-[var(--color-accent)]">{data.recommendation}</span>
        </div>

        <p className="text-sm text-[var(--color-text-primary)] leading-relaxed">{data.reasoning}</p>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div className="space-y-1.5">
            <span className="text-[11px] font-semibold text-[var(--color-up)]">Styrkor</span>
            {Object.entries(data.strengths).filter(([, v]) => v).map(([t, s]) => (
              <div key={t} className="text-xs text-[var(--color-text-secondary)]">
                <span className="font-mono font-medium text-[var(--color-text-primary)]">{t}:</span> {s}
              </div>
            ))}
          </div>
          <div className="space-y-1.5">
            <span className="text-[11px] font-semibold text-[var(--color-down)]">Svagheter</span>
            {Object.entries(data.weaknesses).filter(([, v]) => v).map(([t, s]) => (
              <div key={t} className="text-xs text-[var(--color-text-secondary)]">
                <span className="font-mono font-medium text-[var(--color-text-primary)]">{t}:</span> {s}
              </div>
            ))}
          </div>
        </div>

        <p className="text-xs text-[var(--color-text-muted)] italic">{data.summary}</p>
        <div className="text-[10px] text-[var(--color-text-muted)]">Analys från {data.cached_date}</div>
      </div>
    </div>
  );
}

// ─── Main View ──────────────────────────────────────────────────────────────

export function JamforView() {
  const [tickers, setTickers] = useState<string[]>([]);
  const [query, setQuery] = useState("");
  const { data: results } = useStockSearch(query, 6);
  const { data: compareData, isLoading, error } = useCompare(tickers);
  const [stockDatas, setStockDatas] = useState<any[]>([]);
  const [showAllMetrics, setShowAllMetrics] = useState(false);
  const { level } = useExperience();
  const isExpert = level === "expert";

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
    setStockDatas([]);
  }, []);

  // Fetch stock details for AI compare
  React.useEffect(() => {
    if (tickers.length < 2) return;
    let cancelled = false;
    Promise.all(
      tickers.map(async (t) => {
        try {
          return await api<any>(`/api/stocks/${t}`);
        } catch {
          return { ticker: t };
        }
      })
    ).then((data) => {
      if (!cancelled) setStockDatas(data.filter(Boolean));
    }).catch(() => {});
    return () => { cancelled = true; };
  }, [tickers]);

  // Radar data from compare metrics
  const radarSeries = useMemo(() => {
    if (!compareData) return [];
    return compareData.tickers.map((t, i) => {
      const getVal = (label: string) => {
        const m = compareData.metrics.find((m) => m.label === label);
        const v = m?.values[t];
        return typeof v === "number" ? v : 0;
      };
      return {
        ticker: t,
        color: tickerColor(i),
        values: {
          score_value: getVal("Värdering"),
          score_quality: getVal("Kvalitet"),
          score_momentum: getVal("Momentum"),
          score_growth: getVal("Tillväxt"),
          score_risk: getVal("Risk"),
          score_dividend: getVal("Utdelning"),
          score_sentiment: 50,
          score_size: 50,
        },
      };
    });
  }, [compareData]);

  // Core metrics (always visible) vs extended (behind toggle)
  const coreMetrics = ["Totalbetyg", "Värdering", "Kvalitet", "Momentum", "Tillväxt", "Risk"];
  const extendedMetrics = ["P/E", "ROE", "Piotroski", "Beta", "Utdelning", "Signal"];

  return (
    <div className="max-w-5xl mx-auto px-4 py-8 sm:py-12">
      <h1 className="text-2xl sm:text-3xl font-bold text-[var(--color-text-primary)] mb-2">
        Jämför aktier
      </h1>
      <p className="text-sm text-[var(--color-text-secondary)] mb-6">
        Välj upp till 5 aktier för att jämföra betyg, nyckeltal och prisutveckling sida vid sida.
      </p>

      {/* Ticker selector */}
      <div
        className="rounded-2xl p-4 sm:p-6 mb-6 bg-[var(--color-bg-surface)]"
        style={{ border: "1px solid var(--color-border-strong)" }}
      >
        <div className="flex flex-wrap gap-2 mb-3">
          {tickers.map((t, i) => (
            <span
              key={t}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-mono font-medium"
              style={{
                background: `${tickerColor(i)}20`,
                color: tickerColor(i),
              }}
            >
              {t}
              <button onClick={() => removeTicker(t)} className="hover:opacity-70 transition-opacity" aria-label={`Ta bort ${t}`}>
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

        <div className="relative">
          <Search size={16} strokeWidth={1.5} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)]" />
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

          {query.length >= 2 && (
            <div
              className="absolute top-full left-0 right-0 mt-1 rounded-xl overflow-hidden shadow-lg z-10 max-h-60 overflow-y-auto
                         bg-[var(--color-bg-surface)]"
              style={{ border: "1px solid var(--color-border-strong)" }}
            >
              {!results || results.length === 0 ? (
                <div className="py-4 text-center text-xs text-[var(--color-text-muted)]">
                  {query.length >= 2 ? "Inga träffar" : "Fortsätt skriv..."}
                </div>
              ) : (
                results.map((stock) => {
                  const added = tickers.includes(stock.ticker);
                  return (
                    <button
                      key={stock.ticker}
                      onClick={() => !added && addTicker(stock.ticker)}
                      disabled={added}
                      className={cn(
                        "w-full flex items-center gap-3 px-4 py-2.5 text-sm transition-colors text-left",
                        added
                          ? "opacity-40 cursor-not-allowed text-[var(--color-text-secondary)] bg-[var(--color-bg-elevated)]"
                          : "hover:bg-[var(--color-bg-elevated)] text-[var(--color-text-primary)] cursor-pointer"
                      )}
                    >
                      <div className="flex flex-col flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-semibold text-[var(--color-text-primary)] truncate">
                            {stock.name || stock.ticker}
                          </span>
                          <span className="font-mono text-[var(--color-text-secondary)] text-[11px]">
                            {stock.ticker}
                          </span>
                          {stock.in_universe === false && (
                            <span className="text-[10px] px-1.5 py-0.5 rounded font-medium
                              bg-[var(--color-warn)]/10 text-[var(--color-warn)] border border-[var(--color-warn)]/20">
                              Ny
                            </span>
                          )}
                        </div>
                      </div>
                      {stock.score_total != null && (
                        <span className={`tabular text-xs font-mono font-semibold ${scoreColorClass(stock.score_total)}`}>
                          {formatScore(stock.score_total)}
                        </span>
                      )}
                    </button>
                  );
                })
              )}
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

      {/* Loading */}
      {isLoading && (
        <div className="flex items-center justify-center py-16">
          <div className="flex items-center gap-3 text-sm text-[var(--color-text-secondary)]">
            <Loader2 size={18} className="animate-spin" />
            Hämtar jämförelsedata...
          </div>
        </div>
      )}

      {/* Error */}
      {error && !isLoading && (
        <div className="rounded-2xl p-4 flex items-start gap-3 text-sm mb-6"
          style={{ background: "color-mix(in srgb, var(--color-down) 10%, transparent)", border: "1px solid color-mix(in srgb, var(--color-down) 30%, transparent)" }}>
          <AlertCircle size={16} className="text-[var(--color-down)] shrink-0 mt-0.5" />
          <span className="text-[var(--color-text-secondary)]">{error.message || "Kunde inte hämta jämförelsedata"}</span>
        </div>
      )}

      {/* Compare content */}
      {compareData && !isLoading && tickers.length >= 2 && (
        <div className="space-y-6">
          {/* Single overlayed factor radar */}
          <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-bg-surface)] p-4">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-semibold text-[var(--color-text-secondary)]">Faktorprofil</h3>
              {tickers.map((t, i) => {
                const metric = compareData.metrics.find((m) => m.label === "Totalbetyg");
                const score = metric?.values[t];
                return (
                  <span key={t} className="text-xs font-mono" style={{ color: tickerColor(i) }}>
                    {t}: {score != null ? formatScore(Number(score)) : "—"}
                  </span>
                );
              })}
            </div>
            <MultiFactorRadar series={radarSeries} />
          </div>

          {/* Core metric table (simple, scannable) */}
          <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-bg-surface)] overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-[var(--color-border)] bg-[var(--color-bg-elevated)]">
                    <th className="px-4 py-2.5 text-left font-medium text-[var(--color-text-muted)] w-32">Nyckeltal</th>
                    {tickers.map((t, i) => (
                      <th key={t} className="px-4 py-2.5 text-right font-mono font-semibold" style={{ color: tickerColor(i) }}>
                        {t}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {/* Core metrics */}
                  {coreMetrics.map((label) => {
                    const metric = compareData.metrics.find((m) => m.label === label);
                    if (!metric) return null;
                    const vals = tickers.map((t) => ({
                      ticker: t,
                      value: metric.values[t],
                    }));
                    const numericVals = vals.filter(
                      (v): v is { ticker: string; value: number } =>
                        typeof v.value === "number" && !Number.isNaN(v.value)
                    );
                    const upGood = isUpGood(label);
                    const best = numericVals.length > 0
                      ? [...numericVals].sort((a, b) => upGood ? b.value - a.value : a.value - b.value)[0].ticker
                      : null;

                    return (
                      <tr key={label} className="border-b border-[var(--color-border)] last:border-0">
                        <td className="px-4 py-2.5 text-[var(--color-text-secondary)] font-medium">{label}</td>
                        {vals.map((v) => (
                          <td
                            key={v.ticker}
                            className={cn(
                              "px-4 py-2.5 text-right font-mono tabular",
                              v.ticker === best && numericVals.length >= 2
                                ? "text-[var(--color-up)]"
                                : "text-[var(--color-text-primary)]",
                            )}
                          >
                            {label === "Signal" && typeof v.value === "string" ? (
                              <span className={cn("inline-block px-1.5 py-0.5 rounded text-[11px] font-semibold border", signalBadgeClass(v.value))}>
                                {signalShortLabel(v.value)}
                              </span>
                            ) : (
                              formatMetric(v.value, label)
                            )}
                          </td>
                        ))}
                      </tr>
                    );
                  })}

                  {/* Extended metrics toggle */}
                  {extendedMetrics.length > 0 && (
                    <>
                      <tr>
                        <td colSpan={tickers.length + 1} className="px-0 py-0">
                          <button
                            onClick={() => setShowAllMetrics(!showAllMetrics)}
                            className="flex items-center gap-1.5 w-full px-4 py-2.5 text-xs text-[var(--color-text-muted)]
                                       hover:text-[var(--color-text-secondary)] transition-colors"
                          >
                            <ChevronDown size={12} className={cn("transition-transform", showAllMetrics && "rotate-180")} />
                            {showAllMetrics ? "Dölj" : "Visa fler nyckeltal"}
                          </button>
                        </td>
                      </tr>
                      {showAllMetrics && extendedMetrics.map((label) => {
                        const metric = compareData.metrics.find((m) => m.label === label);
                        if (!metric) return null;
                        const vals = tickers.map((t) => ({
                          ticker: t,
                          value: metric.values[t],
                        }));
                        const numericVals = vals.filter(
                          (v): v is { ticker: string; value: number } =>
                            typeof v.value === "number" && !Number.isNaN(v.value)
                        );
                        const upGood = isUpGood(label);
                        const best = numericVals.length > 0
                          ? [...numericVals].sort((a, b) => upGood ? b.value - a.value : a.value - b.value)[0].ticker
                          : null;

                        return (
                          <tr key={label} className="border-b border-[var(--color-border)] last:border-0">
                            <td className="px-4 py-2.5 text-[var(--color-text-secondary)] font-medium">{label}</td>
                            {vals.map((v) => (
                              <td
                                key={v.ticker}
                                className={cn(
                                  "px-4 py-2.5 text-right font-mono tabular",
                                  v.ticker === best && numericVals.length >= 2
                                    ? "text-[var(--color-up)]"
                                    : "text-[var(--color-text-primary)]",
                                )}
                              >
                                {label === "Signal" && typeof v.value === "string" ? (
                                  <span className={cn("inline-block px-1.5 py-0.5 rounded text-[11px] font-semibold border", signalBadgeClass(v.value))}>
                                    {signalShortLabel(v.value)}
                                  </span>
                                ) : (
                                  formatMetric(v.value, label)
                                )}
                              </td>
                            ))}
                          </tr>
                        );
                      })}
                    </>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Price comparison chart */}
          <ComparePriceChart tickers={tickers} />

          {/* AI Compare */}
          {stockDatas.length >= 2 && (
            <AICompareCard tickers={tickers} stockDatas={stockDatas} />
          )}
        </div>
      )}

      {/* Empty state */}
      {!compareData && !isLoading && !error && tickers.length >= 2 && (
        <div className="py-16 text-center text-sm text-[var(--color-text-muted)]">
          <TrendingUp size={24} className="mx-auto mb-3 opacity-40" />
          Kunde inte hitta data för de valda aktierna. Försök med andra tickers.
        </div>
      )}
    </div>
  );
}
