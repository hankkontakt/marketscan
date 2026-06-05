"use client";

import { useEffect, useRef, useState } from "react";
import type { IChartApi, ISeriesApi } from "lightweight-charts";

interface Candle {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

interface Props {
  candles: Candle[];
  height?: number;
}

const PERIODS = ["1M", "3M", "6M", "1Å", "MAX"] as const;

export function PriceChart({ candles, height = 300 }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const [period, setPeriod] = useState<"1M" | "3M" | "6M" | "1Å" | "MAX">("3M");

  useEffect(() => {
    if (!containerRef.current || typeof window === "undefined") return;

    let chart: IChartApi;

    import("lightweight-charts").then(({ createChart, CrosshairMode }) => {
      if (!containerRef.current) return;
      chart = createChart(containerRef.current, {
        height,
        layout: {
          background: { color: "transparent" },
          textColor: "#9AA1AC",
          fontFamily: "Geist Mono, monospace",
          fontSize: 11,
        },
        grid: {
          vertLines: { color: "#262A31", style: 1 },
          horzLines: { color: "#262A31", style: 1 },
        },
        crosshair: { mode: CrosshairMode.Normal },
        rightPriceScale: {
          borderColor: "#262A31",
        },
        timeScale: {
          borderColor: "#262A31",
          timeVisible: true,
          secondsVisible: false,
        },
      });

      const candleSeries = chart.addCandlestickSeries({
        upColor: "#3FB68B",
        downColor: "#E0645C",
        borderUpColor: "#3FB68B",
        borderDownColor: "#E0645C",
        wickUpColor: "#3FB68B",
        wickDownColor: "#E0645C",
      });

      seriesRef.current = candleSeries;
      chartRef.current = chart;

      updateData(candleSeries, period);

      const ro = new ResizeObserver(() => {
        if (containerRef.current) {
          chart.applyOptions({ width: containerRef.current.clientWidth });
        }
      });
      ro.observe(containerRef.current);
      return () => ro.disconnect();
    });

    return () => chart?.remove();
  }, [candles]);

  function updateData(series: ISeriesApi<"Candlestick">, p: typeof period) {
    const filtered = filterByPeriod(candles, p);
    series.setData(filtered.map((c) => ({
      time: c.time,
      open: c.open, high: c.high, low: c.low, close: c.close,
    })));
    chartRef.current?.timeScale().fitContent();
  }

  function changePeriod(p: typeof period) {
    setPeriod(p);
    if (seriesRef.current) updateData(seriesRef.current, p);
  }

  return (
    <div className="space-y-2">
      <div className="flex gap-1">
        {PERIODS.map((p) => (
          <button
            key={p}
            onClick={() => changePeriod(p)}
            className={`px-2.5 py-0.5 rounded text-xs font-mono transition-colors ${
              period === p
                ? "bg-[var(--color-accent)] text-white"
                : "text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]"
            }`}
          >
            {p}
          </button>
        ))}
      </div>
      <div ref={containerRef} style={{ height }} />
    </div>
  );
}

function filterByPeriod(candles: Candle[], period: string): Candle[] {
  if (period === "MAX") return candles;
  const now = new Date();
  const cutoff = new Date(now);
  if (period === "1M") cutoff.setMonth(now.getMonth() - 1);
  else if (period === "3M") cutoff.setMonth(now.getMonth() - 3);
  else if (period === "6M") cutoff.setMonth(now.getMonth() - 6);
  else if (period === "1Å") cutoff.setFullYear(now.getFullYear() - 1);
  const cutStr = cutoff.toISOString().slice(0, 10);
  return candles.filter((c) => c.time >= cutStr);
}
