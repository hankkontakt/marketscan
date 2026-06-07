"use client";

import { TrendingUp, Globe, ChevronUp, ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";
import { scoreColorClass } from "@/lib/format";
import { SectorHeatmap, GlobalIndexPanel, useSectorOverview, useGlobalIndices } from "@/hooks/useMarkets";

export function MarknadView() {
  const { data: sectors, isLoading: secLoading } = useSectorOverview();
  const { data: markets, isLoading: mktLoading } = useGlobalIndices();

  return (
    <div className="space-y-6">
      <h1 className="text-lg font-semibold text-[var(--color-text-primary)]">Marknadsöversikt</h1>

      {/* Global indices */}
      <div className="rounded-xl border p-5 bg-[var(--color-bg-surface)] border-[var(--color-border)]">
        <div className="flex items-center gap-2 mb-4">
          <Globe size={16} className="text-[var(--color-accent)]" />
          <h2 className="text-sm font-semibold text-[var(--color-text-primary)]">Globala index</h2>
        </div>
        {mktLoading
          ? <div className="skeleton h-32 rounded-lg" />
          : markets?.indices && markets.indices.length > 0
          ? <GlobalIndexPanel indices={markets.indices} />
          : <p className="text-sm text-[var(--color-text-muted)] text-center py-6">
              Indexdata ej tillgänglig (Finnhub API-nyckel krävs)
            </p>
        }
      </div>

      {/* Sector heatmap */}
      <div className="rounded-xl border p-5 bg-[var(--color-bg-surface)] border-[var(--color-border)]">
        <div className="flex items-center gap-2 mb-4">
          <TrendingUp size={16} className="text-[var(--color-accent)]" />
          <h2 className="text-sm font-semibold text-[var(--color-text-primary)]">Sektoröversikt</h2>
          {sectors?.scan_date && (
            <span className="text-[10px] text-[var(--color-text-muted)] ml-auto">
              Senast: {sectors.scan_date}
            </span>
          )}
        </div>
        {secLoading
          ? <div className="skeleton h-48 rounded-lg" />
          : sectors?.sectors && sectors.sectors.length > 0
          ? <SectorHeatmap sectors={sectors.sectors} />
          : <p className="text-sm text-[var(--color-text-muted)] text-center py-6">
              Sektordata ej tillgänglig
            </p>
        }
      </div>

      {/* Top sectors table */}
      {sectors?.sectors && sectors.sectors.length > 0 && (
        <div className="rounded-xl border p-5 bg-[var(--color-bg-surface)] border-[var(--color-border)]">
          <h2 className="text-sm font-semibold mb-4 text-[var(--color-text-primary)]">
            Alla sektorer
          </h2>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-[var(--color-text-muted)] border-b border-[var(--color-border)]">
                  <th className="text-left py-2 pr-4 font-medium">Sektor</th>
                  <th className="text-right py-2 pr-4 font-medium">Antal</th>
                  <th className="text-right py-2 pr-4 font-medium">Betyg</th>
                  <th className="text-right py-2 pr-4 font-medium">Momentum</th>
                  <th className="text-right py-2 pr-4 font-medium">Value</th>
                  <th className="text-right py-2 pr-4 font-medium">Quality</th>
                  <th className="text-right py-2 pr-4 font-medium">Growth</th>
                  <th className="text-right py-2 font-medium">Risk</th>
                </tr>
              </thead>
              <tbody>
                {[...sectors.sectors]
                  .sort((a, b) => b.avg_score - a.avg_score)
                  .map(s => (
                    <tr key={s.sector} className="border-b border-[var(--color-border)] hover:bg-[var(--color-bg-elevated)]">
                      <td className="py-2 pr-4">
                        <a href={`/screener?sector=${encodeURIComponent(s.sector)}`}
                           className="text-[var(--color-text-primary)] hover:text-[var(--color-accent)] font-medium">
                          {s.sector}
                        </a>
                      </td>
                      <td className="text-right py-2 pr-4 font-mono tabular text-[var(--color-text-muted)]">
                        {s.count}
                      </td>
                      <td className={`text-right py-2 pr-4 font-mono tabular ${scoreColorClass(s.avg_score)}`}>
                        {s.avg_score.toFixed(1)}
                      </td>
                      <td className={`text-right py-2 pr-4 font-mono tabular ${scoreColorClass(s.avg_momentum)}`}>
                        {s.avg_momentum.toFixed(1)}
                      </td>
                      <td className="text-right py-2 pr-4 font-mono tabular text-[var(--color-text-secondary)]">
                        {s.avg_value?.toFixed(1) ?? "—"}
                      </td>
                      <td className="text-right py-2 pr-4 font-mono tabular text-[var(--color-text-secondary)]">
                        {s.avg_quality?.toFixed(1) ?? "—"}
                      </td>
                      <td className="text-right py-2 pr-4 font-mono tabular text-[var(--color-text-secondary)]">
                        {s.avg_growth?.toFixed(1) ?? "—"}
                      </td>
                      <td className="text-right py-2 font-mono tabular text-[var(--color-text-secondary)]">
                        {s.avg_risk?.toFixed(1) ?? "—"}
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

// P2-3: Removed local duplicate — using shared scoreColorClass from @/lib/format
