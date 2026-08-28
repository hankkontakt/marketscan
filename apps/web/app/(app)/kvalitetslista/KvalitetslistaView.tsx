"use client";

import { AlertTriangle, ExternalLink, ShieldCheck } from "lucide-react";
import { useMarketIntelQmjRank } from "@/hooks/useMarketIntel";
import { cn } from "@/lib/utils";
import { scoreColorClass } from "@/lib/format";

// ─── Z-bar ────────────────────────────────────────────────────────────────────
// Kort stapel med bredd = z/100 (z är en 0-100 percentil inom storleksgrupp).

function ZBar({ value }: { value: number | null }) {
  const pct = value != null ? Math.max(0, Math.min(100, value)) : 0;
  const color =
    pct >= 70 ? "var(--color-score-high)" :
    pct >= 50 ? "var(--color-score-mid)" :
    "var(--color-score-low)";
  return (
    <div className="w-12 h-1.5 rounded-full bg-[var(--color-bg-elevated)] overflow-hidden">
      <div className="h-full rounded-full" style={{ width: `${pct}%`, background: color }} />
    </div>
  );
}

const WARNING_LABELS: Record<string, string> = {
  sell_cluster: "Säljkluster",
  illiquid: "Illikvid",
};

// ─── Main View ────────────────────────────────────────────────────────────────

export function KvalitetslistaView() {
  const { data = [], isLoading, error } = useMarketIntelQmjRank();
  const rows = data.slice(0, 30);

  return (
    <div className="max-w-5xl space-y-6">

      {/* Header */}
      <div>
        <h1 className="text-xl font-semibold text-[var(--color-text-primary)]">Kvalitetslista</h1>
        <p className="text-xs text-[var(--color-text-muted)] mt-0.5">
          Evidensbaserad kvalitetsscreening — rankad efter kvalitet, momentum, insiderhandel, värde och utdelning
        </p>
      </div>

      {/* Table */}
      {isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="h-12 rounded-lg bg-[var(--color-bg-elevated)] animate-pulse" />
          ))}
        </div>
      ) : error ? (
        <div className="flex flex-col items-center py-16 gap-3 text-center">
          <AlertTriangle size={32} strokeWidth={1} className="text-[var(--color-warn)]" />
          <p className="text-sm text-[var(--color-text-muted)]">
            Kunde inte hämta kvalitetsdata
          </p>
        </div>
      ) : rows.length === 0 ? (
        <div className="flex flex-col items-center py-16 gap-3 text-center">
          <ShieldCheck size={36} strokeWidth={1} className="text-[var(--color-text-muted)]" />
          <p className="text-sm text-[var(--color-text-muted)]">
            Ingen kvalitetsdata tillgänglig ännu
          </p>
          <p className="text-xs text-[var(--color-text-muted)] max-w-xs">
            Listan uppdateras veckovis från bokslutsdata.
          </p>
        </div>
      ) : (
        <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-bg-card)] overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--color-border)]">
                <th className="px-4 py-3 text-left text-xs font-medium text-[var(--color-text-muted)]">Aktie</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-[var(--color-text-muted)]">Rank</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-[var(--color-text-muted)] hidden sm:table-cell">Kvalitet</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-[var(--color-text-muted)] hidden sm:table-cell">Momentum</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-[var(--color-text-muted)] hidden md:table-cell">Insider</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-[var(--color-text-muted)] hidden md:table-cell">Värde</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-[var(--color-text-muted)] hidden lg:table-cell">Utdelning</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-[var(--color-text-muted)] hidden lg:table-cell">As-of</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-[var(--color-text-muted)]">Varningar</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.ticker} className="border-b border-[var(--color-border)] hover:bg-[var(--color-bg-elevated)] transition-colors">
                  {/* Ticker */}
                  <td className="px-4 py-3">
                    <a
                      href={`/aktie/${row.ticker}`}
                      className="flex items-center gap-1 font-semibold text-sm text-[var(--color-text-primary)] hover:text-[var(--color-accent)] transition-colors"
                    >
                      {row.ticker}
                      <ExternalLink size={10} className="opacity-50" />
                    </a>
                  </td>

                  {/* Rank */}
                  <td className="px-4 py-3 text-right">
                    <span className={cn("text-sm font-bold tabular", scoreColorClass(row.alpha_rank))}>
                      {row.alpha_rank != null ? Math.round(row.alpha_rank) : "—"}
                    </span>
                  </td>

                  {/* Z-bars */}
                  <td className="px-4 py-3 hidden sm:table-cell"><ZBar value={row.quality_z} /></td>
                  <td className="px-4 py-3 hidden sm:table-cell"><ZBar value={row.momentum_z} /></td>
                  <td className="px-4 py-3 hidden md:table-cell"><ZBar value={row.insider_z} /></td>
                  <td className="px-4 py-3 hidden md:table-cell"><ZBar value={row.value_z} /></td>
                  <td className="px-4 py-3 hidden lg:table-cell"><ZBar value={row.payout_z} /></td>

                  {/* As-of */}
                  <td className="px-4 py-3 text-right hidden lg:table-cell">
                    <span className="text-xs text-[var(--color-text-muted)]">
                      {row.as_of_date ?? "—"}
                    </span>
                  </td>

                  {/* Warnings */}
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap gap-1">
                      {(row.warning_flags ?? []).map((flag) => (
                        <span
                          key={flag}
                          className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-[var(--color-warn-soft)] text-[var(--color-warn)]"
                        >
                          {WARNING_LABELS[flag] ?? flag}
                        </span>
                      ))}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Honesty footer */}
      <p className="text-xs text-[var(--color-text-muted)]">
        Evidensbaserad kvalitetsscreening. Historisk avkastning är ingen garanti. Småbolagsspread ~1 % per sida — rebalansera högst årligen.
      </p>
    </div>
  );
}