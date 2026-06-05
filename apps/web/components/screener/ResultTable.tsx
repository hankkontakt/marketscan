"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { TrendingUp, TrendingDown, Minus, AlertTriangle } from "lucide-react";
import { ScoreSparkline } from "@/components/charts/ScoreSparkline";
import { cn } from "@/lib/utils";
import {
  formatPctChange,
  formatPrice,
  formatMarketCap,
  formatScore,
  formatNumber,
  signalLabel,
  signalClass,
  scoreColorClass,
  segmentLabel,
  changeClass,
  trendLabel,
} from "@/lib/format";
import type { ScanRow } from "@/types/scan";

interface Props {
  data: ScanRow[];
  loading?: boolean;
}

type SortKey = "score_total" | "change_pct" | "price" | "market_cap" | "pe_trailing" | "roe";
type SortDir = "asc" | "desc";

export function ResultTable({ data, loading }: Props) {
  const router = useRouter();
  const [sort, setSort] = useState<{ key: SortKey; dir: SortDir }>({
    key: "score_total",
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

  function openStock(ticker: string) {
    router.push(`/aktie/${ticker}`);
  }

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
    [sorted.length],
  );

  if (loading) return <TableSkeleton />;

  return (
    <div className="rounded-xl overflow-hidden border"
         style={{ borderColor: "var(--color-border)" }}>
      <div className="overflow-x-auto">
        <table className="w-full text-xs border-collapse">
          <thead>
            <tr style={{ background: "var(--color-bg-surface)", borderBottom: "1px solid var(--color-border)" }}>
              <Th label="Aktie" width="220px" />
              <Th label="Segment" width="110px" />
              <Th
                label="Totalbetyg"
                sortKey="score_total"
                sort={sort}
                onSort={toggleSort}
                width="90px"
                align="right"
              />
              {/* Score trend — awaiting R2 score history */}
              {/* <Th label="Trend (graf)" width="64px" /> */}
              <Th label="Köpläge" width="130px" />
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
                      <AlertTriangle size={12} strokeWidth={1.5}
                                     style={{ color: "var(--color-warn)", flexShrink: 0 }} />
                    )}
                    <div>
                      <div className="font-mono font-semibold text-[var(--color-text-primary)] text-xs">
                        {row.ticker}
                      </div>
                      <div className="text-[var(--color-text-muted)] text-[11px] truncate max-w-36">
                        {row.name}
                      </div>
                    </div>
                  </div>
                </td>

                {/* Segment */}
                <td className="px-4 py-3 text-[var(--color-text-muted)]">
                  {segmentLabel(row.segment)}
                </td>

                {/* Totalbetyg */}
                <td className="px-4 py-3 text-right">
                  <ScoreChip score={row.score_total} />
                </td>

              {/* Score trend — awaiting R2 score history */}
              {/* <td className="px-4 py-3">
                  <ScoreSparkline
                    values={row.score_total != null
                      ? [
                          Math.max(0, row.score_total - 6),
                          Math.max(0, row.score_total - 2),
                          row.score_total - 4,
                          row.score_total + 1,
                          row.score_total,
                        ]
                      : []}
                    width={44}
                    height={18}
                  />
                </td> */}

                {/* Köpläge */}
                <td className="px-4 py-3">
                  <span className={cn("px-2 py-0.5 rounded text-[11px] font-medium", signalClass(row.entry_signal))}>
                    {signalLabel(row.entry_signal)}
                  </span>
                </td>

                {/* Trend */}
                <td className="px-4 py-3">
                  <TrendBadge trend={row.trend_signal} />
                </td>

                {/* Kurs */}
                <td className="px-4 py-3 tabular text-right text-[var(--color-text-primary)]">
                  {formatPrice(row.price)}
                </td>

                {/* Idag */}
                <td className={cn("px-4 py-3 tabular text-right font-medium", changeClass(row.change_pct))}>
                  {formatPctChange(row.change_pct)}
                </td>

                {/* Börsvärde */}
                <td className="px-4 py-3 tabular text-right text-[var(--color-text-secondary)]">
                  {formatMarketCap(row.market_cap)}
                </td>

                {/* P/E */}
                <td className="px-4 py-3 tabular text-right text-[var(--color-text-secondary)]">
                  {row.pe_trailing ? formatNumber(row.pe_trailing, 1) : "—"}
                </td>

                {/* ROE */}
                <td className="px-4 py-3 tabular text-right text-[var(--color-text-secondary)]">
                  {row.roe ? `${(row.roe * 100).toFixed(0)}%` : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {sorted.length === 0 && (
        <div className="py-16 text-center text-sm text-[var(--color-text-muted)]">
          Inga aktier matchade dina filter
        </div>
      )}

      <div className="px-4 py-2 border-t flex justify-between items-center"
           style={{ borderColor: "var(--color-border)" }}>
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

function Th({
  label, width, sortKey, sort, onSort, align = "left",
}: {
  label: string;
  width?: string;
  sortKey?: SortKey;
  sort?: { key: SortKey; dir: SortDir };
  onSort?: (k: SortKey) => void;
  align?: "left" | "right";
}) {
  const active = sortKey && sort?.key === sortKey;
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
      {label}
      {active && <span className="ml-1">{sort?.dir === "desc" ? "↓" : "↑"}</span>}
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

function TrendBadge({ trend }: { trend: string | null | undefined }) {
  if (!trend) return <span className="text-[var(--color-text-muted)]">—</span>;
  const icon =
    trend === "Upptrend" ? <TrendingUp size={12} strokeWidth={1.5} style={{ color: "var(--color-up)" }} /> :
    trend === "Nedtrend" ? <TrendingDown size={12} strokeWidth={1.5} style={{ color: "var(--color-down)" }} /> :
    <Minus size={12} strokeWidth={1.5} style={{ color: "var(--color-text-muted)" }} />;
  return (
    <div className="flex items-center gap-1 text-[var(--color-text-secondary)]">
      {icon}
      <span>{trendLabel(trend)}</span>
    </div>
  );
}

function TableSkeleton() {
  return (
    <div className="rounded-xl overflow-hidden border" style={{ borderColor: "var(--color-border)" }}>
      {Array.from({ length: 8 }).map((_, i) => (
        <div key={i} className="flex gap-4 px-4 py-3 border-b"
             style={{ borderColor: "var(--color-border)" }}>
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
