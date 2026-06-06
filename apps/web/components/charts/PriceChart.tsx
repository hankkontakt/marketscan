"use client";

import { useEffect, useRef, useState } from "react";
import type { IChartApi, ISeriesApi } from "lightweight-charts";
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
  const volumeSeriesRef = useRef<ISeriesApi<"Histogram"> | null>(null);
  const ma50Ref = useRef<ISeriesApi<"Line"> | null>(null);
  const ma200Ref = useRef<ISeriesApi<"Line"> | null>(null);
  const resizeObserverRef = useRef<ResizeObserver | null>(null);
  const [period, setPeriod] = useState<"1M" | "3M" | "6M" | "1Å" | "MAX">("3M");
  const { resolved } = useTheme();

  useEffect(() => {
    if (!containerRef.current || typeof window === "undefined") return;

    const isDark = resolved === "dark";
    const gridColor   = isDark ? "#262A31" : "#E3E6EC";
    const textColor   = isDark ? "#9AA1AC" : "#4A5567";
    const upColor     = isDark ? "#3FB68B" : "#15803D";
    const downColor   = isDark ? "#E0645C" : "#DC2626";
    const ma50Color   = isDark ? "rgba(217,164,65,0.7)"  : "rgba(180,83,9,0.6)";
    const ma200Color  = isDark ? "rgba(91,141,239,0.7)"  : "rgba(29,78,216,0.6)";
    const volColor    = isDark ? "rgba(91,141,239,0.25)" : "rgba(29,78,216,0.15)";

    let chart: IChartApi;

    import("lightweight-charts").then(({ createChart, CrosshairMode }) => {
      if (!containerRef.current) return;

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

      const volumeSeries = chart.addHistogramSeries({
        priceScaleId: "volume",
        color: volColor,
        priceFormat: { type: "volume" },
      });
      chart.priceScale("volume").applyOptions({
        scaleMargins: { top: 0.8, bottom: 0 },
      });

      const ma50 = chart.addLineSeries({
        color: ma50Color, lineWidth: 1, priceScaleId: "right",
        crosshairMarkerVisible: false, lastValueVisible: false, priceLineVisible: false,
      });

      const ma200 = chart.addLineSeries({
        color: ma200Color, lineWidth: 1, priceScaleId: "right",
        crosshairMarkerVisible: false, lastValueVisible: false, priceLineVisible: false,
      });

      seriesRef.current = candleSeries;
      volumeSeriesRef.current = volumeSeries;
      ma50Ref.current = ma50;
      ma200Ref.current = ma200;
      chartRef.current = chart;

      updateData(candleSeries, volumeSeries, ma50, ma200, candles, period);

      resizeObserverRef.current = new ResizeObserver(() => {
        if (containerRef.current) {
          chart.applyOptions({ width: containerRef.current.clientWidth });
        }
      });
      resizeObserverRef.current.observe(containerRef.current);
    });

    return () => {
      chart?.remove();
      resizeObserverRef.current?.disconnect();
    };
  }, [candles, resolved]); // eslint-disable-line react-hooks/exhaustive-deps

  function updateData(
    candleSeries: ISeriesApi<"Candlestick">,
    volumeSeries: ISeriesApi<"Histogram">,
    ma50: ISeriesApi<"Line">,
    ma200: ISeriesApi<"Line">,
    data: Candle[],
    p: (typeof PERIODS)[number],
  ) {
    const filtered = filterByPeriod(data, p);
    candleSeries.setData(filtered.map((c) => ({
      time: c.time,
      open: c.open, high: c.high, low: c.low, close: c.close,
    })));

    volumeSeries.setData(
      filtered.map((c) => ({
        time: c.time,
        value: c.volume,
        color: c.close >= c.open ? "rgba(63,182,139,0.3)" : "rgba(224,100,92,0.3)",
      }))
    );

    function calcMA(data: Candle[], n: number) {
      return data.map((_, i) => {
        if (i < n - 1) return null;
        const slice = data.slice(i - n + 1, i + 1);
        return { time: data[i].time, value: slice.reduce((s, c) => s + c.close, 0) / n };
      }).filter(Boolean);
    }

    ma50.setData(calcMA(filtered, 50) as Parameters<ISeriesApi<"Line">["setData"]>[0]);
    ma200.setData(calcMA(filtered, 200) as Parameters<ISeriesApi<"Line">["setData"]>[0]);

    chartRef.current?.timeScale().fitContent();
  }

  function changePeriod(p: (typeof PERIODS)[number]) {
    setPeriod(p);
    if (
      seriesRef.current &&
      volumeSeriesRef.current &&
      ma50Ref.current &&
      ma200Ref.current
    ) {
      updateData(
        seriesRef.current,
        volumeSeriesRef.current,
        ma50Ref.current,
        ma200Ref.current,
        candles,
        p,
      );
    }
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
      <div className="flex items-center gap-3 text-[10px] text-[var(--color-text-muted)]">
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
