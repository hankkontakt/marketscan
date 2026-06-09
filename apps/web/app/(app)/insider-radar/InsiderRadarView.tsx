"use client";

import { useState } from "react";
import { Users, TrendingUp, AlertCircle, ChevronDown, ExternalLink } from "lucide-react";
import { useInsiderRadar, type InsiderCluster, type RecentInsiderTrade } from "@/hooks/useStrategies";
import { cn } from "@/lib/utils";
import { formatPrice } from "@/lib/format";

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatAmount(amount: number): string {
  if (amount >= 1_000_000) return `${(amount / 1_000_000).toFixed(1)} M`;
  if (amount >= 1_000) return `${(amount / 1_000).toFixed(0)} k`;
  return amount.toFixed(0);
}

const SIGNAL_COLORS: Record<string, string> = {
  STARK:      "bg-[var(--color-up-soft)] text-[var(--color-up)]",
  OK:         "bg-[var(--color-accent-soft)] text-[var(--color-accent)]",
  VÄNTA:      "bg-[var(--color-warn-soft)] text-[var(--color-warn)]",
  EJ_AKTUELL: "bg-[var(--color-bg-elevated)] text-[var(--color-text-muted)]",
};

const SIGNAL_LABELS: Record<string, string> = {
  STARK: "Stark", OK: "OK", VÄNTA: "Avvakta", EJ_AKTUELL: "Ej aktuell",
};

// ─── ClusterScore bar ─────────────────────────────────────────────────────────

function ClusterBar({ score }: { score: number }) {
  // Max realistic score: ~30 (10 insiders * 3 + many trades)
  const pct = Math.min(score / 30 * 100, 100);
  const color = pct >= 66 ? "var(--color-up)" : pct >= 33 ? "var(--color-accent)" : "var(--color-warn)";
  return (
    <div className="flex items-center gap-2">
      <div className="w-16 h-1.5 rounded-full bg-[var(--color-bg-elevated)] overflow-hidden">
        <div className="h-full rounded-full transition-all" style={{ width: `${pct}%`, background: color }} />
      </div>
      <span className="text-xs tabular-nums text-[var(--color-text-muted)]">{score.toFixed(1)}</span>
    </div>
  );
}

// ─── Detail panel ─────────────────────────────────────────────────────────────

function DetailPanel({ cluster }: { cluster: InsiderCluster }) {
  return (
    <tr>
      <td colSpan={8} className="p-0">
        <div className="px-6 py-4 bg-[var(--color-bg-elevated)] border-b border-[var(--color-border)] space-y-3">
          <p className="text-xs font-medium text-[var(--color-text-secondary)]">
            Senaste affärer
          </p>
          <div className="space-y-1.5">
            {cluster.recent_trades.map((t: RecentInsiderTrade, i: number) => (
              <div key={i} className="flex items-center gap-4 text-xs">
                <span className={cn(
                  "w-8 text-center rounded px-1 py-0.5 font-medium",
                  t.type === "buy"
                    ? "bg-[var(--color-up-soft)] text-[var(--color-up)]"
                    : "bg-[var(--color-down-soft)] text-[var(--color-down)]",
                )}>
                  {t.type === "buy" ? "Köp" : "Sälj"}
                </span>
                <span className="font-medium text-[var(--color-text-primary)] w-32 truncate">
                  {t.name ?? "Okänd"}
                </span>
                {t.role && (
                  <span className="text-[var(--color-text-muted)] w-28 truncate">{t.role}</span>
                )}
                {t.amount != null && (
                  <span className="tabular-nums text-[var(--color-text-secondary)]">
                    {formatAmount(t.amount)} kr
                  </span>
                )}
                {t.shares != null && (
                  <span className="tabular-nums text-[var(--color-text-muted)]">
                    {t.shares.toLocaleString("sv-SE")} aktier
                  </span>
                )}
                <span className="ml-auto text-[var(--color-text-muted)]">{t.trade_date}</span>
              </div>
            ))}
          </div>
        </div>
      </td>
    </tr>
  );
}

// ─── Table Row ────────────────────────────────────────────────────────────────

function ClusterRow({
  cluster,
  selected,
  onClick,
}: {
  cluster: InsiderCluster;
  selected: boolean;
  onClick: () => void;
}) {
  const signal = cluster.entry_signal ?? "EJ_AKTUELL";
  const signalColor = SIGNAL_COLORS[signal] ?? SIGNAL_COLORS["EJ_AKTUELL"];
  const signalLabel = SIGNAL_LABELS[signal] ?? signal;

  return (
    <tr
      onClick={onClick}
      className={cn(
        "border-b border-[var(--color-border)] cursor-pointer hover:bg-[var(--color-bg-elevated)] transition-colors",
        selected && "bg-[var(--color-accent-soft)]",
      )}
    >
      {/* Ticker + name */}
      <td className="px-4 py-3">
        <div className="flex items-center gap-2">
          <div>
            <a
              href={`/aktie/${cluster.ticker}`}
              onClick={(e) => e.stopPropagation()}
              className="flex items-center gap-1 font-semibold text-sm text-[var(--color-text-primary)] hover:text-[var(--color-accent)] transition-colors"
            >
              {cluster.ticker}
              <ExternalLink size={10} className="opacity-50" />
            </a>
            {cluster.name && (
              <div className="text-xs text-[var(--color-text-muted)] truncate max-w-[130px]">
                {cluster.name}
              </div>
            )}
          </div>
        </div>
      </td>

      {/* Sector */}
      <td className="px-4 py-3 hidden md:table-cell">
        <span className="text-xs text-[var(--color-text-muted)]">
          {cluster.sector ?? "—"}
        </span>
      </td>

      {/* # Insiders / # Trades */}
      <td className="px-4 py-3 text-center">
        <div className="flex items-center justify-center gap-1">
          <Users size={12} className="text-[var(--color-text-muted)]" />
          <span className="text-sm font-medium text-[var(--color-text-primary)]">
            {cluster.unique_insiders}
          </span>
          <span className="text-xs text-[var(--color-text-muted)]">
            ({cluster.trade_count})
          </span>
        </div>
      </td>

      {/* Total amount */}
      <td className="px-4 py-3 text-right">
        <span className="text-sm tabular-nums font-medium text-[var(--color-text-primary)]">
          {formatAmount(cluster.total_amount)} kr
        </span>
      </td>

      {/* Latest date */}
      <td className="px-4 py-3 text-right hidden sm:table-cell">
        <span className="text-xs text-[var(--color-text-muted)]">
          {cluster.latest_date}
        </span>
      </td>

      {/* Entry signal */}
      <td className="px-4 py-3 text-center hidden lg:table-cell">
        <span className={cn("text-[10px] font-medium px-1.5 py-0.5 rounded", signalColor)}>
          {signalLabel}
        </span>
      </td>

      {/* Score + price */}
      <td className="px-4 py-3 text-right hidden lg:table-cell">
        <div className="text-xs text-[var(--color-text-muted)]">
          {cluster.score_total != null ? `${Math.round(cluster.score_total)}/100` : "—"}
        </div>
        {cluster.price != null && (
          <div className="text-xs tabular-nums text-[var(--color-text-secondary)]">
            {formatPrice(cluster.price)}
          </div>
        )}
      </td>

      {/* Cluster score bar */}
      <td className="px-4 py-3 hidden xl:table-cell">
        <ClusterBar score={cluster.cluster_score} />
      </td>

      {/* Expand chevron */}
      <td className="px-4 py-3 w-8 text-center">
        <ChevronDown
          size={14}
          className={cn(
            "text-[var(--color-text-muted)] transition-transform",
            selected && "rotate-180",
          )}
        />
      </td>
    </tr>
  );
}

// ─── Main View ────────────────────────────────────────────────────────────────

const DAY_OPTIONS = [
  { label: "7 dagar", value: 7 },
  { label: "30 dagar", value: 30 },
  { label: "90 dagar", value: 90 },
] as const;

type TradeFilter = "all" | "buy" | "sell";

export function InsiderRadarView() {
  const [days, setDays] = useState<number>(30);
  const [tradeFilter, setTradeFilter] = useState<TradeFilter>("buy");
  const [selectedTicker, setSelectedTicker] = useState<string | null>(null);

  const tradeType = tradeFilter === "all" ? undefined : tradeFilter;
  const { data = [], isLoading, error } = useInsiderRadar(days, tradeType);

  function toggleRow(ticker: string) {
    setSelectedTicker((prev) => (prev === ticker ? null : ticker));
  }

  return (
    <div className="max-w-5xl space-y-6">

      {/* Header */}
      <div>
        <h1 className="text-xl font-semibold text-[var(--color-text-primary)]">Insider Radar</h1>
        <p className="text-xs text-[var(--color-text-muted)] mt-0.5">
          Kluster av insiders som köper eller säljer — styrelse, VD och ledning rapporterar via Finansinspektionen
        </p>
      </div>

      {/* Info box */}
      <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-bg-card)] p-4 text-xs text-[var(--color-text-muted)] space-y-2">
        <p className="font-medium text-[var(--color-text-secondary)]">Hur fungerar det?</p>
        <p>
          Insiderhandel från FI (Finansinspektionen) och Finnhub samlas in kontinuerligt.
          Radarn visar de aktier där <strong>flest insiders handlat under vald period</strong>,
          vägt mot handelsvolym och unikhet. Kluster-poängen viktar:
          antal unika insiders (×3), antal affärer (×2) och total belopp.
        </p>
        <p className="text-[10px]">
          Observera: historisk insiderhandel är inte en garanti för framtida kursutveckling.
        </p>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 items-center">
        {/* Time window */}
        <div className="flex gap-1">
          {DAY_OPTIONS.map(({ label, value }) => (
            <button
              key={value}
              onClick={() => setDays(value)}
              className={cn(
                "px-3 py-1.5 rounded-lg text-xs font-medium transition-colors",
                days === value
                  ? "bg-[var(--color-accent)] text-white"
                  : "bg-[var(--color-bg-elevated)] text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]",
              )}
            >
              {label}
            </button>
          ))}
        </div>

        {/* Trade type */}
        <div className="flex gap-1">
          {(["all", "buy", "sell"] as TradeFilter[]).map((f) => (
            <button
              key={f}
              onClick={() => setTradeFilter(f)}
              className={cn(
                "px-3 py-1.5 rounded-lg text-xs font-medium transition-colors",
                tradeFilter === f
                  ? "bg-[var(--color-accent)] text-white"
                  : "bg-[var(--color-bg-elevated)] text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]",
              )}
            >
              {f === "all" ? "Alla affärer" : f === "buy" ? "Köp" : "Sälj"}
            </button>
          ))}
        </div>

        {/* Result count */}
        {!isLoading && (
          <span className="ml-auto text-xs text-[var(--color-text-muted)]">
            {data.length} aktier med insiderhandel
          </span>
        )}
      </div>

      {/* Table */}
      {isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="h-12 rounded-lg bg-[var(--color-bg-elevated)] animate-pulse" />
          ))}
        </div>
      ) : error ? (
        <div className="flex flex-col items-center py-16 gap-3 text-center">
          <AlertCircle size={32} strokeWidth={1} className="text-[var(--color-warn)]" />
          <p className="text-sm text-[var(--color-text-muted)]">
            Kunde inte hämta insiderdata
          </p>
        </div>
      ) : data.length === 0 ? (
        <div className="flex flex-col items-center py-16 gap-3 text-center">
          <Users size={36} strokeWidth={1} className="text-[var(--color-text-muted)]" />
          <p className="text-sm text-[var(--color-text-muted)]">
            Ingen insiderhandel registrerad för den valda perioden
          </p>
          <p className="text-xs text-[var(--color-text-muted)] max-w-xs">
            Data hämtas från Finansinspektionen och Finnhub och uppdateras nattligen.
          </p>
        </div>
      ) : (
        <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-bg-card)] overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--color-border)]">
                <th className="px-4 py-3 text-left text-xs font-medium text-[var(--color-text-muted)]">Aktie</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-[var(--color-text-muted)] hidden md:table-cell">Sektor</th>
                <th className="px-4 py-3 text-center text-xs font-medium text-[var(--color-text-muted)]">Insiders (affärer)</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-[var(--color-text-muted)]">Totalt belopp</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-[var(--color-text-muted)] hidden sm:table-cell">Senaste</th>
                <th className="px-4 py-3 text-center text-xs font-medium text-[var(--color-text-muted)] hidden lg:table-cell">Köpläge</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-[var(--color-text-muted)] hidden lg:table-cell">Betyg / Kurs</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-[var(--color-text-muted)] hidden xl:table-cell">Kluster-poäng</th>
                <th className="px-4 py-3 w-8" />
              </tr>
            </thead>
            <tbody>
              {data.map((cluster) => {
                const isSelected = selectedTicker === cluster.ticker;
                return (
                  <>
                    <ClusterRow
                      key={cluster.ticker}
                      cluster={cluster}
                      selected={isSelected}
                      onClick={() => toggleRow(cluster.ticker)}
                    />
                    {isSelected && (
                      <DetailPanel key={`detail-${cluster.ticker}`} cluster={cluster} />
                    )}
                  </>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Summary stats */}
      {!isLoading && data.length > 0 && (
        <div className="grid grid-cols-3 gap-4">
          {[
            {
              label: "Aktier med insiderköp",
              value: data.filter(d => d.recent_trades.some(t => t.type === "buy")).length,
              icon: TrendingUp,
              color: "text-[var(--color-up)]",
            },
            {
              label: "Unika insiders totalt",
              value: data.reduce((sum, d) => sum + d.unique_insiders, 0),
              icon: Users,
              color: "text-[var(--color-accent)]",
            },
            {
              label: "Totalt handelsvolym (kr)",
              value: `${formatAmount(data.reduce((sum, d) => sum + d.total_amount, 0))} kr`,
              icon: TrendingUp,
              color: "text-[var(--color-text-secondary)]",
            },
          ].map(({ label, value, icon: Icon, color }) => (
            <div
              key={label}
              className="rounded-xl border border-[var(--color-border)] bg-[var(--color-bg-card)] p-4"
            >
              <div className="flex items-center gap-2 mb-1">
                <Icon size={14} className={color} />
                <span className="text-xs text-[var(--color-text-muted)]">{label}</span>
              </div>
              <div className={cn("text-lg font-bold tabular-nums", color)}>
                {value}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
