"use client";

import { useMemo } from "react";
import Link from "next/link";
import {
  TrendingUp, TrendingDown, Users, Activity, Globe,
  ArrowRight, Briefcase, Radio,
} from "lucide-react";
import { useScreener } from "@/hooks/useScreener";
import { useScoreMovers } from "@/hooks/useAlerts";
import { useInsiderRadar } from "@/hooks/useStrategies";
import { useMacroRegime, useSectorOverview, useGlobalIndices } from "@/hooks/useMarkets";
import { usePortfolio, usePortfolioHistory, useFundHoldings } from "@/hooks/usePortfolio";
import { cn } from "@/lib/utils";
import {
  formatPrice, scoreColorClass, formatScore,
  changeClass, formatPctChange, signalBadgeClass, signalShortLabel,
} from "@/lib/format";
import type { ScanRow } from "@/types/scan";
import type { ScoreMover } from "@/types/alerts";
import { RegimeGauge } from "@/components/widgets/RegimeGauge";
import { RiskGauge } from "@/components/widgets/RiskGauge";
import { WatchlistStrip } from "@/components/widgets/WatchlistStrip";
import { MewsStrip } from "@/components/widgets/MewsStrip";
import { PortfolioCoachCard } from "@/components/widgets/PortfolioCoachCard";

// ─── helpers ──────────────────────────────────────────────────────────────

function fmt(v: number) {
  if (v >= 1_000_000) return `${(v / 1_000_000).toFixed(1)} M`;
  if (v >= 1_000)     return `${(v / 1_000).toFixed(0)} k`;
  return v.toFixed(0);
}

function fmtPct(v: number | null | undefined): string {
  if (v == null) return "—";
  const sign = v >= 0 ? "+" : "";
  return `${sign}${v.toFixed(1).replace(".", ",")} %`;
}

// ─── Portfolio hero ────────────────────────────────────────────────────────

function PortfolioHero() {
  const { data: portfolio, isLoading: loadingPortfolio } = usePortfolio();
  const { data: funds = [],  isLoading: loadingFunds }    = useFundHoldings();
  const { data: history,     isLoading: loadingHistory }  = usePortfolioHistory();

  const holdings = portfolio?.holdings ?? [];

  const stockValue = useMemo(
    () => holdings.reduce((s, h) => s + h.shares * (h.price ?? 0), 0),
    [holdings],
  );
  const fundValue  = useMemo(
    () => funds.reduce((s, f) => s + (f.current_value ?? 0), 0),
    [funds],
  );
  const totalValue = stockValue + fundValue;

  const totalCost = useMemo(
    () => holdings.reduce((s, h) => s + h.shares * (h.cost_basis ?? 0), 0),
    [holdings],
  );
  const totalReturn = totalCost > 0 ? (stockValue - totalCost) / totalCost : null;

  // Today's change in kr (stocks only — fund change_pct not available)
  const todayKr = useMemo(
    () => holdings.reduce((s, h) => s + (h.change_pct ?? 0) / 100 * h.shares * (h.price ?? 0), 0),
    [holdings],
  );
  const todayPct = totalValue > 0 ? (todayKr / totalValue) * 100 : null;

  const hasPortfolio = holdings.length > 0 || funds.length > 0;

  const PERIODS = ["1M", "3M", "6M", "12M"] as const;

  const isLoading = loadingPortfolio || loadingFunds;

  // ── No portfolio: show market hero instead ──────────────────────────────
  if (!isLoading && !hasPortfolio) return <MarketHero />;

  return (
    <div className="relative rounded-2xl overflow-hidden bg-[var(--color-accent)] text-white px-6 pt-7 pb-6">
      {/* Subtle radial glow for depth */}
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,rgba(255,255,255,0.07)_0%,transparent_60%)]" />

      {isLoading ? (
        <div className="animate-pulse space-y-3">
          <div className="h-4 w-28 bg-white/20 rounded-full" />
          <div className="h-10 w-48 bg-white/20 rounded-xl" />
          <div className="h-4 w-36 bg-white/20 rounded-full" />
        </div>
      ) : (
        <>
          {/* Main numbers */}
          <p className="text-sm text-white/70 mb-1 font-medium">Portföljvärde</p>
          <div className="flex items-end gap-4 flex-wrap">
            <span className="text-4xl font-bold tracking-tight font-mono tabular">
              {formatPrice(totalValue)}
            </span>
            {todayPct != null && (
              <span className={cn(
                "text-base font-semibold font-mono tabular mb-1",
                todayKr >= 0 ? "text-green-300" : "text-red-300",
              )}>
                {todayKr >= 0 ? "+" : ""}{formatPrice(todayKr).replace(" kr", "")} kr
                {" "}({fmtPct(todayPct)})
              </span>
            )}
          </div>

          {totalReturn != null && (
            <p className="text-sm text-white/60 mt-1 font-mono tabular">
              {fmtPct(totalReturn * 100)} total avkastning
            </p>
          )}

          {/* Period returns row */}
          {!loadingHistory && history && (
            <div className="flex flex-wrap items-center gap-2 mt-5">
              {PERIODS.map((p) => {
                const period = history.periods?.[p];
                const pct    = period?.pct;
                const pos    = period?.positive ?? (pct != null ? pct >= 0 : null);
                return (
                  <span
                    key={p}
                    className={cn(
                      "px-3 py-1 rounded-full text-xs font-semibold font-mono tabular",
                      pct == null
                        ? "bg-white/10 text-white/40"
                        : pos
                        ? "bg-green-500/20 text-green-200"
                        : "bg-red-500/20 text-red-300",
                    )}
                  >
                    {p} {pct != null ? fmtPct(pct) : "—"}
                  </span>
                );
              })}
              <Link
                href="/portfolj"
                className="ml-auto flex items-center gap-1 text-xs text-white/70 hover:text-white transition-colors"
              >
                Visa portfölj <ArrowRight size={12} strokeWidth={1.5} />
              </Link>
            </div>
          )}
        </>
      )}
    </div>
  );
}

// ─── Market hero — shown when user has no portfolio ────────────────────────

function MarketHero() {
  const { data: indicesData, isLoading } = useGlobalIndices();
  const indices = indicesData?.indices ?? [];
  const { data: regime }                  = useMacroRegime();

  return (
    <div className="relative rounded-2xl overflow-hidden bg-[var(--color-accent)] text-white px-6 py-6">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,rgba(255,255,255,0.07)_0%,transparent_60%)]" />

      <div className="flex flex-col sm:flex-row sm:items-center gap-4 justify-between">
        <div>
          <p className="text-sm text-white/70 font-medium mb-1">Marknadsöversikt</p>
          {regime && (
            <span className="text-lg font-semibold">{regime.label}</span>
          )}
        </div>

        <div className="flex gap-5 flex-wrap">
          {isLoading
            ? [1, 2, 3].map(i => (
                <div key={i} className="animate-pulse space-y-1">
                  <div className="h-3 w-16 bg-white/20 rounded" />
                  <div className="h-5 w-12 bg-white/20 rounded" />
                </div>
              ))
            : indices.slice(0, 4).map(idx => (
                <div key={idx.name} className="text-right">
                  <p className="text-xs text-white/60">{idx.name}</p>
                  <p className={cn(
                    "text-sm font-semibold font-mono tabular",
                    idx.change_pct == null ? "text-white/60"
                    : idx.change_pct >= 0  ? "text-green-300"
                    : "text-red-300",
                  )}>
                    {idx.change_pct != null ? fmtPct(idx.change_pct) : "—"}
                  </p>
                </div>
              ))
          }
        </div>
      </div>

      <p className="mt-4 text-xs text-white/60">
        Lägg till aktier i din{" "}
        <Link href="/portfolj" className="text-white/90 underline underline-offset-2 hover:text-white">
          portfölj
        </Link>{" "}
        för att se din personliga avkastning här.
      </p>
    </div>
  );
}

// ─── Stat card ─────────────────────────────────────────────────────────────

function StatCard({
  icon: Icon, label, value, sub, positive, href,
}: {
  icon: React.ElementType;
  label: string;
  value: React.ReactNode;
  sub?: string;
  positive?: boolean | null;
  href?: string;
}) {
  const content = (
    <div className="rounded-xl border bg-[var(--color-bg-surface)] border-[var(--color-border)] p-4
                    hover:border-[var(--color-border-strong)] transition-colors h-full">
      <div className="flex items-center gap-1.5 mb-2">
        <Icon size={13} strokeWidth={1.5} className="text-[var(--color-text-muted)]" />
        <span className="text-[11px] text-[var(--color-text-muted)] font-medium uppercase tracking-wide">{label}</span>
      </div>
      <p className={cn(
        "text-xl font-bold font-mono tabular tracking-tight",
        positive === true  ? "text-[var(--color-up)]"
        : positive === false ? "text-[var(--color-down)]"
        : "text-[var(--color-text-primary)]",
      )}>
        {value}
      </p>
      {sub && (
        <p className="text-xs text-[var(--color-text-muted)] mt-0.5">{sub}</p>
      )}
    </div>
  );

  return href ? <Link href={href}>{content}</Link> : content;
}

// ─── Section card ──────────────────────────────────────────────────────────

function SectionCard({
  title, icon: Icon, iconColor = "text-[var(--color-text-muted)]",
  action, children, isLoading, empty, emptyText,
}: {
  title: string;
  icon: React.ElementType;
  iconColor?: string;
  action?: { label: string; href: string };
  children: React.ReactNode;
  isLoading?: boolean;
  empty?: boolean;
  emptyText?: string;
}) {
  return (
    <div className="rounded-xl border bg-[var(--color-bg-surface)] border-[var(--color-border)] flex flex-col overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--color-border)]">
        <div className="flex items-center gap-2">
          <Icon size={14} strokeWidth={1.5} className={iconColor} />
          <h2 className="text-sm font-semibold text-[var(--color-text-primary)]">{title}</h2>
        </div>
        {action && (
          <Link
            href={action.href}
            className="flex items-center gap-1 text-[11px] text-[var(--color-text-muted)] hover:text-[var(--color-accent)] transition-colors"
          >
            {action.label}
            <ArrowRight size={10} strokeWidth={1.5} />
          </Link>
        )}
      </div>

      {/* Body */}
      <div className="flex-1 px-1 py-1">
        {isLoading ? (
          <div className="space-y-1 p-2">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="h-9 rounded-lg skeleton" />
            ))}
          </div>
        ) : empty ? (
          <p className="flex items-center justify-center py-8 text-xs text-[var(--color-text-muted)]">
            {emptyText ?? "Ingen data tillgänglig"}
          </p>
        ) : children}
      </div>
    </div>
  );
}

// ─── Stock row ─────────────────────────────────────────────────────────────

function StockRow({ stock }: { stock: ScanRow }) {
  return (
    <Link
      href={`/aktie/${stock.ticker}`}
      className="flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-[var(--color-bg-elevated)] transition-colors group"
    >
      <div className="min-w-0 flex-1">
        <span className="text-sm font-semibold text-[var(--color-text-primary)] group-hover:text-[var(--color-accent)] transition-colors">
          {stock.ticker}
        </span>
        {stock.name && (
          <span className="ml-2 text-xs text-[var(--color-text-muted)] truncate hidden sm:inline max-w-[100px]">
            {stock.name}
          </span>
        )}
      </div>
      <div className="flex items-center gap-2 shrink-0">
        {stock.score_total != null && (
          <span className={cn("text-xs font-bold tabular font-mono", scoreColorClass(stock.score_total))}>
            {formatScore(stock.score_total)}
          </span>
        )}
        <span className={cn("text-[10px] font-medium px-1.5 py-0.5 rounded-md", signalBadgeClass(stock.entry_signal))}>
          {signalShortLabel(stock.entry_signal)}
        </span>
      </div>
    </Link>
  );
}

// ─── Mover row ─────────────────────────────────────────────────────────────

function MoverRow({ mover, direction }: { mover: ScoreMover; direction: "up" | "down" }) {
  const isUp = direction === "up";
  return (
    <Link
      href={`/aktie/${mover.ticker}`}
      className="flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-[var(--color-bg-elevated)] transition-colors group"
    >
      <div className="min-w-0 flex-1">
        <span className="text-sm font-semibold text-[var(--color-text-primary)] group-hover:text-[var(--color-accent)] transition-colors">
          {mover.ticker}
        </span>
        {mover.name && (
          <span className="ml-2 text-xs text-[var(--color-text-muted)] truncate hidden sm:inline max-w-[80px]">
            {mover.name}
          </span>
        )}
      </div>
      <span className={cn(
        "text-sm font-bold tabular font-mono shrink-0",
        isUp ? "text-[var(--color-up)]" : "text-[var(--color-down)]",
      )}>
        {isUp ? "+" : ""}{mover.score_change.toFixed(1)}
      </span>
    </Link>
  );
}

// ─── Main view ─────────────────────────────────────────────────────────────

export function DagligBriefingView() {
  // Data
  const { data: starkStocks = [],  isLoading: loadingStark }    = useScreener({
    segments: ["large_cap", "mid_cap", "small_cap", "micro_cap"],
    entry_signal: "STARK",
    limit: 7,
  });
  const { data: moversUp   = [],  isLoading: loadingUp }         = useScoreMovers(7, "up",   5);
  const { data: moversDown = [],  isLoading: loadingDown }       = useScoreMovers(7, "down", 5);
  const { data: insiders   = [],  isLoading: loadingInsiders }   = useInsiderRadar(14, "buy");
  const { data: regime,           isLoading: loadingRegime }     = useMacroRegime();
  const { data: sectorData,       isLoading: loadingSectors }    = useSectorOverview();
  const { data: indicesData }                                     = useGlobalIndices();
  const indices = indicesData?.indices ?? [];

  // Computed
  const topInsiders = insiders.slice(0, 5);
  const topSectors  = sectorData?.sectors
    ? [...sectorData.sectors].sort((a, b) => b.avg_score - a.avg_score).slice(0, 5)
    : [];

  // OMX + S&P for stat cards
  const omx = indices.find(i => i.name.toLowerCase().includes("omx") || i.name === "OMX30");
  const sp  = indices.find(i => i.name.includes("S&P") || i.name.includes("500"));

  const REGIME_COLORS: Record<string, string> = {
    green:   "text-[var(--color-up)]",
    red:     "text-[var(--color-down)]",
    amber:   "text-[var(--color-warn)]",
    neutral: "text-[var(--color-text-secondary)]",
  };
  const regimeColor = REGIME_COLORS[regime?.color ?? "neutral"];

  return (
    <div className="space-y-5 max-w-6xl">

      {/* ── Hero ─────────────────────────────────────────────────── */}
      <PortfolioHero />

      {/* ── Stat chips ───────────────────────────────────────────── */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {/* Marknadsläge */}
        <StatCard
          icon={Radio}
          label="Marknadsläge"
          value={loadingRegime ? "…" : (regime?.label ?? "—")}
          sub={regime?.regime}
          positive={regime?.color === "green" ? true : regime?.color === "red" ? false : null}
          href="/marknad"
        />

        {/* STARK count */}
        <StatCard
          icon={TrendingUp}
          label="STARK-aktier"
          value={loadingStark ? "…" : `${starkStocks.length} st`}
          sub="idag"
          href="/screener?entry_signal=STARK"
        />

        {/* OMX */}
        {omx ? (
          <StatCard
            icon={Globe}
            label={omx.name}
            value={omx.change_pct != null ? fmtPct(omx.change_pct) : "—"}
            sub="idag"
            positive={omx.change_pct != null ? omx.change_pct >= 0 : null}
          />
        ) : (
          <StatCard icon={Globe} label="OMX30" value="—" />
        )}

        {/* S&P */}
        {sp ? (
          <StatCard
            icon={Activity}
            label={sp.name}
            value={sp.change_pct != null ? fmtPct(sp.change_pct) : "—"}
            sub="idag"
            positive={sp.change_pct != null ? sp.change_pct >= 0 : null}
          />
        ) : (
          <StatCard icon={Activity} label="S&P 500" value="—" />
        )}
      </div>

      {/* ── Personligt: bevakningar + risk/regim ─────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-5">
        <div className="lg:col-span-3">
          <WatchlistStrip />
        </div>
        <div className="lg:col-span-2 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-1 gap-5">
          <RegimeGauge />
          <RiskGauge />
        </div>
      </div>

      {/* ── Portföljcoach ────────────────────────────────────────── */}
      <PortfolioCoachCard />

      {/* ── Mångdubblar-kandidater ───────────────────────────────── */}
      <MewsStrip />

      {/* ── Main grid ────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-5">

        {/* Left column — 2/5 */}
        <div className="lg:col-span-2 space-y-5">

          <SectionCard
            title="Toppaktier idag"
            icon={TrendingUp}
            iconColor="text-[var(--color-up)]"
            action={{ label: "Visa alla", href: "/screener?entry_signal=STARK" }}
            isLoading={loadingStark}
            empty={starkStocks.length === 0}
            emptyText="Inga STARK-aktier just nu"
          >
            {starkStocks.map(s => <StockRow key={s.ticker} stock={s} />)}
          </SectionCard>

          <SectionCard
            title="Insiderköp (14 dagar)"
            icon={Users}
            iconColor="text-[var(--color-accent)]"
            action={{ label: "Insider Radar", href: "/insider-radar" }}
            isLoading={loadingInsiders}
            empty={topInsiders.length === 0}
            emptyText="Ingen registrerad insiderhandel"
          >
            {topInsiders.map(cluster => (
              <Link
                key={cluster.ticker}
                href={`/aktie/${cluster.ticker}`}
                className="flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-[var(--color-bg-elevated)] transition-colors group"
              >
                <div className="min-w-0 flex-1">
                  <span className="text-sm font-semibold text-[var(--color-text-primary)] group-hover:text-[var(--color-accent)] transition-colors">
                    {cluster.ticker}
                  </span>
                  {cluster.name && (
                    <span className="ml-2 text-xs text-[var(--color-text-muted)] truncate hidden sm:inline max-w-[80px]">
                      {cluster.name}
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-1.5 shrink-0 text-xs">
                  <span className="text-[var(--color-text-muted)]">{cluster.unique_insiders} ins.</span>
                  <span className="font-medium text-[var(--color-accent)] font-mono tabular">
                    {fmt(cluster.total_amount)} kr
                  </span>
                </div>
              </Link>
            ))}
          </SectionCard>
        </div>

        {/* Right column — 3/5 */}
        <div className="lg:col-span-3 space-y-5">

          {/* Score movers: side by side */}
          <div className="grid grid-cols-2 gap-5">
            <SectionCard
              title="Stigande betyg"
              icon={TrendingUp}
              iconColor="text-[var(--color-up)]"
              action={{ label: "Signalanalys", href: "/signal-analytics" }}
              isLoading={loadingUp}
              empty={(moversUp as ScoreMover[]).length === 0}
              emptyText="Inga tydliga rörelser"
            >
              {(moversUp as ScoreMover[]).map(m => (
                <MoverRow key={m.ticker} mover={m} direction="up" />
              ))}
            </SectionCard>

            <SectionCard
              title="Sjunkande betyg"
              icon={TrendingDown}
              iconColor="text-[var(--color-down)]"
              isLoading={loadingDown}
              empty={(moversDown as ScoreMover[]).length === 0}
              emptyText="Inga tydliga rörelser"
            >
              {(moversDown as ScoreMover[]).map(m => (
                <MoverRow key={m.ticker} mover={m} direction="down" />
              ))}
            </SectionCard>
          </div>

          {/* Sectors */}
          <SectionCard
            title="Sektorer — snittbetyg"
            icon={Globe}
            iconColor="text-[var(--color-text-muted)]"
            action={{ label: "Komplett vy", href: "/marknad" }}
            isLoading={loadingSectors}
            empty={topSectors.length === 0}
            emptyText="Sektordata ej tillgänglig"
          >
            <div className="px-3 py-2 space-y-3">
              {topSectors.map(s => (
                <div key={s.sector}>
                  <div className="flex items-center justify-between mb-1">
                    <Link
                      href={`/screener?sector=${encodeURIComponent(s.sector)}`}
                      className="text-xs font-medium text-[var(--color-text-primary)] hover:text-[var(--color-accent)] transition-colors truncate max-w-[180px]"
                    >
                      {s.sector}
                    </Link>
                    <div className="flex items-center gap-2 shrink-0">
                      {s.stark_count > 0 && (
                        <span className="text-[10px] text-[var(--color-up)] font-medium">
                          {s.stark_count} STARK
                        </span>
                      )}
                      <span className={cn("text-xs font-bold font-mono tabular", scoreColorClass(s.avg_score))}>
                        {s.avg_score.toFixed(0)}
                      </span>
                    </div>
                  </div>
                  <div className="h-1.5 rounded-full overflow-hidden bg-[var(--color-bg-elevated)]">
                    <div
                      className="h-full rounded-full transition-all"
                      style={{
                        width: `${s.avg_score}%`,
                        background: s.avg_score >= 70
                          ? "var(--color-score-high)"
                          : s.avg_score >= 50
                          ? "var(--color-score-mid)"
                          : "var(--color-score-low)",
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </SectionCard>
        </div>
      </div>
    </div>
  );
}
