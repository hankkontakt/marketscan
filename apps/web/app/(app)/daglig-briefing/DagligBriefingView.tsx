"use client";

import { TrendingUp, TrendingDown, Users, Activity, Globe, RefreshCw, type LucideIcon } from "lucide-react";
import { useScreener } from "@/hooks/useScreener";
import { useScoreMovers } from "@/hooks/useAlerts";
import type { ScoreMover } from "@/types/alerts";
import { useInsiderRadar } from "@/hooks/useStrategies";
import { useMacroRegime, useSectorOverview } from "@/hooks/useMarkets";
import { cn } from "@/lib/utils";
import { formatPrice, formatPct, scoreColorClass, formatScore } from "@/lib/format";
import type { ScanRow } from "@/types/scan";

// ─── Helpers ──────────────────────────────────────────────────────────────────

const SIGNAL_COLORS: Record<string, string> = {
  STARK:      "bg-[var(--color-up-soft)] text-[var(--color-up)]",
  OK:         "bg-[var(--color-accent-soft)] text-[var(--color-accent)]",
  VÄNTA:      "bg-[var(--color-warn-soft)] text-[var(--color-warn)]",
  EJ_AKTUELL: "bg-[var(--color-bg-elevated)] text-[var(--color-text-muted)]",
};
const SIGNAL_LABELS: Record<string, string> = {
  STARK: "Stark", OK: "OK", VÄNTA: "Avvakta", EJ_AKTUELL: "Ej aktuell",
};

const REGIME_PALETTE: Record<string, { bg: string; text: string; border: string }> = {
  green:   { bg: "bg-[var(--color-up-soft)]",   text: "text-[var(--color-up)]",   border: "border-[var(--color-up)]" },
  red:     { bg: "bg-[var(--color-down-soft)]",  text: "text-[var(--color-down)]", border: "border-[var(--color-down)]" },
  amber:   { bg: "bg-[var(--color-warn-soft)]",  text: "text-[var(--color-warn)]", border: "border-[var(--color-warn)]" },
  neutral: { bg: "bg-[var(--color-bg-elevated)]", text: "text-[var(--color-text-secondary)]", border: "border-[var(--color-border)]" },
};

function formatAmount(v: number): string {
  if (v >= 1_000_000) return `${(v / 1_000_000).toFixed(1)} M`;
  if (v >= 1_000) return `${(v / 1_000).toFixed(0)} k`;
  return v.toFixed(0);
}

// ─── Stock mini-row ───────────────────────────────────────────────────────────

function StockMiniRow({ stock }: { stock: ScanRow }) {
  const signal = stock.entry_signal ?? "EJ_AKTUELL";
  const signalColor = SIGNAL_COLORS[signal] ?? SIGNAL_COLORS["EJ_AKTUELL"];
  const signalLabel = SIGNAL_LABELS[signal] ?? signal;

  return (
    <a
      href={`/aktie/${stock.ticker}`}
      className="flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-[var(--color-bg-elevated)] transition-colors group"
    >
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-[var(--color-text-primary)] group-hover:text-[var(--color-accent)] transition-colors">
            {stock.ticker}
          </span>
          {stock.name && (
            <span className="text-xs text-[var(--color-text-muted)] truncate hidden sm:block max-w-[120px]">
              {stock.name}
            </span>
          )}
        </div>
      </div>
      <div className="flex items-center gap-2 shrink-0">
        {stock.score_total != null && (
          <span className={cn("text-xs font-bold tabular", scoreColorClass(stock.score_total))}>
            {formatScore(stock.score_total)}
          </span>
        )}
        <span className={cn("text-[10px] font-medium px-1.5 py-0.5 rounded", signalColor)}>
          {signalLabel}
        </span>
        {stock.price != null && (
          <span className="text-xs font-mono tabular text-[var(--color-text-secondary)]">
            {formatPrice(stock.price)}
          </span>
        )}
      </div>
    </a>
  );
}

// ─── Score mover row ─────────────────────────────────────────────────────────

function MoverRow({ mover, direction }: { mover: ScoreMover; direction: "up" | "down" }) {
  const isUp = direction === "up";
  return (
    <a
      href={`/aktie/${mover.ticker}`}
      className="flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-[var(--color-bg-elevated)] transition-colors group"
    >
      <div className="min-w-0 flex-1">
        <span className="text-sm font-semibold text-[var(--color-text-primary)] group-hover:text-[var(--color-accent)] transition-colors">
          {mover.ticker}
        </span>
        {mover.name && (
          <span className="ml-2 text-xs text-[var(--color-text-muted)] truncate hidden sm:inline max-w-[100px]">
            {mover.name}
          </span>
        )}
      </div>
      <div className="flex items-center gap-2 shrink-0">
        {mover.prev_score != null && mover.score_total != null && (
          <span className="text-xs text-[var(--color-text-muted)] tabular">
            {Math.round(mover.prev_score)} → {Math.round(mover.score_total)}
          </span>
        )}
        <span className={cn(
          "text-sm font-bold tabular",
          isUp ? "text-[var(--color-up)]" : "text-[var(--color-down)]",
        )}>
          {isUp ? "+" : ""}{mover.score_change.toFixed(1)}
        </span>
      </div>
    </a>
  );
}

// ─── Section card ─────────────────────────────────────────────────────────────

function BriefingCard({
  title,
  icon: Icon,
  iconColor,
  children,
  isLoading,
  empty,
  emptyText,
}: {
  title: string;
  icon: LucideIcon;
  iconColor: string;
  children: React.ReactNode;
  isLoading?: boolean;
  empty?: boolean;
  emptyText?: string;
}) {
  return (
    <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-bg-card)] flex flex-col">
      <div className="flex items-center gap-2 px-4 py-3 border-b border-[var(--color-border)]">
        <Icon size={15} className={iconColor} />
        <h2 className="text-sm font-semibold text-[var(--color-text-primary)]">{title}</h2>
      </div>
      <div className="flex-1 px-1 py-1">
        {isLoading ? (
          <div className="space-y-1 p-2">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="h-9 rounded-lg bg-[var(--color-bg-elevated)] animate-pulse" />
            ))}
          </div>
        ) : empty ? (
          <div className="flex items-center justify-center py-8 text-xs text-[var(--color-text-muted)]">
            {emptyText ?? "Ingen data tillgänglig"}
          </div>
        ) : (
          children
        )}
      </div>
    </div>
  );
}

// ─── Main View ────────────────────────────────────────────────────────────────

export function DagligBriefingView() {
  const today = new Date().toLocaleDateString("sv-SE", {
    weekday: "long", year: "numeric", month: "long", day: "numeric",
  });

  // Data fetching
  const { data: starkStocks = [], isLoading: loadingStark } = useScreener({
    segments: ["large_cap", "mid_cap", "small_cap", "micro_cap"],
    entry_signal: "STARK",
    limit: 8,
  });

  const { data: moversUp = [], isLoading: loadingUp } = useScoreMovers(7, "up", 6);
  const { data: moversDown = [], isLoading: loadingDown } = useScoreMovers(7, "down", 6);

  const { data: insiders = [], isLoading: loadingInsiders } = useInsiderRadar(14, "buy");

  const { data: regime, isLoading: loadingRegime } = useMacroRegime();
  const { data: sectorData, isLoading: loadingSectors } = useSectorOverview();

  const regimePalette = REGIME_PALETTE[regime?.color ?? "neutral"];

  const topInsiders = insiders.slice(0, 5);
  const topSectors = sectorData?.sectors
    ? [...sectorData.sectors].sort((a, b) => b.avg_score - a.avg_score).slice(0, 5)
    : [];

  return (
    <div className="space-y-6 max-w-6xl">

      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold text-[var(--color-text-primary)]">Daglig Briefing</h1>
          <p className="text-xs text-[var(--color-text-muted)] mt-0.5 capitalize">{today}</p>
        </div>

        {/* Regime badge */}
        {!loadingRegime && regime && (
          <div className={cn(
            "px-3 py-2 rounded-xl border text-xs font-medium flex items-center gap-2",
            regimePalette.bg, regimePalette.text, regimePalette.border,
          )}>
            <Activity size={13} />
            {regime.label}
          </div>
        )}
      </div>

      {/* Regime description */}
      {!loadingRegime && regime && (
        <div className={cn(
          "rounded-xl border p-3 text-xs",
          regimePalette.bg, regimePalette.border,
        )}>
          <p className={cn("font-medium mb-0.5", regimePalette.text)}>Marknadsläge: {regime.label}</p>
          <p className="text-[var(--color-text-muted)]">{regime.description}</p>
        </div>
      )}

      {/* Main grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">

        {/* Column 1: Top STARK + Insiders */}
        <div className="space-y-5">
          <BriefingCard
            title="Toppbetyg idag"
            icon={TrendingUp}
            iconColor="text-[var(--color-up)]"
            isLoading={loadingStark}
            empty={starkStocks.length === 0}
            emptyText="Inga STARK-aktier just nu"
          >
            {starkStocks.map((s) => (
              <StockMiniRow key={s.ticker} stock={s} />
            ))}
            <a
              href="/screener?entry_signal=STARK"
              className="block px-3 py-2 text-xs text-[var(--color-accent)] hover:underline"
            >
              Visa alla STARK →
            </a>
          </BriefingCard>

          <BriefingCard
            title="Insiderköp (14 dagar)"
            icon={Users}
            iconColor="text-[var(--color-accent)]"
            isLoading={loadingInsiders}
            empty={topInsiders.length === 0}
            emptyText="Ingen insiderhandel registrerad"
          >
            {topInsiders.map((cluster) => (
              <a
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
                <div className="flex items-center gap-2 shrink-0 text-xs text-[var(--color-text-muted)]">
                  <Users size={11} />
                  <span>{cluster.unique_insiders}</span>
                  <span className="text-[var(--color-accent)] font-medium">
                    {formatAmount(cluster.total_amount)} kr
                  </span>
                </div>
              </a>
            ))}
            <a
              href="/insider-radar"
              className="block px-3 py-2 text-xs text-[var(--color-accent)] hover:underline"
            >
              Visa hela Insider Radar →
            </a>
          </BriefingCard>
        </div>

        {/* Column 2: Score movers */}
        <div className="space-y-5">
          <BriefingCard
            title="Stigande betyg (7 dagar)"
            icon={TrendingUp}
            iconColor="text-[var(--color-up)]"
            isLoading={loadingUp}
            empty={(moversUp as ScoreMover[]).length === 0}
            emptyText="Inga tydliga stigande betyg"
          >
            {(moversUp as ScoreMover[]).map((m) => (
              <MoverRow key={m.ticker} mover={m} direction="up" />
            ))}
            <a
              href="/signal-analytics"
              className="block px-3 py-2 text-xs text-[var(--color-accent)] hover:underline"
            >
              Signalanalys →
            </a>
          </BriefingCard>

          <BriefingCard
            title="Sjunkande betyg (7 dagar)"
            icon={TrendingDown}
            iconColor="text-[var(--color-down)]"
            isLoading={loadingDown}
            empty={(moversDown as ScoreMover[]).length === 0}
            emptyText="Inga tydliga sjunkande betyg"
          >
            {(moversDown as ScoreMover[]).map((m) => (
              <MoverRow key={m.ticker} mover={m} direction="down" />
            ))}
          </BriefingCard>
        </div>

        {/* Column 3: Sectors */}
        <div className="space-y-5">
          <BriefingCard
            title="Sektorer — snittbetyg"
            icon={Globe}
            iconColor="text-[var(--color-text-secondary)]"
            isLoading={loadingSectors}
            empty={topSectors.length === 0}
            emptyText="Sektordata ej tillgänglig"
          >
            <div className="px-2 py-1 space-y-2">
              {topSectors.map((s) => (
                <div key={s.sector}>
                  <div className="flex justify-between text-xs mb-0.5">
                    <a
                      href={`/screener?sector=${encodeURIComponent(s.sector)}`}
                      className="text-[var(--color-text-primary)] hover:text-[var(--color-accent)] transition-colors"
                    >
                      {s.sector}
                    </a>
                    <span className={cn("font-mono tabular", scoreColorClass(s.avg_score))}>
                      {s.avg_score.toFixed(0)}
                    </span>
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
                  <div className="flex gap-2 mt-0.5 text-[10px] text-[var(--color-text-muted)]">
                    <span>{s.count} aktier</span>
                    {s.stark_count > 0 && (
                      <span className="text-[var(--color-up)]">{s.stark_count} STARK</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
            <a
              href="/marknad"
              className="block px-3 py-2 text-xs text-[var(--color-accent)] hover:underline"
            >
              Komplett marknadsvy →
            </a>
          </BriefingCard>

          {/* Scan metadata */}
          <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-bg-card)] p-4 text-xs space-y-2">
            <div className="flex items-center gap-2 text-[var(--color-text-muted)]">
              <RefreshCw size={12} />
              <span>Data uppdateras nattligen (kl. 03:00 UTC)</span>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <a
                href="/screener"
                className="block text-center px-2 py-1.5 rounded-lg bg-[var(--color-bg-elevated)] text-[var(--color-text-secondary)] hover:text-[var(--color-accent)] transition-colors"
              >
                Screener
              </a>
              <a
                href="/signal-analytics"
                className="block text-center px-2 py-1.5 rounded-lg bg-[var(--color-bg-elevated)] text-[var(--color-text-secondary)] hover:text-[var(--color-accent)] transition-colors"
              >
                Signalanalys
              </a>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
