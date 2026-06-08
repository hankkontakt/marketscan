"use client";

import { useState, useMemo } from "react";
import Link from "next/link";
import { ArrowRight, TrendingUp, TrendingDown, Minus, Star, Globe, BarChart3, Search, LayoutDashboard, Sun, Moon } from "lucide-react";
import {
  AreaChart, Area, ResponsiveContainer, Tooltip as ReTooltip,
} from "recharts";
import { useScreener } from "@/hooks/useScreener";
import { usePortfolio, useWatchlist, usePortfolioHistory } from "@/hooks/usePortfolio";
import { InfoTooltip } from "@/components/ui/InfoTooltip";
import { useExperience, ExpertOnly } from "@/components/providers/ExperienceProvider";
import {
  formatPrice, formatPctChange, signalLabel, signalClass, signalBadgeClass,
  scoreColorClass, formatScore, changeClass, formatNumber,
} from "@/lib/format";
import { cn } from "@/lib/utils";
import { useGlobalIndices, GlobalIndexPanel, useTopMovers, type TopMover, useSectorOverview } from "@/hooks/useMarkets";

// ─── Tab definition ──────────────────────────────────────────────────────────

type OverviewTab = "portfolio" | "market" | "discover";

interface TabDef {
  id: OverviewTab;
  label: string;
  icon: React.ElementType;
  beginner: boolean;
}

const TABS: TabDef[] = [
  { id: "portfolio", label: "Portfölj", icon: LayoutDashboard, beginner: true },
  { id: "market", label: "Marknad", icon: Globe, beginner: true },
  { id: "discover", label: "Hitta aktier", icon: Search, beginner: true },
];

// ─── Main view ────────────────────────────────────────────────────────────────

export function OversiktView() {
  const [activeTab, setActiveTab] = useState<OverviewTab>("portfolio");
  const { level } = useExperience();

  const { data: portfolio } = usePortfolio();
  const { data: watchlist = [] } = useWatchlist();
  const holdings = portfolio?.holdings ?? [];
  const hasPortfolio = holdings.length > 0;

  // Weekday greeting
  const now = new Date();
  const hour = now.getHours();
  const greeting = hour < 10 ? "God morgon" : hour < 13 ? "Hej" : hour < 18 ? "God eftermiddag" : "God kväll";
  const dateStr = now.toLocaleDateString("sv-SE", {
    weekday: "long", day: "numeric", month: "long",
  });

  return (
    <div className="max-w-4xl mx-auto space-y-5 pb-12">
      {/* ── Greeting ─────────────────────────────────────── */}
      <div className="flex items-baseline justify-between pt-2">
        <h1 className="text-xl font-semibold text-[var(--color-text-primary)]">
          {greeting}
        </h1>
        <span className="text-sm capitalize text-[var(--color-text-muted)]">
          {dateStr}
        </span>
      </div>

      {/* ── Tab bar ──────────────────────────────────────── */}
      <div className="flex gap-1 p-1 rounded-xl bg-[var(--color-bg-elevated)]">
        {TABS.filter((t) => t.beginner || level === "expert").map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={cn(
              "flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium transition-colors flex-1 justify-center",
              activeTab === tab.id
                ? "bg-[var(--color-bg-surface)] text-[var(--color-accent)] shadow-sm"
                : "text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]",
            )}
          >
            <tab.icon size={14} strokeWidth={1.5} />
            {tab.label}
          </button>
        ))}
      </div>

      {/* ── Tab: Portfolio ───────────────────────────────── */}
      {activeTab === "portfolio" && (
        <TabPortfolio hasPortfolio={hasPortfolio} holdings={holdings} portfolio={portfolio} />
      )}

      {/* ── Tab: Market ──────────────────────────────────── */}
      {activeTab === "market" && <TabMarket />}

      {/* ── Tab: Discover ────────────────────────────────── */}
      {activeTab === "discover" && <TabDiscover />}
    </div>
  );
}

// ─── Tab: Portfolio ────────────────────────────────────────────────────────────

function TabPortfolio({ hasPortfolio, holdings, portfolio }: {
  hasPortfolio: boolean;
  holdings: any[];
  portfolio: any;
}) {
  const PERIOD_LABELS = ["1M", "3M", "6M", "12M"];
  const { data: history } = usePortfolioHistory();
  const [selectedPeriod, setSelectedPeriod] = useState("6M");

  const totalValue = useMemo(
    () => holdings.reduce((s: number, h: any) => s + (h.price ?? 0) * h.shares, 0),
    [holdings]
  );
  const totalCost = useMemo(
    () => holdings.reduce((s: number, h: any) => s + (h.cost_basis ?? 0) * h.shares, 0),
    [holdings]
  );
  const todayChange = useMemo(
    () => holdings.reduce((s: number, h: any) => s + (h.change_pct ?? 0) * (h.price ?? 0) * h.shares, 0),
    [holdings]
  );
  const totalReturn = totalCost > 0 ? (totalValue - totalCost) / totalCost : null;

  const periods = PERIOD_LABELS.map((label) => {
    const apiPeriod = history?.periods?.[label];
    if (apiPeriod?.pct != null) {
      const sign = apiPeriod.pct >= 0 ? "+" : "";
      return { label, pct: `${sign}${apiPeriod.pct.toFixed(1).replace(".", ",")} %`, positive: apiPeriod.positive ?? apiPeriod.pct >= 0 };
    }
    return { label, pct: null, positive: null };
  });

  if (!hasPortfolio) {
    return (
      <div className="rounded-2xl border p-8 bg-[var(--color-bg-surface)] border-[var(--color-border)] text-center">
        <LayoutDashboard size={32} strokeWidth={1.5} className="mx-auto mb-3 text-[var(--color-text-muted)]" />
        <h2 className="text-base font-semibold text-[var(--color-text-primary)] mb-1">Välkommen till MarketScan</h2>
        <p className="text-sm text-[var(--color-text-secondary)] mb-4 max-w-sm mx-auto">
          Lägg till dina första aktier för att se din portföljöversikt, eller importera från Avanza.
        </p>
        <div className="flex items-center justify-center gap-3">
          <Link
            href="/portfolj"
            className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium text-white bg-[var(--color-accent)]"
          >
            <TrendingUp size={14} strokeWidth={1.5} />
            Gå till portföljen
          </Link>
          <Link
            href="/screener"
            className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium border border-[var(--color-border)] text-[var(--color-text-secondary)]"
          >
            <Search size={14} strokeWidth={1.5} />
            Utforska aktier
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-2xl border p-5 bg-[var(--color-bg-surface)] border-[var(--color-border)]">
      {/* Value */}
      <div className="flex items-start justify-between mb-4">
        <div>
          <div className="flex items-center gap-1 mb-1">
            <span className="text-xs text-[var(--color-text-muted)]">Portföljvärde</span>
            <InfoTooltip text="Det totala marknadsvärdet på alla dina aktieinnehav just nu." />
          </div>
          <div className="text-2xl font-bold font-mono tabular tracking-tight text-[var(--color-text-primary)]">
            {formatPrice(totalValue)}
          </div>
          {totalReturn != null && (
            <div className={cn("flex items-center gap-1 mt-1 text-xs font-mono tabular font-medium", changeClass(totalReturn))}>
              {formatPctChange(totalReturn)}
              <span className="text-[var(--color-text-muted)] font-normal">total avkastning</span>
            </div>
          )}
        </div>
        <div className="text-right">
          <div className="flex items-center gap-1 justify-end mb-0.5">
            <span className="text-xs text-[var(--color-text-muted)]">Idag</span>
          </div>
          <div className={cn("font-mono tabular text-sm font-medium", totalValue > 0 ? changeClass(todayChange / totalValue || 0) : "")}>
            {todayChange >= 0 ? "+" : ""}{formatPrice(todayChange)}
          </div>
        </div>
      </div>

      {/* Period selector */}
      <div className="flex items-center gap-2 mb-4">
        <span className="text-xs text-[var(--color-text-muted)]">Avkastning</span>
        {periods.map((p) => {
          const active = p.label === selectedPeriod;
          return (
            <button
              key={p.label}
              onClick={() => setSelectedPeriod(p.label)}
              className={cn(
                "px-2.5 py-1 rounded-lg text-xs font-medium transition-all",
                active ? "bg-[var(--color-accent)] text-white" : "hover:bg-[var(--color-bg-elevated)] text-[var(--color-text-muted)]",
              )}
            >
              {p.label}
              {active && p.pct && (
                <span className={cn("ml-1 font-mono", p.positive ? "text-green-200" : "text-red-200")}>{p.pct}</span>
              )}
            </button>
          );
        })}
      </div>

      {/* Holdings summary */}
      <div className="space-y-1">
        {holdings.slice(0, 5).map((h: any) => (
          <Link
            key={h.id}
            href={`/aktie/${h.ticker}`}
            className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-[var(--color-bg-elevated)] transition-colors"
          >
            <div className="flex-1 min-w-0 flex items-center gap-2">
              <span className="text-xs font-medium text-[var(--color-text-primary)] truncate">{h.name || h.ticker}</span>
              <span className="font-mono text-[10px] text-[var(--color-text-muted)]">{h.ticker}</span>
            </div>
            <span className="text-xs font-mono tabular text-[var(--color-text-secondary)]">
              {formatPrice((h.price ?? 0) * h.shares)}
            </span>
            <span className={cn("font-mono tabular text-xs w-14 text-right", changeClass(h.change_pct))}>
              {formatPctChange(h.change_pct)}
            </span>
          </Link>
        ))}
      </div>

      {holdings.length > 5 && (
        <Link href="/portfolj" className="flex items-center justify-center gap-1 mt-2 py-2 text-xs text-[var(--color-accent)]">
          Visa alla {holdings.length} innehav <ArrowRight size={12} strokeWidth={1.5} />
        </Link>
      )}
    </div>
  );
}

// ─── Tab: Market ────────────────────────────────────────────────────────────────

function TabMarket() {
  const { data: markets } = useGlobalIndices();
  const { data: movers, isLoading: moversLoading } = useTopMovers();
  const { level } = useExperience();
  const isExpert = level === "expert";

  return (
    <div className="space-y-5">
      {/* Global indices */}
      {markets?.indices && markets.indices.length > 0 && (
        <div className="rounded-xl border p-4 bg-[var(--color-bg-surface)] border-[var(--color-border)]">
          <div className="flex items-center gap-2 mb-3">
            <Globe size={14} strokeWidth={1.5} className="text-[var(--color-accent)]" />
            <span className="text-xs font-semibold text-[var(--color-text-primary)]">Globala index</span>
            <Link href="/marknad" className="ml-auto flex items-center gap-1 text-[10px] text-[var(--color-accent)]">
              Visa alla <ArrowRight size={11} strokeWidth={1.5} />
            </Link>
          </div>
          <GlobalIndexPanel indices={markets.indices} />
        </div>
      )}

      {/* Top movers */}
      {movers && !moversLoading && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="rounded-xl border overflow-hidden bg-[var(--color-bg-surface)] border-[var(--color-border)]">
            <div className="flex items-center gap-2 px-4 py-3 border-b border-[var(--color-border)]">
              <BarChart3 size={14} strokeWidth={1.5} className="text-[var(--color-accent)]" />
              <span className="text-xs font-semibold text-[var(--color-text-primary)]">Dagens marknad</span>
            </div>
            <div className="px-4 py-3">
              {movers.up.length === 0 && movers.down.length === 0 ? (
                <p className="text-[11px] text-[var(--color-text-muted)] text-center py-3">
                  Ingen prisdata för idag — kör pipeline för att uppdatera.
                </p>
              ) : (
                <>
                  <div className="flex items-center gap-1 mb-2">
                    <TrendingUp size={11} strokeWidth={1.5} className="text-[var(--color-up)]" />
                    <span className="text-[10px] font-medium text-[var(--color-up)]">Störst upp</span>
                  </div>
                  {movers.up.slice(0, isExpert ? 5 : 3).map((m: TopMover) => <MoverRow key={m.ticker} item={m} />)}
                  <div className="flex items-center gap-1 mt-3 mb-2">
                    <TrendingDown size={11} strokeWidth={1.5} className="text-[var(--color-down)]" />
                    <span className="text-[10px] font-medium text-[var(--color-down)]">Störst ned</span>
                  </div>
                  {movers.down.slice(0, isExpert ? 5 : 3).map((m: TopMover) => <MoverRow key={m.ticker} item={m} />)}
                </>
              )}
            </div>
          </div>

          <div className="rounded-xl border overflow-hidden bg-[var(--color-bg-surface)] border-[var(--color-border)]">
            <div className="flex items-center gap-2 px-4 py-3 border-b border-[var(--color-border)]">
              <Star size={14} strokeWidth={1.5} className="text-[var(--color-warn)]" />
              <span className="text-xs font-semibold text-[var(--color-text-primary)]">Betygsvinnare</span>
              <InfoTooltip text="Aktier med högst respektive lägst Marketscan-betyg just nu." />
            </div>
            <div className="px-4 py-3">
              <div className="text-[10px] font-medium text-[var(--color-up)] mb-2">Högst betyg</div>
              {movers.score_winners.slice(0, 3).map((m: TopMover) => <MoverRow key={m.ticker} item={m} />)}
              <div className="text-[10px] font-medium text-[var(--color-text-muted)] mt-3 mb-2">Lägst betyg</div>
              {movers.score_losers.slice(0, 3).map((m: TopMover) => <MoverRow key={m.ticker} item={m} />)}
            </div>
          </div>
        </div>
      )}

      {moversLoading && <div className="skeleton h-32 rounded-xl" />}
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
        <span className="font-mono text-[10px] text-[var(--color-text-muted)] ml-1">{item.ticker}</span>
      </div>
      {item.score_total != null && (
        <span className={cn("tabular text-xs font-mono", scoreColorClass(item.score_total))}>
          {formatScore(item.score_total)}
        </span>
      )}
      {item.change_pct != null && (
        <span className={cn("font-mono tabular text-xs w-14 text-right", changeClass(item.change_pct))}>
          {formatPctChange(item.change_pct)}
        </span>
      )}
    </Link>
  );
}

// ─── Tab: Discover ──────────────────────────────────────────────────────────────

function TabDiscover() {
  const { data: topPicks = [], isLoading: picksLoading } = useScreener({
    segments: ["large_cap", "mid_cap", "small_cap", "micro_cap"],
    entry_signal: "STARK",
    score_min: 60,
    limit: 5,
  });

  return (
    <div className="space-y-4">
      {/* Top picks */}
      <div className="rounded-xl border overflow-hidden bg-[var(--color-bg-surface)] border-[var(--color-border)]">
        <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--color-border)]">
          <div className="flex items-center gap-2">
            <TrendingUp size={14} strokeWidth={1.5} className="text-[var(--color-up)]" />
            <span className="text-xs font-semibold text-[var(--color-text-primary)]">Starka köplägen</span>
            <InfoTooltip text="Aktier med starkast köpläge just nu baserat på betyg, trend och tekniska signaler." />
          </div>
          <Link href="/screener?entry_signal=STARK" className="flex items-center gap-1 text-xs text-[var(--color-accent)]">
            Visa alla <ArrowRight size={11} strokeWidth={1.5} />
          </Link>
        </div>
        <div>
          {picksLoading
            ? Array.from({ length: 3 }).map((_, i) => (
                <div key={i} className="px-4 py-3 border-b last:border-b-0 flex items-center gap-3 border-[var(--color-border)]">
                  <div className="skeleton h-4 w-20 rounded" />
                  <div className="skeleton h-4 w-12 rounded ml-auto" />
                </div>
              ))
            : topPicks.length === 0
            ? <div className="px-4 py-6 text-center text-xs text-[var(--color-text-muted)]">Inga starka köplägen just nu</div>
            : topPicks.map((stock: any) => (
                <Link
                  key={stock.ticker}
                  href={`/aktie/${stock.ticker}`}
                  className="flex items-center gap-3 px-4 py-3 border-b last:border-b-0 transition-colors hover:bg-[var(--color-bg-elevated)] border-[var(--color-border)]"
                >
                  <div className="flex-1 min-w-0">
                    <div className="text-xs font-semibold text-[var(--color-text-primary)] truncate">{stock.name}</div>
                    <div className="font-mono text-[10px] text-[var(--color-text-muted)]">{stock.ticker.replace(".ST", "")}</div>
                  </div>
                  <span className={cn("text-xs font-mono font-bold px-2 py-0.5 rounded tabular", (stock.score_total ?? 0) >= 70 ? "score-chip-high" : "score-chip-mid")}>
                    {formatScore(stock.score_total)}
                  </span>
                  <div className="text-right">
                    <div className="font-mono tabular text-xs text-[var(--color-text-primary)]">{formatPrice(stock.price)}</div>
                    <div className={cn("font-mono tabular text-[10px]", changeClass(stock.change_pct))}>{formatPctChange(stock.change_pct)}</div>
                  </div>
                </Link>
              ))}
        </div>
      </div>

      {/* Quick links */}
      <div className="grid grid-cols-2 gap-3">
        <Link
          href="/screener"
          className="rounded-xl border p-4 bg-[var(--color-bg-surface)] border-[var(--color-border)] hover:shadow-sm transition-shadow"
        >
          <Search size={16} strokeWidth={1.5} className="text-[var(--color-accent)] mb-2" />
          <span className="text-xs font-semibold text-[var(--color-text-primary)]">Screener</span>
          <p className="text-[10px] text-[var(--color-text-muted)] mt-1">Filtrera bland alla aktier</p>
        </Link>
        <Link
          href="/jamfor"
          className="rounded-xl border p-4 bg-[var(--color-bg-surface)] border-[var(--color-border)] hover:shadow-sm transition-shadow"
        >
          <BarChart3 size={16} strokeWidth={1.5} className="text-[var(--color-accent)] mb-2" />
          <span className="text-xs font-semibold text-[var(--color-text-primary)]">Jämför aktier</span>
          <p className="text-[10px] text-[var(--color-text-muted)] mt-1">Jämför betyg, nyckeltal och pris</p>
        </Link>
      </div>
    </div>
  );
}
