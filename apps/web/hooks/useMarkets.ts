"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { TrendingUp, Globe } from "lucide-react";

export interface SectorSummary {
  sector: string;
  count: number;
  avg_score: number;
  avg_momentum: number;
  avg_value: number | null;
  avg_quality: number | null;
  avg_growth: number | null;
  avg_risk: number | null;
  top_ticker: string | null;
  top_score: number | null;
  stark_count: number;
  ok_count: number;
  vanta_count: number;
}

interface SectorOverview {
  sectors: SectorSummary[];
  total_tickers: number;
  scan_date: string | null;
}

export function useSectorOverview() {
  return useQuery<SectorOverview>({
    queryKey: ["sector-overview"],
    queryFn: () => api<SectorOverview>("/api/markets/sectors"),
    staleTime: 10 * 60_000,
  });
}

interface GlobalIndex {
  name: string;
  price: number | null;
  change_pct: number | null;
}

interface GlobalMarkets {
  indices: GlobalIndex[];
}

export function useGlobalIndices() {
  return useQuery<GlobalMarkets>({
    queryKey: ["global-indices"],
    queryFn: () => api<GlobalMarkets>("/api/markets/indices"),
    staleTime: 2 * 60_000,
  });
}

function scoreColor(val: number): string {
  if (val >= 70) return "text-[var(--color-score-high)]";
  if (val >= 50) return "text-[var(--color-score-mid)]";
  return "text-[var(--color-score-low)]";
}

export function SectorHeatmap({ sectors }: { sectors: SectorSummary[] }) {
  const maxScore = Math.max(...sectors.map(s => s.avg_score), 1);
  const topSectors = [...sectors].sort((a, b) => b.avg_score - a.avg_score);

  return (
    <div className="space-y-1.5 max-h-[300px] overflow-y-auto pr-1">
      {topSectors.map(s => {
        const pct = (s.avg_score / maxScore) * 100;
        return (
          <div key={s.sector} className="group relative">
            <div className="flex justify-between text-xs mb-0.5">
              <a
                href={`/screener?sector=${encodeURIComponent(s.sector)}`}
                className="font-medium text-[var(--color-text-primary)] hover:text-[var(--color-accent)] z-10 relative"
              >
                {s.sector}
              </a>
              <span className={`font-mono tabular ${scoreColor(s.avg_score)}`}>
                {s.avg_score.toFixed(0)}
              </span>
            </div>
            <div className="h-2 rounded-full overflow-hidden bg-[var(--color-bg-elevated)]">
              <div
                className="h-full rounded-full transition-all"
                style={{
                  width: `${pct}%`,
                  background: s.avg_score >= 70
                    ? "var(--color-score-high)"
                    : s.avg_score >= 50
                    ? "var(--color-score-mid)"
                    : "var(--color-score-low)",
                  opacity: 0.6 + (s.avg_score / 100) * 0.4,
                }}
              />
            </div>
            <div className="hidden group-hover:block absolute left-0 top-full mt-1 z-50 p-2 rounded-lg text-xs shadow-lg bg-[var(--color-bg-elevated)] border border-[var(--color-border-strong)] min-w-[200px]">
              <p><strong>{s.sector}</strong> — {s.count} aktier</p>
              <p>Bäst: {s.top_ticker ?? "—"} ({s.top_score?.toFixed(0) ?? "—"})</p>
              <p>STARK: {s.stark_count} | OK: {s.ok_count} | VÄNTA: {s.vanta_count}</p>
            </div>
          </div>
        );
      })}
    </div>
  );
}

export function GlobalIndexPanel({ indices }: { indices: GlobalIndex[] }) {
  return (
    <div className="space-y-1.5">
      {indices.map(idx => (
        <div key={idx.name} className="flex justify-between items-center text-xs">
          <span className="text-[var(--color-text-primary)]">{idx.name}</span>
          <div className="flex items-center gap-2">
            <span className="font-mono tabular text-[var(--color-text-secondary)]">
              {idx.price?.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
            </span>
            {idx.change_pct != null && (
              <span className={`font-mono tabular w-14 text-right ${
                idx.change_pct >= 0 ? "text-[var(--color-up)]" : "text-[var(--color-down)]"
              }`}>
                {idx.change_pct >= 0 ? "+" : ""}{idx.change_pct.toFixed(2)}%
              </span>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
