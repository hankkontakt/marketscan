"use client";

import { useEffect, useRef, useState } from "react";
import type { IChartApi, ISeriesApi, HistogramSeriesPartialOptions } from "lightweight-charts";
import { useTheme } from "@/hooks/useTheme";

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
  const { resolved } = useTheme();

  useEffect(() => {
    if (!containerRef.current || typeof window === "undefined") return;

    let chart: IChartApi;

    import("lightweight-charts").then(({ createChart, CrosshairMode }) => {
      if (!containerRef.current) return;

      // Read theme from useTheme hook (reacts to toggle)
      const isDark = resolved === "dark";
      const gridColor   = isDark ? "#262A31" : "#E3E6EC";
      const textColor   = isDark ? "#9AA1AC" : "#4A5567";
      const upColor     = isDark ? "#3FB68B" : "#15803D";
      const downColor   = isDark ? "#E0645C" : "#DC2626";
      const ma50Color   = isDark ? "rgba(217,164,65,0.7)"  : "rgba(180,83,9,0.6)";
      const ma200Color  = isDark ? "rgba(91,141,239,0.7)"  : "rgba(29,78,216,0.6)";
      const volColor    = isDark ? "rgba(91,141,239,0.25)" : "rgba(29,78,216,0.15)";

      chart = createChart(containerRef.current, {
        height,
        layout: {
          background: { color: "transparent" },
          textColor,
          fontFamily: "Inter, system-ui, sans-serif",
          fontSize: 11,
        },
        grid: {
          vertLines: { color: gridColor, style: 1 },
          horzLines: { color: gridColor, style: 1 },
        },
        crosshair: { mode: CrosshairMode.Normal },
        rightPriceScale: { borderColor: gridColor },
        timeScale: { borderColor: gridColor, timeVisible: true, secondsVisible: false },
      });

      const candleSeries = chart.addCandlestickSeries({
        upColor, downColor,
        borderUpColor: upColor, borderDownColor: downColor,
        wickUpColor: upColor,   wickDownColor: downColor,
        priceScaleId: "right",
      });

      // Volume bars
      const volumeSeries = chart.addHistogramSeries({
        priceScaleId: "volume",
        color: volColor,
        priceFormat: { type: "volume" },
      });
      chart.priceScale("volume").applyOptions({
        scaleMargins: { top: 0.8, bottom: 0 },
      });

      // MA50 line
      const ma50Series = chart.addLineSeries({
        color: ma50Color, lineWidth: 1, priceScaleId: "right",
        crosshairMarkerVisible: false, lastValueVisible: false, priceLineVisible: false,
      });

      // MA200 line
      const ma200Series = chart.addLineSeries({
        color: ma200Color, lineWidth: 1, priceScaleId: "right",
        crosshairMarkerVisible: false, lastValueVisible: false, priceLineVisible: false,
      });

      seriesRef.current = candleSeries;
      chartRef.current = chart;

      // Store extra series refs for data updates
      (chart as unknown as Record<string, unknown>)._volumeSeries = volumeSeries;
      (chart as unknown as Record<string, unknown>)._ma50 = ma50Series;
      (chart as unknown as Record<string, unknown>)._ma200 = ma200Series;

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

    // Volume
    const chart = chartRef.current as unknown as Record<string, unknown>;
    if (chart?._volumeSeries) {
      (chart._volumeSeries as ISeriesApi<"Histogram">).setData(
        filtered.map((c) => ({
          time: c.time,
          value: c.volume,
          color: c.close >= c.open ? "rgba(63,182,139,0.3)" : "rgba(224,100,92,0.3)",
        }))
      );
    }

    // MA helper
    function calcMA(data: Candle[], n: number) {
      return data.map((_, i) => {
        if (i < n - 1) return null;
        const slice = data.slice(i - n + 1, i + 1);
        return { time: data[i].time, value: slice.reduce((s, c) => s + c.close, 0) / n };
      }).filter(Boolean);
    }

    if (chart?._ma50) {
      (chart._ma50 as ISeriesApi<"Line">).setData(calcMA(filtered, 50) as Parameters<ISeriesApi<"Line">["setData"]>[0]);
    }
    if (chart?._ma200) {
      (chart._ma200 as ISeriesApi<"Line">).setData(calcMA(filtered, 200) as Parameters<ISeriesApi<"Line">["setData"]>[0]);
    }

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
      {/* MA legend */}
      <div className="flex items-center gap-3 text-[10px]" style={{ color: "var(--color-text-muted)" }}>
        <span className="flex items-center gap-1">
          <span className="inline-block w-4 h-0.5 rounded" style={{ background: "rgba(217,164,65,0.8)" }} />
          MA50
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block w-4 h-0.5 rounded" style={{ background: "rgba(91,141,239,0.8)" }} />
          MA200
        </span>
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
