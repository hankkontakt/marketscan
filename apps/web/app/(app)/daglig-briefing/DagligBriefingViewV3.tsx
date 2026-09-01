"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import type { ElementType, ReactNode } from "react";
import Link from "next/link";
import {
  Activity, ArrowDownRight, ArrowRight, ArrowUpRight, Globe, Radio, Users,
} from "lucide-react";
import { ApiError } from "@/lib/api";
import { v3Changes } from "@/lib/v3";
import type { ChangeEventV3 } from "@/lib/types/decision_v3";
import { useInsiderRadar } from "@/hooks/useStrategies";
import type { InsiderCluster } from "@/hooks/useStrategies";
import { useMacroRegime, useSectorOverview, useGlobalIndices } from "@/hooks/useMarkets";
import type { SectorSummary } from "@/hooks/useMarkets";
import { usePortfolio, usePortfolioHistory, useFundHoldings } from "@/hooks/usePortfolio";
import { cn } from "@/lib/utils";
import { formatPrice, scoreColorClass } from "@/lib/format";
import { RegimeGauge } from "@/components/widgets/RegimeGauge";
import { RiskGauge } from "@/components/widgets/RiskGauge";
import { MewsStrip } from "@/components/widgets/MewsStrip";
import { PortfolioCoachCard } from "@/components/widgets/PortfolioCoachCard";
import { InfoTooltip } from "@/components/ui/InfoTooltip";
import {
  THESIS_BAND_CONFIG,
  SETUP_STATE_CONFIG,
  RISK_STATE_CONFIG,
  DATA_GRADE_CONFIG,
  TRADABILITY_CONFIG,
} from "@/components/screener-v3/badges";

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

// ─── Transition labels (svenska) ───────────────────────────────────────────

const TRANSITION_LABELS: Record<string, string> = {
  thesis: "Tes",
  setup: "Setup",
  risk: "Risk",
  data_grade: "Datakvalitet",
  tradability: "Tradability",
  rank: "Rank",
};

function transitionLabel(type: string): string {
  return TRANSITION_LABELS[type] ?? type;
}

// State configs per dimension — reuse the V3 semantic badge labels so a state
// is always shown as text, never as a bare code.
const STATE_CONFIGS: Record<string, Record<string, { label: string }>> = {
  thesis: THESIS_BAND_CONFIG,
  setup: SETUP_STATE_CONFIG,
  risk: RISK_STATE_CONFIG,
  data_grade: DATA_GRADE_CONFIG,
  tradability: TRADABILITY_CONFIG,
};

function stateLabel(transitionType: string, state: string | null | undefined): string {
  if (state == null || state === "") return "—";
  const config = STATE_CONFIGS[transitionType];
  return config?.[state]?.label ?? state;
}

// ─── Portfolio hero ────────────────────────────────────────────────────────

function PortfolioHero() {
  const { data: portfolio, isLoading: loadingPortfolio } = usePortfolio();
  const { data: funds = [],  isLoading: loadingFunds }    = useFundHoldings();
  const { data: history,     isLoading: loadingHistory }  = usePortfolioHistory();

  const holdings = useMemo(() => portfolio?.holdings ?? [], [portfolio?.holdings]);

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
  icon: ElementType;
  label: string;
  value: ReactNode;
  sub?: string;
  positive?: boolean | null;
  href?: string;
}) {
  const content = (
    <div className="rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 p-4
                    hover:border-zinc-300 dark:hover:border-zinc-700 transition-colors h-full">
      <div className="flex items-center gap-1.5 mb-2">
        <Icon size={13} strokeWidth={1.5} className="text-zinc-400" />
        <span className="text-[11px] text-zinc-500 font-medium uppercase tracking-wide">{label}</span>
      </div>
      <p className={cn(
        "text-xl font-bold font-mono tabular tracking-tight",
        positive === true  ? "text-emerald-600 dark:text-emerald-400"
        : positive === false ? "text-rose-600 dark:text-rose-400"
        : "text-zinc-900 dark:text-zinc-100",
      )}>
        {value}
      </p>
      {sub && (
        <p className="text-xs text-zinc-500 mt-0.5">{sub}</p>
      )}
    </div>
  );

  return href ? <Link href={href}>{content}</Link> : content;
}

// ─── Change row — one transition between the two latest snapshots ──────────

function ChangeRow({ row }: { row: ChangeEventV3 }) {
  const delta = row.rank_delta;
  return (
    <li>
      <Link
        href={`/aktie/${encodeURIComponent(row.ticker)}`}
        className="flex items-center gap-3 px-4 py-3 hover:bg-zinc-50 dark:hover:bg-zinc-900/50 transition-colors group"
      >
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-semibold text-zinc-900 dark:text-zinc-100 group-hover:text-emerald-600 dark:group-hover:text-emerald-400 transition-colors">
              {row.ticker}
            </span>
            <span className="inline-flex items-center px-1.5 py-0.5 rounded-md text-[10px] font-medium uppercase tracking-wide bg-zinc-100 dark:bg-zinc-800 text-zinc-500 dark:text-zinc-400">
              {transitionLabel(row.transition_type)}
            </span>
          </div>
          <div className="flex items-center gap-1.5 mt-1 flex-wrap text-xs">
            <span className="text-zinc-500">{stateLabel(row.transition_type, row.from_state)}</span>
            <ArrowRight size={10} strokeWidth={1.5} className="text-zinc-400 shrink-0" aria-hidden="true" />
            <span className="font-medium text-zinc-800 dark:text-zinc-200">
              {stateLabel(row.transition_type, row.to_state)}
            </span>
            <code className="font-mono text-[10px] text-zinc-400 bg-zinc-100 dark:bg-zinc-800 px-1.5 py-0.5 rounded truncate max-w-[220px]">
              {row.reason_code}
            </code>
          </div>
        </div>
        {delta != null && (
          <span className={cn(
            "flex items-center gap-1 text-sm font-bold font-mono tabular shrink-0",
            delta >= 0 ? "text-emerald-600 dark:text-emerald-400" : "text-rose-600 dark:text-rose-400",
          )}>
            {delta >= 0
              ? <ArrowUpRight size={14} strokeWidth={2} aria-hidden="true" />
              : <ArrowDownRight size={14} strokeWidth={2} aria-hidden="true" />}
            {delta >= 0 ? "+" : ""}{delta.toFixed(1)}
          </span>
        )}
      </Link>
    </li>
  );
}

// ─── "Vad ändrades?" — primary section ─────────────────────────────────────

function ChangesCard({
  rows, isLoading, error, asOf,
}: {
  rows: ChangeEventV3[];
  isLoading: boolean;
  error: string | null;
  asOf: string | null;
}) {
  return (
    <section
      aria-labelledby="changes-heading"
      className="rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 shadow-sm overflow-hidden"
    >
      <div className="flex items-center justify-between px-4 py-3 border-b border-zinc-200 dark:border-zinc-800">
        <div className="flex items-center gap-2">
          <h2 id="changes-heading" className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
            Vad ändrades?
          </h2>
          <InfoTooltip
            text="State-transitioner och rank-rörelser mellan de två senaste publicerade besluts-snapshotten."
            side="top"
          />
        </div>
        {asOf && (
          <span className="text-[11px] font-mono text-zinc-400">
            {new Date(asOf).toLocaleDateString("sv-SE")}
          </span>
        )}
      </div>

      {error ? (
        <div
          role="alert"
          className="m-4 py-10 text-center text-sm text-amber-700 dark:text-amber-300 rounded-xl border border-amber-500/30 bg-amber-500/5"
        >
          {error}
        </div>
      ) : isLoading ? (
        <div role="status" className="space-y-1 p-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-10 rounded-lg skeleton" />
          ))}
          <span className="sr-only">Laddar förändringar...</span>
        </div>
      ) : rows.length === 0 ? (
        <div className="py-12 text-center">
          <p className="text-sm font-medium text-zinc-600 dark:text-zinc-300">
            Inga förändringar sedan förra publicerade snapshotten
          </p>
          <p className="text-xs text-zinc-400 mt-1">
            Nästa diff publiceras när en ny snapshot har publicerats.
          </p>
        </div>
      ) : (
        <ul className="divide-y divide-zinc-100 dark:divide-zinc-900">
          {rows.map((row) => (
            <ChangeRow key={row.id} row={row} />
          ))}
        </ul>
      )}
    </section>
  );
}

// ─── Insider card ──────────────────────────────────────────────────────────

function InsiderCard({ insiders, isLoading }: { insiders: InsiderCluster[]; isLoading: boolean }) {
  return (
    <div className="rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 shadow-sm overflow-hidden">
      <div className="flex items-center justify-between px-4 py-3 border-b border-zinc-200 dark:border-zinc-800">
        <div className="flex items-center gap-2">
          <Users size={14} strokeWidth={1.5} className="text-zinc-400" />
          <h2 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">Insiderköp (14 dagar)</h2>
        </div>
        <Link
          href="/insider-radar"
          className="flex items-center gap-1 text-[11px] text-zinc-500 hover:text-emerald-600 dark:hover:text-emerald-400 transition-colors"
        >
          Insider Radar
          <ArrowRight size={10} strokeWidth={1.5} />
        </Link>
      </div>

      <div className="p-1">
        {isLoading ? (
          <div className="space-y-1 p-2">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="h-9 rounded-lg skeleton" />
            ))}
          </div>
        ) : insiders.length === 0 ? (
          <p className="flex items-center justify-center py-8 text-xs text-zinc-500">
            Ingen registrerad insiderhandel
          </p>
        ) : (
          insiders.map(cluster => (
            <Link
              key={cluster.ticker}
              href={`/aktie/${cluster.ticker}`}
              className="flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-zinc-50 dark:hover:bg-zinc-900/50 transition-colors group"
            >
              <div className="min-w-0 flex-1">
                <span className="text-sm font-semibold text-zinc-900 dark:text-zinc-100 group-hover:text-emerald-600 dark:group-hover:text-emerald-400 transition-colors">
                  {cluster.ticker}
                </span>
                {cluster.name && (
                  <span className="ml-2 text-xs text-zinc-500 truncate hidden sm:inline max-w-[80px]">
                    {cluster.name}
                  </span>
                )}
              </div>
              <div className="flex items-center gap-1.5 shrink-0 text-xs">
                <span className="text-zinc-500">{cluster.unique_insiders} ins.</span>
                <span className="font-medium text-emerald-600 dark:text-emerald-400 font-mono tabular">
                  {fmt(cluster.total_amount)} kr
                </span>
              </div>
            </Link>
          ))
        )}
      </div>
    </div>
  );
}

// ─── Sector card ───────────────────────────────────────────────────────────

function SectorCard({ sectors, isLoading }: { sectors: SectorSummary[]; isLoading: boolean }) {
  return (
    <div className="rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 shadow-sm overflow-hidden">
      <div className="flex items-center justify-between px-4 py-3 border-b border-zinc-200 dark:border-zinc-800">
        <div className="flex items-center gap-2">
          <Globe size={14} strokeWidth={1.5} className="text-zinc-400" />
          <h2 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">Sektorer — snittbetyg</h2>
        </div>
        <Link
          href="/marknad"
          className="flex items-center gap-1 text-[11px] text-zinc-500 hover:text-emerald-600 dark:hover:text-emerald-400 transition-colors"
        >
          Komplett vy
          <ArrowRight size={10} strokeWidth={1.5} />
        </Link>
      </div>

      <div className="px-3 py-2">
        {isLoading ? (
          <div className="space-y-3 p-2">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="h-6 rounded-lg skeleton" />
            ))}
          </div>
        ) : sectors.length === 0 ? (
          <p className="flex items-center justify-center py-8 text-xs text-zinc-500">
            Sektordata ej tillgänglig
          </p>
        ) : (
          <div className="space-y-3">
            {sectors.map(s => (
              <div key={s.sector}>
                <div className="flex items-center justify-between mb-1">
                  <Link
                    href={`/screener?sector=${encodeURIComponent(s.sector)}`}
                    className="text-xs font-medium text-zinc-800 dark:text-zinc-200 hover:text-emerald-600 dark:hover:text-emerald-400 transition-colors truncate max-w-[180px]"
                  >
                    {s.sector}
                  </Link>
                  <div className="flex items-center gap-2 shrink-0">
                    {s.stark_count > 0 && (
                      <span className="text-[10px] text-emerald-600 dark:text-emerald-400 font-medium">
                        {s.stark_count} STARK
                      </span>
                    )}
                    <span className={cn("text-xs font-bold font-mono tabular", scoreColorClass(s.avg_score))}>
                      {s.avg_score.toFixed(0)}
                    </span>
                  </div>
                </div>
                <div className="h-1.5 rounded-full overflow-hidden bg-zinc-100 dark:bg-zinc-800">
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
        )}
      </div>
    </div>
  );
}

// ─── Main view ─────────────────────────────────────────────────────────────

export function DagligBriefingViewV3() {
  // Primary question: what changed since the last published snapshot?
  const [rows, setRows] = useState<ChangeEventV3[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [asOf, setAsOf] = useState<string | null>(null);

  const load = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await v3Changes(50);
      setRows(data.rows ?? []);
      setAsOf(data.as_of ?? null);
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        setError("Ingen publicerad besluts-snapshot finns ännu.");
      } else if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Kunde inte hämta förändringarna.");
      }
      setRows([]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  // Market data for stat cards
  const { data: regime, isLoading: loadingRegime } = useMacroRegime();
  const { data: indicesData } = useGlobalIndices();
  const indices = indicesData?.indices ?? [];
  const omx = indices.find(i => i.name.toLowerCase().includes("omx") || i.name === "OMX30");
  const sp  = indices.find(i => i.name.includes("S&P") || i.name.includes("500"));

  // Insider + sectors (non-score sections kept from V1)
  const { data: insiders = [], isLoading: loadingInsiders } = useInsiderRadar(14, "buy");
  const topInsiders = insiders.slice(0, 5);
  const { data: sectorData, isLoading: loadingSectors } = useSectorOverview();
  const topSectors = sectorData?.sectors
    ? [...sectorData.sectors].sort((a, b) => b.avg_score - a.avg_score).slice(0, 5)
    : [];

  return (
    <div className="w-full space-y-5 max-w-7xl mx-auto px-4 sm:px-6 py-6">

      {/* ── Header ─────────────────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-zinc-900 dark:text-zinc-50">
            Daglig briefing
          </h1>
          <p className="text-xs text-zinc-500 mt-0.5">
            Vad ändrades materiellt sedan förra publicerade snapshotten?
          </p>
        </div>
        <div className="text-xs font-mono text-zinc-400 text-right">
          {asOf ? `Snapshot ${new Date(asOf).toLocaleDateString("sv-SE")}` : "ingen snapshot ännu"}
        </div>
      </div>

      {/* ── Vad ändrades? (primärfråga) ─────────────────────────────── */}
      <ChangesCard rows={rows} isLoading={isLoading} error={error} asOf={asOf} />

      {/* ── Portfölj-hero ───────────────────────────────────────────── */}
      <PortfolioHero />

      {/* ── Stat chips ──────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <StatCard
          icon={Radio}
          label="Marknadsläge"
          value={loadingRegime ? "…" : (regime?.label ?? "—")}
          sub={regime?.regime}
          positive={regime?.color === "green" ? true : regime?.color === "red" ? false : null}
          href="/marknad"
        />
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

      {/* ── Regim + risk ────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
        <RegimeGauge />
        <RiskGauge />
      </div>

      {/* ── Portföljcoach ───────────────────────────────────────────── */}
      <PortfolioCoachCard />

      {/* ── Mångdubblar-kandidater ──────────────────────────────────── */}
      <MewsStrip />

      {/* ── Insider + sektor ────────────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <InsiderCard insiders={topInsiders} isLoading={loadingInsiders} />
        <SectorCard sectors={topSectors} isLoading={loadingSectors} />
      </div>
    </div>
  );
}