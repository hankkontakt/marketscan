"use client";

import { cn } from "@/lib/utils";

interface Series {
  ticker: string;
  values: Record<string, number | null | undefined>;
  color: string;
}

interface MultiFactorRadarProps {
  series: Series[];
}

// ─── Factor config ─────────────────────────────────────────────────────────

const FACTORS = [
  { key: "score_value",     label: "Värde",     tip: "Värdering relativt vinst, bok och kassaflöde" },
  { key: "score_quality",   label: "Kvalitet",  tip: "Lönsamhet, skuldsättning och bokföringskvalitet" },
  { key: "score_momentum",  label: "Momentum",  tip: "Kurs- och vinstrevisions-momentum" },
  { key: "score_growth",    label: "Tillväxt",  tip: "Intäkts- och vinsttillväxt" },
  { key: "score_risk",      label: "Risk",      tip: "Riskjusterat betyg — högt = lägre risk" },
  { key: "score_dividend",  label: "Utdelning", tip: "Direktavkastning och utdelningsstabilitet" },
  { key: "score_sentiment", label: "Sentiment", tip: "Analytikersentiment och insideraktivitet" },
] as const;

// ─── Color helpers ──────────────────────────────────────────────────────────

export const TICKER_COLORS = [
  "#3b82f6",   // blue
  "#22c55e",   // green
  "#f97316",   // orange
  "#a855f7",   // purple
  "#ef4444",   // red
];

export function tickerColor(index: number): string {
  return TICKER_COLORS[index % TICKER_COLORS.length];
}

function scoreColor(v: number): string {
  if (v >= 70) return "#22c55e";
  if (v >= 50) return "#84cc16";
  if (v >= 35) return "#eab308";
  return "#ef4444";
}

// ─── Single factor row ──────────────────────────────────────────────────────

function FactorRow({
  label,
  tip,
  series,
}: {
  label: string;
  tip: string;
  series: { ticker: string; value: number | null; color: string }[];
}) {
  // Find the best value to highlight
  const validVals = series.filter((s) => s.value != null).map((s) => s.value as number);
  const max = validVals.length > 0 ? Math.max(...validVals) : null;

  return (
    <div className="grid items-center gap-x-3 py-2.5 border-b border-[var(--color-border)] last:border-0"
      style={{ gridTemplateColumns: `7rem 1fr` }}>
      {/* Factor label */}
      <div className="flex items-center gap-1 min-w-0">
        <span className="text-xs font-medium text-[var(--color-text-secondary)] truncate">{label}</span>
        <span className="relative group cursor-help shrink-0">
          <span className="text-[9px] w-3.5 h-3.5 rounded-full bg-[var(--color-bg-elevated)] text-[var(--color-text-muted)] flex items-center justify-center">?</span>
          <span className="absolute left-5 top-1/2 -translate-y-1/2 z-10 hidden group-hover:block
                           w-44 text-[11px] text-[var(--color-text-secondary)] bg-[var(--color-bg-card)]
                           border border-[var(--color-border-strong)] rounded-lg px-2.5 py-2 shadow-lg pointer-events-none">
            {tip}
          </span>
        </span>
      </div>

      {/* Bars */}
      <div className="space-y-1.5">
        {series.map(({ ticker, value, color }) => {
          const hasData = value != null;
          const pct = hasData ? Math.min(Math.max(value, 0), 100) : 0;
          const isWinner = hasData && value === max && validVals.length > 1;

          return (
            <div key={ticker} className="flex items-center gap-2">
              {/* Ticker tag */}
              <span
                className="text-[10px] font-mono font-semibold w-14 shrink-0 text-right"
                style={{ color }}
              >
                {ticker}
              </span>

              {hasData ? (
                <>
                  {/* Bar track */}
                  <div className="flex-1 h-4 rounded bg-[var(--color-bg-elevated)] overflow-hidden relative">
                    <div
                      className="h-full rounded transition-all duration-500"
                      style={{
                        width: `${pct}%`,
                        backgroundColor: isWinner ? color : `${color}99`,
                      }}
                    />
                  </div>
                  {/* Score value */}
                  <span
                    className={cn(
                      "text-xs font-mono tabular-nums w-7 text-right shrink-0 font-semibold",
                      isWinner ? "text-[var(--color-text-primary)]" : "text-[var(--color-text-muted)]",
                    )}
                    style={isWinner ? { color } : undefined}
                  >
                    {Math.round(pct)}
                  </span>
                </>
              ) : (
                <>
                  <div className="flex-1 h-4 rounded bg-[var(--color-bg-elevated)]">
                    <div className="h-full flex items-center px-2">
                      <span className="text-[10px] text-[var(--color-text-muted)]">Ej tillgänglig</span>
                    </div>
                  </div>
                  <span className="text-xs font-mono tabular-nums w-7 text-right text-[var(--color-text-muted)]">–</span>
                </>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ─── Main component ─────────────────────────────────────────────────────────

export function MultiFactorRadar({ series }: MultiFactorRadarProps) {
  if (series.length === 0) return null;

  // Filter to only factors where at least one series has a non-null value
  const activeFactors = FACTORS.filter(({ key }) =>
    series.some((s) => {
      const v = s.values[key];
      return v != null && v > 0;
    }),
  );

  if (activeFactors.length === 0) {
    return (
      <div className="py-8 text-center text-xs text-[var(--color-text-muted)]">
        Ingen faktordata tillgänglig för valda aktier
      </div>
    );
  }

  return (
    <div className="w-full">
      {/* Scale header */}
      <div className="grid items-center gap-x-3 mb-1 pb-1 border-b border-[var(--color-border-strong)]"
        style={{ gridTemplateColumns: `7rem 1fr` }}>
        <span />
        <div className="pl-16 flex items-center gap-0 text-[10px] text-[var(--color-text-muted)]">
          <span>0</span>
          <div className="flex-1 mx-1 flex justify-between">
            <span className="opacity-0">|</span>
            <span>50</span>
            <span className="opacity-0">|</span>
          </div>
          <span>100</span>
        </div>
      </div>

      {/* Factor rows */}
      <div>
        {activeFactors.map(({ key, label, tip }) => (
          <FactorRow
            key={key}
            label={label}
            tip={tip}
            series={series.map((s) => ({
              ticker: s.ticker,
              value: s.values[key] ?? null,
              color: s.color,
            }))}
          />
        ))}
      </div>

      {/* Scale footer */}
      <div className="mt-2 flex items-center gap-2 flex-wrap text-[10px] text-[var(--color-text-muted)]">
        <span>Skala 0–100 poäng.</span>
        <span>Starkare färg = bäst i jämförelsen.</span>
        <span className="flex items-center gap-1">
          {series.map((s, i) => (
            <span key={s.ticker} className="flex items-center gap-1 mr-2">
              <span className="w-2.5 h-2.5 rounded-sm inline-block" style={{ background: s.color }} />
              {s.ticker}
            </span>
          ))}
        </span>
      </div>
    </div>
  );
}
