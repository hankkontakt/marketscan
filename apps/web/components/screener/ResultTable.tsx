"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { TrendingUp, TrendingDown, Minus, AlertTriangle, Droplet } from "lucide-react";
import { InfoTooltip } from "@/components/ui/InfoTooltip";
import { cn } from "@/lib/utils";
import {
  formatPctChange,
  formatPrice,
  formatMarketCap,
  formatPE,
  signalLabel,
  signalClass,
  segmentLabel,
  changeClass,
  trendLabel,
} from "@/lib/format";
import type { ScanRow } from "@/types/scan";

interface Props {
  data: ScanRow[];
  loading?: boolean;
  onReset?: () => void;
}

type SortKey = "master_rank" | "master_rank_pctl" | "score_total" | "change_pct" | "price" | "market_cap" | "pe_trailing" | "roe";
type SortDir = "asc" | "desc";

export function ResultTable({ data, loading, onReset }: Props) {
  const router = useRouter();
  const [sort, setSort] = useState<{ key: SortKey; dir: SortDir }>({
    key: "master_rank",
    dir: "desc",
  });
  const [focusedRow, setFocusedRow] = useState<number>(-1);

  const sorted = [...data].sort((a, b) => {
    const av = a[sort.key] ?? -Infinity;
    const bv = b[sort.key] ?? -Infinity;
    return sort.dir === "desc" ? (bv as number) - (av as number) : (av as number) - (bv as number);
  });

  function toggleSort(key: SortKey) {
    setSort((s) => ({
      key,
      dir: s.key === key ? (s.dir === "desc" ? "asc" : "desc") : "desc",
    }));
  }

  const openStock = useCallback((ticker: string) => {
    router.push(`/aktie/${ticker}`);
  }, [router]);

  // Keyboard navigation
  const onKeyDown = useCallback(
    (e: React.KeyboardEvent, index: number, ticker: string) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        openStock(ticker);
      } else if (e.key === "ArrowDown") {
        e.preventDefault();
        setFocusedRow(Math.min(index + 1, sorted.length - 1));
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setFocusedRow(Math.max(index - 1, 0));
      }
    },
    [openStock, sorted.length],
  );

  if (loading) return <TableSkeleton />;

  return (
    <div className="rounded-xl overflow-hidden border border-[var(--color-border)]">
      <div className="overflow-x-auto">
        <table className="w-full min-w-[1200px] text-xs border-collapse whitespace-nowrap">
          <thead>
            <tr className="bg-[var(--color-bg-surface)]" style={{ borderBottom: "1px solid var(--color-border)" }}>
              <Th label="Aktie" width="220px" />
              <Th label="Segment" width="110px" />
              <Th
                label="MasterRank"
                sortKey="master_rank"
                sort={sort}
                onSort={toggleSort}
                tip="Kvantitativ faktormodell (0–100) kalibrerad per segment med datatäthets-tak och multi-faktor-regim"
                width="85px"
                align="right"
              />
              <Th
                label="Pctl"
                sortKey="master_rank_pctl"
                sort={sort}
                onSort={toggleSort}
                tip="MasterRank-percentil (0–100) inom aktiens segment. Möjliggör direkt jämförelse mellan olika segment."
                width="65px"
                align="right"
              />
              <Th
                label="Totalbetyg"
                sortKey="score_total"
                sort={sort}
                onSort={toggleSort}
                tip="Linjär sammanvägning av 8 delbetyg (0–100) från den breda scanning-motorn"
                width="85px"
                align="right"
              />
              <Th
                label="Köpläge"
                width="130px"
                tip="Långsiktigt rankläge (T1–T3). Under v2-migrationen separeras detta i Thesis och kortsiktig Setup."
              />
              <Th label="Trend" width="90px" />
              <Th
                label="Kurs"
                sortKey="price"
                sort={sort}
                onSort={toggleSort}
                width="90px"
                align="right"
              />
              <Th
                label="Idag"
                sortKey="change_pct"
                sort={sort}
                onSort={toggleSort}
                width="75px"
                align="right"
              />
              <Th
                label="Börsvärde"
                sortKey="market_cap"
                sort={sort}
                onSort={toggleSort}
                width="90px"
                align="right"
              />
              <Th
                label="P/E"
                sortKey="pe_trailing"
                sort={sort}
                onSort={toggleSort}
                width="65px"
                align="right"
              />
              <Th
                label="ROE"
                sortKey="roe"
                sort={sort}
                onSort={toggleSort}
                width="65px"
                align="right"
              />
            </tr>
          </thead>
          <tbody>
            {sorted.map((row, i) => (
              <tr
                key={row.ticker}
                tabIndex={0}
                role="row"
                aria-label={`${row.name} ${row.ticker}`}
                onClick={() => openStock(row.ticker)}
                onKeyDown={(e) => onKeyDown(e, i, row.ticker)}
                ref={(el) => { if (focusedRow === i) el?.focus(); }}
                className={cn(
                  "cursor-pointer border-b transition-colors focus:outline-none",
                  "bg-[var(--color-bg-surface)] hover:bg-[var(--color-bg-elevated)] focus:bg-[var(--color-bg-elevated)]",
                )}
                style={{ borderColor: "var(--color-border)" }}
              >
                {/* Aktie */}
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    {row.low_liquidity && (
                      <span title="Låg likviditet — genomsnittlig handelsvolym under tröskelvärde (beräknas externt; risk vid stora order)">
                        <AlertTriangle size={12} strokeWidth={1.5}
                                       className="text-[var(--color-warn)] shrink-0" />
                      </span>
                    )}
                    <div>
                      <div className="flex items-center gap-1.5">
                        <span className="font-semibold text-[var(--color-text-primary)] text-xs truncate max-w-36">
                          {row.name}
                        </span>
                        {row.liquidity_grade && row.liquidity_grade !== "unknown" && (
                          <span
                            className={cn(
                              "px-1 py-0.2 rounded text-[10px] font-mono font-medium inline-flex items-center gap-0.5",
                              row.liquidity_grade === "A" || row.liquidity_grade === "B"
                                ? "bg-[var(--color-bg-elevated)] text-[var(--color-text-secondary)] border border-[var(--color-border)]"
                                : row.liquidity_grade === "C"
                                ? "bg-[var(--color-bg-elevated)] text-[var(--color-text-muted)] border border-[var(--color-border)]"
                                : "bg-red-950/40 text-red-400 border border-red-800/40"
                            )}
                            title={`Likviditetsgrad ${row.liquidity_grade} (baserat på 20d medianomsättning mot segmentgolv)`}
                          >
                            <Droplet size={8} strokeWidth={1.5} />
                            {row.liquidity_grade}
                          </span>
                        )}
                      </div>
                      <div className="font-mono text-[var(--color-text-muted)] text-[11px]">
                        {row.ticker}
                      </div>
                    </div>
                  </div>
                </td>

                {/* Segment */}
                <td className="px-4 py-3 text-[var(--color-text-muted)]">
                  {segmentLabel(row.segment)}
                </td>

                {/* MasterRank */}
                <td className="px-4 py-3 text-right">
                  <MasterRankCell row={row} />
                </td>

                {/* Segment-Pctl */}
                <td className="px-4 py-3 text-right tabular text-[var(--color-text-secondary)]">
                  {row.master_rank_pctl != null ? (
                    <span className="font-mono text-xs" title={`Percentil ${Math.round(row.master_rank_pctl)} i ${segmentLabel(row.segment)}`}>
                      {Math.round(row.master_rank_pctl)}%
                    </span>
                  ) : (
                    <span className="text-[var(--color-text-muted)]">—</span>
                  )}
                </td>

                {/* Totalbetyg */}
                <td className="px-4 py-3 text-right">
                  <ScoreChip score={row.score_total} />
                </td>

                {/* Köpläge */}
                <td className="px-4 py-3">
                  <span className={cn("px-2 py-0.5 rounded text-[11px] font-medium", signalClass(row.entry_signal))}>
                    {signalLabel(row.entry_signal)}
                  </span>
                </td>

                {/* Trend — fallback till trend_tech från MasterRank när trend_signal saknas */}
                <td className="px-4 py-3">
                  <TrendBadge trend={row.trend_signal ?? row.trend_tech} />
                </td>

                {/* Kurs */}
                <td className="px-4 py-3 tabular text-right text-[var(--color-text-primary)]">
                  {formatPrice(row.price, row.currency ?? "USD")}
                </td>

                {/* Idag */}
                <td className={cn("px-4 py-3 tabular text-right font-medium", changeClass(row.change_pct))}>
                  {formatPctChange(row.change_pct)}
                </td>

                {/* Börsvärde — lagras i USD (FX-normaliserat) */}
                <td className="px-4 py-3 tabular text-right text-[var(--color-text-secondary)]" title="Börsvärde i USD (FX-normaliserat)">
                  {formatMarketCap(row.market_cap, "USD")}
                </td>

                {/* P/E — visar Trailing P/E med fallback till Forward P/E om tomt */}
                <td className="px-4 py-3 tabular text-right text-[var(--color-text-secondary)]">
                  {(() => {
                    const pe = formatPE(
                      row.pe_trailing_raw ?? row.pe_trailing,
                      row.pe_forward_raw ?? row.pe_forward
                    );
                    return (
                      <span className={cn(pe.isForward ? "text-[var(--color-text-muted)] text-[11px] italic" : "")}
                            title={pe.isForward ? "Forward P/E (prognos)" : "Trailing P/E (senaste 12 mån)"}>
                        {pe.text}
                      </span>
                    );
                  })()}
                </td>

                {/* ROE — visar endast RÅ värde, inklusive negativa tal */}
                <td className="px-4 py-3 text-right tabular">
                  {(() => {
                    const v = row.roe_raw;
                    if (v == null || !Number.isFinite(v)) {
                      return (
                        <span className="text-[var(--color-text-muted)] inline-flex items-center justify-end gap-1" title="Rå ROE saknas">
                          —
                        </span>
                      );
                    }
                    const isNeg = v < 0;
                    return (
                      <span className={cn(isNeg ? "text-[var(--color-down)]" : "text-[var(--color-text-secondary)]")}
                            title={isNeg ? "Negativt ROE (förlustperiod/nedskrivning)" : "Rå ROE"}>
                        {(v * 100).toFixed(0)}%
                      </span>
                    );
                  })()}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {sorted.length === 0 && !loading && (
        <div className="py-16 text-center space-y-2">
          <div className="text-sm font-semibold text-[var(--color-text-primary)]">
            Inga aktier matchar dina filter
          </div>
          <p className="text-xs text-[var(--color-text-muted)]">
            Prova att bredda kriterierna eller välj en förinställning ovan.
          </p>
          {onReset && (
            <button
              onClick={onReset}
              className="mt-2 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium
                         bg-[var(--color-accent)] text-white hover:bg-[var(--color-accent-hover)] transition-colors"
            >
              Återställ filter
            </button>
          )}
        </div>
      )}

      <div className="px-4 py-2 border-t flex justify-between items-center border-[var(--color-border)]">
        <span className="text-xs text-[var(--color-text-muted)]">
          {sorted.length} aktier
        </span>
        <span className="text-xs text-[var(--color-text-muted)]">
          Piltangenter + Enter för tangentbordsnavigering
        </span>
      </div>
    </div>
  );
}

// U-8: Column header tooltips — explanations for each metric
const COL_TIPS: Partial<Record<string, string>> = {
  MasterRank: "Kvantitativ faktormodell (0–100) kalibrerad per segment med datatäthets-tak och multi-faktor-regim. Till skillnad från Totalbetyg anpassas trösklarna för småbolag.",
  Pctl: "MasterRank-percentil (0–100) inom aktiens storlekssegment. Möjliggör direkt jämförelse mellan olika segment.",
  Totalbetyg: "Linjär sammanvägning av 8 delbetyg (0–100) från den breda scanning-motorn: Värde, Kvalitet, Momentum, Tillväxt, Risk, Storlek, Utdelning och Sentiment.",
  Köpläge: "Visar rankläge baserat på aktiens långsiktiga kvalitets-, tillväxt- och värderingsprofil (T1=Stark, T2=Bra, T3=Vänta). I MarketScan v2 separeras detta i Långsiktig Thesis och Kortsiktig Setup.",
  Trend: "Aktiens pristrend de senaste 3–6 månaderna. Upptrend = stigande mönster. Nedtrend = fallande. Sidled = utan tydlig riktning.",
  Börsvärde: "Aktiekursen multiplicerat med antalet aktier — hur mycket hela bolaget värderas till på börsen (normaliserat till USD).",
  "P/E": "Price/Earnings — aktiekursen delat med vinst per aktie (senaste 12 mån). Lägre = billigare relativt vinsten. Negativt = bolaget går med förlust.",
  ROE: "Return on Equity — hur mycket vinst bolaget genererar per investerad krona av eget kapital (visar uteslutande verkligt råvärde).",
};

function Th({
  label, width, sortKey, sort, onSort, align = "left", tip: propTip,
}: {
  label: string;
  width?: string;
  sortKey?: SortKey;
  sort?: { key: SortKey; dir: SortDir };
  onSort?: (k: SortKey) => void;
  align?: "left" | "right";
  tip?: string;
}) {
  const active = sortKey && sort?.key === sortKey;
  const tip = propTip ?? COL_TIPS[label];
  return (
    <th
      style={{ width }}
      className={cn(
        "px-4 py-2.5 text-[11px] font-medium whitespace-nowrap select-none",
        align === "right" ? "text-right" : "text-left",
        sortKey ? "cursor-pointer hover:text-[var(--color-text-primary)]" : "",
        active ? "text-[var(--color-accent)]" : "text-[var(--color-text-muted)]",
      )}
      onClick={() => sortKey && onSort?.(sortKey)}
    >
      <span className="inline-flex items-center gap-0.5">
        {label}
        {tip && <InfoTooltip text={tip} side="bottom" />}
        {active && <span className="ml-1">{sort?.dir === "desc" ? "↓" : "↑"}</span>}
      </span>
    </th>
  );
}

function ScoreChip({ score }: { score: number | null | undefined }) {
  if (score == null) return <span className="text-[var(--color-text-muted)]">—</span>;
  const cls =
    score >= 70
      ? "score-chip-high"
      : score >= 50
      ? "score-chip-mid"
      : "score-chip-low";
  return (
    <span className={cn("px-2 py-0.5 rounded font-mono font-semibold text-xs", cls)}>
      {Math.round(score)}
    </span>
  );
}

function MasterRankCell({ row }: { row: ScanRow }) {
  if (row.master_rank == null) return <span className="text-[var(--color-text-muted)]">—</span>;
  const cls =
    row.master_rank >= 70
      ? "score-chip-high"
      : row.master_rank >= 50
      ? "score-chip-mid"
      : "score-chip-low";

  const details = [
    row.master_tier ? `Tier: ${row.master_tier}` : null,
    row.quality_z != null ? `Kvalitet: ${Math.round(row.quality_z)}` : null,
    row.value_z != null ? `Värde: ${Math.round(row.value_z)}` : null,
    row.momentum_z != null ? `Momentum: ${Math.round(row.momentum_z)}` : null,
    row.analyst_z != null
      ? `Analytiker: ${Math.round(row.analyst_z)}${row.analyst_upside != null ? ` (${row.analyst_upside > 0 ? "+" : ""}${row.analyst_upside.toFixed(0)}%)` : ""}`
      : null,
  ]
    .filter(Boolean)
    .join(" • ");

  return (
    <span
      className={cn("px-2 py-0.5 rounded font-mono font-semibold text-xs cursor-help", cls)}
      title={details || "MasterRank (0–100)"}
    >
      {Math.round(row.master_rank)}
    </span>
  );
}

function TrendBadge({ trend }: { trend: string | null | undefined }) {
  if (!trend) return <span className="text-[var(--color-text-muted)]">—</span>;
  const icon =
    trend === "Upptrend" ? <TrendingUp size={12} strokeWidth={1.5} className="text-[var(--color-up)]" /> :
    trend === "Nedtrend" ? <TrendingDown size={12} strokeWidth={1.5} className="text-[var(--color-down)]" /> :
    <Minus size={12} strokeWidth={1.5} className="text-[var(--color-text-muted)]" />;
  return (
    <div className="flex items-center gap-1 text-[var(--color-text-secondary)]">
      {icon}
      <span>{trendLabel(trend)}</span>
    </div>
  );
}

function TableSkeleton() {
  return (
    <div className="rounded-xl overflow-hidden border border-[var(--color-border)]">
      {Array.from({ length: 8 }).map((_, i) => (
        <div key={i} className="flex gap-4 px-4 py-3 border-b border-[var(--color-border)]">
          <div className="skeleton h-4 w-32" />
          <div className="skeleton h-4 w-20 ml-auto" />
          <div className="skeleton h-4 w-16" />
          <div className="skeleton h-4 w-20" />
          <div className="skeleton h-4 w-16" />
        </div>
      ))}
    </div>
  );
}
