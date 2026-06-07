"use client";

import {
  RadarChart, PolarGrid, PolarAngleAxis, Radar,
  ResponsiveContainer, Tooltip, Legend,
} from "recharts";
import { cn } from "@/lib/utils";

interface MultiFactorRadarProps {
  series: {
    ticker: string;
    values: Record<string, number>;
    color: string;
  }[];
}

const FACTORS = [
  { key: "score_value",     label: "Värde" },
  { key: "score_quality",   label: "Kvalitet" },
  { key: "score_momentum",  label: "Momentum" },
  { key: "score_growth",    label: "Tillväxt" },
  { key: "score_risk",      label: "Risk" },
  { key: "score_dividend",  label: "Utdelning" },
  { key: "score_sentiment", label: "Sentiment" },
  { key: "score_size",      label: "Storlek" },
] as const;

export function MultiFactorRadar({ series }: MultiFactorRadarProps) {
  const numSeries = series.length;
  const useFill = numSeries <= 3;

  const data = FACTORS.map(({ key, label }) => {
    const point: Record<string, string | number> = { factor: label };
    for (const s of series) {
      point[s.ticker] = s.values[key] ?? 0;
    }
    return point;
  });

  if (series.length === 0) return null;

  return (
    <ResponsiveContainer width="100%" height={280}>
      <RadarChart data={data} margin={{ top: 10, right: 20, bottom: 10, left: 20 }}>
        <PolarGrid stroke="var(--color-border)" />
        <PolarAngleAxis
          dataKey="factor"
          tick={{ fill: "var(--color-text-secondary)", fontSize: 11, fontFamily: "Inter, sans-serif" }}
        />
        <Tooltip
          contentStyle={{
            background: "var(--color-bg-elevated)",
            border: "1px solid var(--color-border)",
            borderRadius: 8,
            fontSize: 12,
            color: "var(--color-text-primary)",
          }}
        />
        <Legend
          wrapperStyle={{ fontSize: 11, color: "var(--color-text-secondary)", paddingTop: 8 }}
        />
        {series.map((s) => (
          <Radar
            key={s.ticker}
            name={s.ticker}
            dataKey={s.ticker}
            stroke={s.color}
            fill={useFill ? s.color : "transparent"}
            fillOpacity={useFill ? 0.08 : 0}
            strokeWidth={useFill ? 1.5 : 2}
          />
        ))}
      </RadarChart>
    </ResponsiveContainer>
  );
}

export const TICKER_COLORS = [
  "var(--color-accent)",
  "var(--color-up)",
  "var(--color-score-mid)",
  "var(--color-score-low)",
  "var(--color-text-muted)",
];

export function tickerColor(index: number): string {
  return TICKER_COLORS[index % TICKER_COLORS.length];
}
