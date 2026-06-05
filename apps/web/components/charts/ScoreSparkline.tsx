"use client";

import React from "react";

/**
 * Mini sparkline for score history in tables.
 * Plan §5.4: "Sparklines i tabeller: 1px linje, ingen axel, färgas av riktning"
 * Takes an array of 4–8 score values (oldest → newest).
 */

interface Props {
  values: number[];
  width?: number;
  height?: number;
}

export const ScoreSparkline = React.memo(function ScoreSparkline({ values, width = 48, height = 20 }: Props) {
  if (!values || values.length < 2) {
    return <div style={{ width, height }} />;
  }

  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;

  const pts = values.map((v, i) => {
    const x = (i / (values.length - 1)) * width;
    const y = height - ((v - min) / range) * (height - 2) - 1;
    return `${x},${y}`;
  });

  const last = values[values.length - 1];
  const first = values[0];
  const color =
    last > first + 2
      ? "var(--color-up)"
      : last < first - 2
      ? "var(--color-down)"
      : "var(--color-text-muted)";

  return (
    <svg width={width} height={height} style={{ overflow: "visible", display: "block" }}>
      <polyline
        points={pts.join(" ")}
        fill="none"
        stroke={color}
        strokeWidth={1.5}
        strokeLinejoin="round"
        strokeLinecap="round"
      />
      {/* Last dot */}
      <circle
        cx={width}
        cy={height - ((last - min) / range) * (height - 2) - 1}
        r={2}
        fill={color}
      />
    </svg>
  );
});

// Exported above via React.memo