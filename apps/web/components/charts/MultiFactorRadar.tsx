"use client";

import { useState } from "react";
import { BarChart2, Radar as RadarIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";

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

// ─── Bar chart — single factor row ──────────────────────────────────────────

function FactorRow({
  label,
  tip,
  series,
}: {
  label: string;
  tip: string;
  series: { ticker: string; value: number | null; color: string }[];
}) {
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
              <span
                className="text-[10px] font-mono font-semibold w-14 shrink-0 text-right"
                style={{ color }}
              >
                {ticker}
              </span>

              {hasData ? (
                <>
                  <div className="flex-1 h-4 rounded bg-[var(--color-bg-elevated)] overflow-hidden relative">
                    <div
                      className="h-full rounded transition-all duration-500"
                      style={{
                        width: `${pct}%`,
                        backgroundColor: isWinner ? color : `${color}99`,
                      }}
                    />
                  </div>
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

// ─── Bar chart view ──────────────────────────────────────────────────────────

function BarView({ series, activeFactors }: {
  series: Series[];
  activeFactors: typeof FACTORS[number][];
}) {
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

      {/* Footer */}
      <div className="mt-2 flex items-center gap-2 flex-wrap text-[10px] text-[var(--color-text-muted)]">
        <span>Skala 0–100 poäng.</span>
        <span>Starkare färg = bäst i jämförelsen.</span>
        <span className="flex items-center gap-1">
          {series.map((s) => (
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

// ─── Radar polygon view ──────────────────────────────────────────────────────

// Custom axis label that shows factor name + all ticker values
function RadarAxisTick({ x, y, payload, series, activeFactors }: any) {
  const factor = activeFactors.find((f: any) => f.label === payload.value);
  if (!factor) return null;

  const values = series.map((s: Series) => {
    const v = s.values[factor.key];
    return { ticker: s.ticker, value: v != null && v > 0 ? Math.round(v) : null, color: s.color };
  });

  // Position label relative to chart centre (cx/cy are passed via payload but we compute offset)
  const cx = 0;
  const cy = 0;

  const textAnchor =
    Math.abs(x - cx) < 10 ? "middle" : x > cx ? "start" : "end";

  return (
    <g>
      {/* Factor name */}
      <text
        x={x}
        y={y}
        textAnchor={textAnchor}
        dominantBaseline="central"
        style={{ fontSize: 11, fontWeight: 600, fill: "var(--color-text-secondary)" }}
      >
        {payload.value}
      </text>
      {/* Per-ticker score badges below the label */}
      {values.map((v: any, i: number) => (
        <text
          key={v.ticker}
          x={x}
          y={y + 14 + i * 13}
          textAnchor={textAnchor}
          style={{ fontSize: 10, fontFamily: "monospace", fill: v.value != null ? v.color : "var(--color-text-muted)" }}
        >
          {v.value != null ? v.value : "—"}
        </text>
      ))}
    </g>
  );
}

function RadarView({ series, activeFactors }: {
  series: Series[];
  activeFactors: typeof FACTORS[number][];
}) {
  // Build data array: one entry per factor
  const data = activeFactors.map(({ key, label }) => {
    const entry: Record<string, string | number> = { subject: label };
    for (const s of series) {
      const v = s.values[key];
      // Use 0 for null (polygon closes at origin) — tooltip shows "—" for nulls
      entry[s.ticker] = v != null && v > 0 ? v : 0;
      entry[`${s.ticker}_raw`] = v != null && v > 0 ? v : -1; // -1 = no data
    }
    return entry;
  });

  // Determine fill opacities — more opaque when fewer series
  const fillOp = series.length === 1 ? 0.25 : series.length === 2 ? 0.15 : 0.10;

  // Custom tooltip
  const CustomTooltip = ({ active, payload, label }: any) => {
    if (!active || !payload?.length) return null;
    return (
      <div
        className="rounded-xl border shadow-lg px-3 py-2.5 text-xs space-y-1"
        style={{
          background: "var(--color-bg-elevated)",
          borderColor: "var(--color-border-strong)",
          minWidth: 120,
        }}
      >
        <div className="font-semibold text-[var(--color-text-primary)] mb-1.5">{label}</div>
        {payload.map((p: any) => {
          // find raw value
          const raw = data.find((d) => d.subject === label)?.[`${p.dataKey}_raw`];
          const display = (raw as number) >= 0 ? Math.round(raw as number) : "—";
          return (
            <div key={p.dataKey} className="flex items-center gap-2 justify-between">
              <span className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full inline-block" style={{ background: p.color }} />
                <span style={{ color: "var(--color-text-secondary)" }}>{p.dataKey}</span>
              </span>
              <span className="font-mono font-semibold tabular-nums" style={{ color: p.color }}>
                {display}
              </span>
            </div>
          );
        })}
      </div>
    );
  };

  return (
    <div className="w-full">
      {/* Extra vertical space for axis labels with score values */}
      <ResponsiveContainer width="100%" height={320}>
        <RadarChart
          data={data}
          margin={{ top: 20, right: 40, bottom: 20, left: 40 }}
        >
          <PolarGrid
            gridType="polygon"
            stroke="var(--color-border)"
            strokeOpacity={0.8}
          />
          {/* Radius axis: tick marks at 25, 50, 75, 100 */}
          <PolarRadiusAxis
            angle={90}
            domain={[0, 100]}
            tickCount={5}
            tick={{ fontSize: 9, fill: "var(--color-text-muted)" }}
            stroke="transparent"
            tickFormatter={(v) => (v === 0 ? "" : String(v))}
          />
          <PolarAngleAxis
            dataKey="subject"
            tick={(props) => (
              <RadarAxisTick {...props} series={series} activeFactors={activeFactors} />
            )}
            tickLine={false}
          />

          {series.map((s) => (
            <Radar
              key={s.ticker}
              name={s.ticker}
              dataKey={s.ticker}
              stroke={s.color}
              strokeWidth={2}
              fill={s.color}
              fillOpacity={fillOp}
              dot={{ r: 3, fill: s.color, strokeWidth: 0 }}
              activeDot={{ r: 5, fill: s.color }}
            />
          ))}

          <Tooltip content={<CustomTooltip />} />

          {series.length > 1 && (
            <Legend
              wrapperStyle={{ fontSize: 11, color: "var(--color-text-secondary)", paddingTop: 4 }}
              formatter={(value) => (
                <span style={{ color: series.find((s) => s.ticker === value)?.color }}>{value}</span>
              )}
            />
          )}
        </RadarChart>
      </ResponsiveContainer>

      <p className="text-[10px] text-[var(--color-text-muted)] text-center -mt-2">
        Skala 0–100. Siffror vid axlarna = betyg per aktie.
        {series.some((s) => activeFactors.some((f) => !(s.values[f.key] ?? null))) && (
          <span> Prickade axlar saknar data.</span>
        )}
      </p>
    </div>
  );
}

// ─── Main component ─────────────────────────────────────────────────────────

export function MultiFactorRadar({ series }: MultiFactorRadarProps) {
  const [view, setView] = useState<"bar" | "radar">("bar");

  if (series.length === 0) return null;

  // Filter to factors where at least one series has data
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
      {/* View toggle */}
      <div className="flex justify-end mb-3">
        <div className="flex p-0.5 rounded-lg bg-[var(--color-bg-elevated)]" style={{ border: "1px solid var(--color-border)" }}>
          <button
            onClick={() => setView("bar")}
            title="Stapelvy"
            className={cn(
              "flex items-center gap-1 px-2.5 py-1 rounded-md text-[11px] font-medium transition-colors",
              view === "bar"
                ? "bg-[var(--color-bg-surface)] text-[var(--color-accent)] shadow-sm"
                : "text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]",
            )}
          >
            <BarChart2 size={13} strokeWidth={1.5} />
            Stapel
          </button>
          <button
            onClick={() => setView("radar")}
            title="Radarvy"
            className={cn(
              "flex items-center gap-1 px-2.5 py-1 rounded-md text-[11px] font-medium transition-colors",
              view === "radar"
                ? "bg-[var(--color-bg-surface)] text-[var(--color-accent)] shadow-sm"
                : "text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]",
            )}
          >
            <RadarIcon size={13} strokeWidth={1.5} />
            Radar
          </button>
        </div>
      </div>

      {view === "bar"
        ? <BarView series={series} activeFactors={activeFactors} />
        : <RadarView series={series} activeFactors={activeFactors} />
      }
    </div>
  );
}
