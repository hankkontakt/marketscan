"use client";

import {
  RadarChart, PolarGrid, PolarAngleAxis, Radar,
  ResponsiveContainer, Tooltip,
} from "recharts";
import type { ScanRow } from "@/types/scan";

interface Props {
  stock: ScanRow;
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

export function FactorRadar({ stock }: Props) {
  const data = FACTORS.map(({ key, label }) => ({
    factor: label,
    value: stock[key] ?? 0,
  }));

  return (
    <ResponsiveContainer width="100%" height={240}>
      <RadarChart data={data} margin={{ top: 10, right: 20, bottom: 10, left: 20 }}>
        <PolarGrid stroke="var(--color-border)" />
        <PolarAngleAxis
          dataKey="factor"
          tick={{ fill: "var(--color-text-secondary)", fontSize: 11, fontFamily: "Geist, sans-serif" }}
        />
        <Radar
          dataKey="value"
          stroke="var(--color-accent)"
          fill="var(--color-accent)"
          fillOpacity={0.12}
          strokeWidth={1.5}
        />
        <Tooltip
          contentStyle={{
            background: "var(--color-bg-elevated)",
            border: "1px solid var(--color-border)",
            borderRadius: 8,
            fontSize: 12,
            fontFamily: "Geist Mono, monospace",
            color: "var(--color-text-primary)",
          }}
          formatter={(v: number) => [Math.round(v), "Betyg"]}
        />
      </RadarChart>
    </ResponsiveContainer>
  );
}
