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
        <PolarGrid stroke="#262A31" />
        <PolarAngleAxis
          dataKey="factor"
          tick={{ fill: "#9AA1AC", fontSize: 11, fontFamily: "Geist, sans-serif" }}
        />
        <Radar
          dataKey="value"
          stroke="#5B8DEF"
          fill="#5B8DEF"
          fillOpacity={0.12}
          strokeWidth={1.5}
        />
        <Tooltip
          contentStyle={{
            background: "#1B1E24",
            border: "1px solid #262A31",
            borderRadius: 8,
            fontSize: 12,
            fontFamily: "Geist Mono, monospace",
          }}
          formatter={(v: number) => [Math.round(v), "Betyg"]}
        />
      </RadarChart>
    </ResponsiveContainer>
  );
}
