"use client";

import { useState, useMemo } from "react";
import Link from "next/link";
import { ArrowRight, TrendingUp, TrendingDown, Minus, Star, Globe, BarChart3 } from "lucide-react";
import {
  AreaChart, Area, ResponsiveContainer, Tooltip as ReTooltip,
} from "recharts";
import { useScreener } from "@/hooks/useScreener";
import { usePortfolio, useWatchlist, usePortfolioHistory } from "@/hooks/usePortfolio";
import { ScoreSparkline } from "@/components/charts/ScoreSparkline";
import { InfoTooltip } from "@/components/ui/InfoTooltip";
import {
  formatPrice, formatPctChange, signalLabel, signalClass,
  scoreColorClass, formatScore, changeClass, formatNumber,
} from "@/lib/format";
import { cn } from "@/lib/utils";
import { useGlobalIndices, GlobalIndexPanel, useTopMovers, type TopMover, useSectorOverview } from "@/hooks/useMarkets";

// ─── Mock portfolio chart data (fallback when no real history) ────
const MOCK_CHART = [
  { m: "Jan", v: 210000 }, { m: "Feb", v: 218500 }, { m: "Mar", v: 215000 },
  { m: "Apr", v: 224000 }, { m: "Maj", v: 239000 }, { m: "Jun", v: 248300 },
];

// ─── Main view ────────────────────────────────────────────────────────────────

export function OversiktView() {
  const PERIOD_LABELS = ["1M", "3M", "6M", "12M"];

  const { data: topPicks = [], isLoading: picksLoading } = useScreener({
    segments: ["large_cap", "mid_cap", "small_cap", "micro_cap"],
    entry_signal: "STARK",
    score_min: 60,
    limit: 3,
  });
  const { data: portfolio } = usePortfolio();
  const { data: watchlist = [] } = useWatchlist();
  const { data: history } = usePortfolioHistory();
  const { data: markets } = useGlobalIndices();

  const holdings = portfolio?.holdings ?? [];
  const totalValue = useMemo(
    () => holdings.reduce((s, h) => s + (h.price ?? 0) * h.shares, 0),
    [holdings]
  );
  const totalCost = useMemo(
    () => holdings.reduce((s, h) => s + (h.cost_basis ?? 0) * h.shares, 0),
    [holdings]
  );
  const todayChange = useMemo(
    () => holdings.reduce((s, h) => s + (h.change_pct ?? 0) * (h.price ?? 0) * h.shares, 0),
    [holdings]
  );
  const hasPortfolio = holdings.length > 0;

  // Build period data from API or fallback to null
  const periods = PERIOD_LABELS.map((label) => {
    const apiPeriod = history?.periods?.[label];
    if (apiPeriod?.pct != null) {
      const sign = apiPeriod.pct >= 0 ? "+" : "";
      return { label, pct: `${sign}${apiPeriod.pct.toFixed(1).replace(".", ",")} %`, positive: apiPeriod.positive ?? apiPeriod.pct >= 0 };
    }
    return { label, pct: null, positive: null };
  });

  // Use mock chart data if no real holdings
  const chartValue = hasPortfolio ? totalValue : 248300;
  const chartData = MOCK_CHART.map((d, i) =>
    i === MOCK_CHART.length - 1
      ? { ...d, v: chartValue }
      : d
  );

  // Weekday greeting
  const now = new Date();
  const hour = now.getHours();
  const greeting = hour < 10 ? "God morgon" : hour < 13 ? "Hej" : hour < 18 ? "God eftermiddag" : "God kväll";
  const dateStr = now.toLocaleDateString("sv-SE", {
    weekday: "long", day: "numeric", month: "long",
  });

  return (
    <div className="max-w-4xl mx-auto space-y-6 pb-12">

      {/* ── Greeting ─────────────────────────────────────── */}
      <div className="flex items-baseline justify-between pt-2">
        <h1 className="text-xl font-semibold text-[var(--color-text-primary)]">
          {greeting}
        </h1>
        <span className="text-sm capitalize text-[var(--color-text-muted)]">
          {dateStr}
        </span>
      </div>

      {/* ── Portfolio card ───────────────────────────────── */}
      <PortfolioCard
        totalValue={chartValue}
        todayChange={todayChange}
        chartData={chartData}
        hasRealData={hasPortfolio}
        periods={periods}
      />

      {/* ── Two-column section ───────────────────────────── */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {/* Strong buy opportunities */}
        <TopPicksCard picks={topPicks} isLoading={picksLoading} />

        {/* Watchlist */}
        <WatchlistCard items={watchlist.slice(0, 5)} />
      </div>

      {/* ── Global markets ──────────────────────────────── */}
      {markets?.indices && markets.indices.length > 0 && (
        <div className="rounded-xl border p-5 bg-[var(--color-bg-surface)] border-[var(--color-border)]">
          <div className="flex items-center gap-2 mb-3">
            <Globe size={15} strokeWidth={1.5} className="text-[var(--color-accent)]" />
            <span className="text-sm font-semibold text-[var(--color-text-primary)]">
              Globala index
            </span>
            <Link href="/marknad" className="ml-auto flex items-center gap-1 text-xs text-[var(--color-accent)]">
              Visa alla <ArrowRight size={12} strokeWidth={1.5} />
            </Link>
          </div>
          <GlobalIndexPanel indices={markets.indices} />
        </div>
      )}

      {/* ── Dagens marknad ─────────────────────────────── */}
      <DayMarketSection />
    </div>
  );
}

// ─── Portfolio card ───────────────────────────────────────────────────────────

function PortfolioCard({
  totalValue,
  todayChange,
  chartData,
  hasRealData,
  periods,
}: {
  totalValue: number;
  todayChange: number;
  chartData: { m: string; v: number }[];
  hasRealData: boolean;
  periods: { label: string; pct: string | null; positive: boolean | null }[];
}) {
  const [activePeriod, setActivePeriod] = useState("6M");

  const activePeriodData = periods.find(p => p.label === activePeriod);

  return (
    <div
      className="rounded-2xl border p-6 bg-[var(--color-bg-surface)] border-[var(--color-border)]"
    >
      {/* Top row: value + change */}
      <div className="flex items-start justify-between mb-5">
        <div>
          <div className="flex items-center gap-1.5 mb-1">
            <span className="text-sm text-[var(--color-text-muted)]">
              Portföljvärde
            </span>
            <InfoTooltip text="Det totala marknadsvärdet på alla dina aktieinnehav just nu." />
          </div>
          <div className="text-3xl font-bold font-mono tabular tracking-tight text-[var(--color-text-primary)]">
            {formatPrice(totalValue)}
          </div>
          {!hasRealData && (
            <p className="text-xs mt-1 text-[var(--color-text-muted)]">
              Exempeldata — lägg till innehav i{" "}
              <Link href="/portfolj" className="underline text-[var(--color-accent)]">
                Min portfölj
              </Link>
            </p>
          )}
        </div>

        <div className="text-right">
          <div className="flex items-center gap-1 justify-end mb-0.5">
            <span className="text-xs text-[var(--color-text-muted)]">Idag</span>
            <InfoTooltip text="Portföljens värdeförändring under dagens handelsdag." side="left" />
          </div>
          <div className={cn("font-mono tabular text-sm font-medium", totalValue > 0 ? changeClass(todayChange / totalValue) : "")}>
            {todayChange >= 0 ? "+" : ""}{formatPrice(todayChange)}
          </div>
        </div>
      </div>

      {/* Area chart */}
      <div className="mb-4" style={{ height: 160 }}>
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={chartData} margin={{ top: 4, right: 0, bottom: 0, left: 0 }}>
            <defs>
              <linearGradient id="portfolioGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="var(--color-accent)" stopOpacity={0.15} />
                <stop offset="95%" stopColor="var(--color-accent)" stopOpacity={0} />
              </linearGradient>
            </defs>
            <ReTooltip
              content={({ active, payload }) => {
                if (!active || !payload?.length) return null;
                return (
                  <div
                    className="px-3 py-2 rounded-lg text-xs shadow-lg bg-[var(--color-bg-surface)] text-[var(--color-text-primary)]"
                    style={{ border: "1px solid var(--color-border-strong)" }}
                  >
                    <span className="font-mono tabular">{formatPrice(payload[0].value as number)}</span>
                  </div>
                );
              }}
            />
            <Area
              type="monotone"
              dataKey="v"
              stroke="var(--color-accent)"
              strokeWidth={2}
              fill="url(#portfolioGradient)"
              dot={false}
              activeDot={{ r: 4, strokeWidth: 0, fill: "var(--color-accent)" }}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Period selector */}
      <div className="flex items-center gap-1 flex-wrap">
        <span className="text-xs text-[var(--color-text-muted)] mr-1">Avkastning</span>
        <InfoTooltip text="Avkastning senaste perioden." side="bottom" />
        {periods.map((period) => {
          const isActive = period.label === activePeriod;
          return (
            <button
              key={period.label}
              onClick={() => setActivePeriod(period.label)}
              className={cn(
                "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all",
                isActive
                  ? "bg-[var(--color-accent)] text-white"
                  : "hover:bg-[var(--color-bg-elevated)] text-[var(--color-text-muted)]",
              )}
            >
              <span>{period.label}</span>
              {isActive && period.pct != null && (
                <span className={cn("font-mono tabular", period.positive ? "text-green-200" : "text-red-200")}>
                  {period.pct}
                </span>
              )}
            </button>
          );
        })}
        {/* Show selected period return */}
        {activePeriod && activePeriodData && (
          <span
            className={cn(
              "ml-auto text-xs font-mono tabular font-semibold",
              activePeriodData.pct != null
                ? (activePeriodData.positive ? "text-[var(--color-up)]" : "text-[var(--color-down)]")
                : "text-[var(--color-text-muted)]"
            )}
          >
            {activePeriodData.pct != null ? activePeriodData.pct : "--"}
            {activePeriodData.pct != null && (
              <span className="font-normal ml-1 text-[var(--color-text-muted)]">
                ({activePeriod})
              </span>
            )}
          </span>
        )}
      </div>
    </div>
  );
}

// ─── Top picks card ───────────────────────────────────────────────────────────

function TopPicksCard({
  picks,
  isLoading,
}: {
  picks: ReturnType<typeof useScreener>["data"] extends (infer T)[] | undefined ? T[] : never[];
  isLoading: boolean;
}) {
  return (
    <div
      className="rounded-2xl border overflow-hidden bg-[var(--color-bg-surface)] border-[var(--color-border)]"
    >
      {/* Header */}
      <div
        className="flex items-center justify-between px-5 py-4 border-b border-[var(--color-border)]"
      >
        <div className="flex items-center gap-2">
          <TrendingUp size={15} strokeWidth={1.5} className="text-[var(--color-up)]" />
          <span className="text-sm font-semibold text-[var(--color-text-primary)]">
            Starka köplägen
          </span>
          <InfoTooltip text="Aktier som systemet bedömer som de bästa köplägen just nu, baserat på betyg, trend och tekniska signaler." />
        </div>
        <Link
          href="/screener?entry_signal=STARK"
          className="flex items-center gap-1 text-xs transition-colors text-[var(--color-accent)]"
        >
          Visa alla <ArrowRight size={12} strokeWidth={1.5} />
        </Link>
      </div>

      {/* Rows */}
      <div>
        {isLoading
          ? Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="px-5 py-4 border-b last:border-b-0 flex items-center gap-3 border-[var(--color-border)]">
                <div className="skeleton h-4 w-20 rounded" />
                <div className="skeleton h-4 w-28 rounded" />
                <div className="skeleton h-4 w-12 rounded ml-auto" />
              </div>
            ))
          : picks.length === 0
          ? (
              <div className="px-5 py-8 text-center">
                <p className="text-sm text-[var(--color-text-muted)]">
                  Inga starka köplägen just nu
                </p>
              </div>
            )
          : picks.map((stock) => (
              <Link
                key={stock.ticker}
                href={`/aktie/${stock.ticker}`}
                className="flex items-center gap-3 px-5 py-4 border-b last:border-b-0
                           transition-colors hover:bg-[var(--color-bg-elevated)] group border-[var(--color-border)]"
              >
                {/* Ticker + name */}
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-semibold text-[var(--color-text-primary)] truncate">
                    {stock.name}
                  </div>
                  <div className="font-mono text-xs mt-0.5 text-[var(--color-text-muted)]">
                    {stock.ticker.replace(".ST", "")}
                  </div>
                </div>

                {/* Score badge */}
                <div
                  className={cn(
                    "text-xs font-mono font-bold px-2 py-0.5 rounded-md tabular",
                    (stock.score_total ?? 0) >= 70 ? "score-chip-high" : "score-chip-mid",
                  )}
                >
                  {formatScore(stock.score_total)}
                </div>

                {/* Change */}
                <div className="text-right">
                  <div className="font-mono tabular text-sm font-semibold text-[var(--color-text-primary)]">
                    {formatPrice(stock.price)}
                  </div>
                  <div className={cn("font-mono tabular text-xs", changeClass(stock.change_pct))}>
                    {formatPctChange(stock.change_pct)}
                  </div>
                </div>

                <ArrowRight
                  size={14}
                  strokeWidth={1.5}
                  className="shrink-0 opacity-0 group-hover:opacity-100 transition-opacity text-[var(--color-text-muted)]"
                />
              </Link>
            ))}
      </div>
    </div>
  );
}

// ─── Watchlist card ───────────────────────────────────────────────────────────

function WatchlistCard({ items }: { items: ReturnType<typeof useWatchlist>["data"] extends (infer T)[] | undefined ? T[] : never[] }) {
  return (
    <div
      className="rounded-2xl border overflow-hidden bg-[var(--color-bg-surface)] border-[var(--color-border)]"
    >
      {/* Header */}
      <div
        className="flex items-center justify-between px-5 py-4 border-b border-[var(--color-border)]"
      >
        <div className="flex items-center gap-2">
          <Star size={15} strokeWidth={1.5} className="text-[var(--color-warn)]" />
          <span className="text-sm font-semibold text-[var(--color-text-primary)]">
            Dina bevakningar
          </span>
          <InfoTooltip text="Aktier du följer. Få snabb överblick av dina bevakningar." />
        </div>
        <Link
          href="/bevakningar"
          className="flex items-center gap-1 text-xs text-[var(--color-accent)]"
        >
          Hantera <ArrowRight size={12} strokeWidth={1.5} />
        </Link>
      </div>

      {/* Rows */}
      <div>
        {items.length === 0
          ? (
              <div className="px-5 py-8 text-center space-y-2">
                <Star size={20} strokeWidth={1.5} style={{ color: "var(--color-border-strong)", margin: "0 auto" }} />
                <p className="text-sm text-[var(--color-text-muted)]">
                  Du bevakar inga aktier ännu
                </p>
                <Link
                  href="/bevakningar"
                  className="inline-flex items-center gap-1 text-xs text-[var(--color-accent)]"
                >
                  Lägg till en bevakning <ArrowRight size={11} strokeWidth={1.5} />
                </Link>
              </div>
            )
          : items.map((item) => {
              const TrendIcon =
                item.trend_signal === "Upptrend" ? TrendingUp :
                item.trend_signal === "Nedtrend" ? TrendingDown :
                Minus;

              return (
                <Link
                  key={item.ticker}
                  href={`/aktie/${item.ticker}`}
                  className="flex items-center gap-3 px-5 py-3.5 border-b last:border-b-0
                             transition-colors hover:bg-[var(--color-bg-elevated)] border-[var(--color-border)]"
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-semibold text-[var(--color-text-primary)] truncate max-w-40">
                        {item.name ?? item.ticker.replace(".ST", "")}
                      </span>
                      {item.entry_signal && (
                        <span className={cn("px-1.5 py-0.5 rounded text-[10px] font-medium",
                                            signalClass(item.entry_signal))}>
                          {signalLabel(item.entry_signal)}
                        </span>
                      )}
                    </div>
                    <div className="font-mono text-[11px] mt-0.5 text-[var(--color-text-muted)]">
                      {item.ticker.replace(".ST", "")}
                    </div>
                  </div>

                  {item.score_total != null && (
                    <span className={cn("font-mono text-xs font-bold tabular",
                                        scoreColorClass(item.score_total))}>
                      {formatScore(item.score_total)}
                    </span>
                  )}

                  <div className="text-right">
                    <div className="font-mono tabular text-xs text-[var(--color-text-primary)]">
                      {item.price != null ? formatPrice(item.price) : "—"}
                    </div>
                    {item.change_pct != null && (
                      <div className={cn("font-mono tabular text-[11px]", changeClass(item.change_pct))}>
                        {formatPctChange(item.change_pct)}
                      </div>
                    )}
                  </div>
                </Link>
              );
            })}
      </div>
    </div>
  );
}


// ─── Dagens marknad widget ──────────────────────────────────────────────

function DayMarketSection() {
  const { data: movers, isLoading } = useTopMovers();

  if (isLoading) return <div className="skeleton h-32 rounded-xl" />;
  if (!movers) return null;

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
      {/* Top movers */}
      <div className="rounded-xl border overflow-hidden bg-[var(--color-bg-surface)] border-[var(--color-border)]">
        <div className="flex items-center justify-between px-5 py-4 border-b border-[var(--color-border)]">
          <div className="flex items-center gap-2">
            <BarChart3 size={15} strokeWidth={1.5} className="text-[var(--color-accent)]" />
            <span className="text-sm font-semibold text-[var(--color-text-primary)]">
              Dagens marknad
            </span>
          </div>
        </div>
        <div className="divide-y divide-[var(--color-border)]">
          <div className="px-5 py-3">
            <div className="flex items-center gap-1.5 mb-2">
              <TrendingUp size={12} strokeWidth={1.5} className="text-[var(--color-up)]" />
              <span className="text-[11px] font-medium text-[var(--color-up)]">Störst upp</span>
            </div>
            {movers.up.slice(0, 3).map((m) => <MoverRow key={m.ticker} item={m} />)}
          </div>
          <div className="px-5 py-3">
            <div className="flex items-center gap-1.5 mb-2">
              <TrendingDown size={12} strokeWidth={1.5} className="text-[var(--color-down)]" />
              <span className="text-[11px] font-medium text-[var(--color-down)]">Störst ned</span>
            </div>
            {movers.down.slice(0, 3).map((m) => <MoverRow key={m.ticker} item={m} />)}
          </div>
        </div>
      </div>

      {/* Score winners/losers */}
      <div className="rounded-xl border overflow-hidden bg-[var(--color-bg-surface)] border-[var(--color-border)]">
        <div className="flex items-center justify-between px-5 py-4 border-b border-[var(--color-border)]">
          <div className="flex items-center gap-2">
            <Star size={15} strokeWidth={1.5} className="text-[var(--color-warn)]" />
            <span className="text-sm font-semibold text-[var(--color-text-primary)]">
              Betygsvinnare
            </span>
            <InfoTooltip text="Aktier med högst respektive lägst Marketscan-betyg just nu." />
          </div>
        </div>
        <div className="divide-y divide-[var(--color-border)]">
          <div className="px-5 py-3">
            <div className="text-[11px] font-medium text-[var(--color-up)] mb-2">Högst betyg</div>
            {movers.score_winners.slice(0, 3).map((m) => <MoverRow key={m.ticker} item={m} />)}
          </div>
          <div className="px-5 py-3">
            <div className="text-[11px] font-medium text-[var(--color-text-muted)] mb-2">Lägst betyg</div>
            {movers.score_losers.slice(0, 3).map((m) => <MoverRow key={m.ticker} item={m} />)}
          </div>
        </div>
      </div>
    </div>
  );
}

function MoverRow({ item }: { item: TopMover }) {
  return (
    <Link
      href={`/aktie/${item.ticker}`}
      className="flex items-center gap-2 py-1.5 group hover:bg-[var(--color-bg-elevated)] -mx-1 px-1 rounded transition-colors"
    >
      <div className="flex-1 min-w-0">
        <span className="text-xs font-medium text-[var(--color-text-primary)] truncate">
          {item.name ?? item.ticker}
        </span>
        <span className="font-mono text-[10px] text-[var(--color-text-muted)] ml-1">
          {item.ticker}
        </span>
      </div>
      {item.score_total != null && (
        <span className={cn("tabular text-xs font-mono", scoreColorClass(item.score_total))}>
          {formatScore(item.score_total)}
        </span>
      )}
      {item.change_pct != null && (
        <span className={cn("font-mono tabular text-xs w-16 text-right", changeClass(item.change_pct))}>
          {formatPctChange(item.change_pct)}
        </span>
      )}
    </Link>
  );
}