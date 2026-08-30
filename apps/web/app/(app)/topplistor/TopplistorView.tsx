"use client";

import { AlertTriangle, ExternalLink, Trophy, Info } from "lucide-react";
import { useState } from "react";
import { useMarketIntelMasterRank } from "@/hooks/useMarketIntel";
import type { MasterRankItem } from "@/lib/api";
import { cn } from "@/lib/utils";
import { scoreColorClass } from "@/lib/format";

// ─── Flaggor → svenska etiketter ──────────────────────────────────────────────

const VAL_FLAG_LABELS: Record<string, string> = {
  EXTREME_OVERVAL: "Övervärderad vs historik",
  CHEAP: "Billig",
};

const TECH_FLAG_LABELS: Record<string, string> = {
  OVERBOUGHT: "Överköpt (RSI > 75)",
  OVERSOLD: "Översålt (RSI < 30)",
  TREND_DOWN: "Under MA200",
  PULLBACK: "Pullback 5–18 %",
};

const TIER_LABELS: Record<string, string> = {
  T1: "T1 · Kandidat",
  T2: "T2 · Värd att kolla",
  T3: "T3 · Neutral",
  T4: "T4 · Undvik",
  EXCLUDED: "Exkluderad",
};

const TIER_COLORS: Record<string, string> = {
  T1: "bg-[var(--color-up-soft)] text-[var(--color-up)]",
  T2: "bg-[var(--color-accent-soft)] text-[var(--color-accent)]",
  T3: "bg-[var(--color-bg-elevated)] text-[var(--color-text-muted)]",
  T4: "bg-[var(--color-down-soft)] text-[var(--color-down)]",
  EXCLUDED: "bg-[var(--color-warn-soft)] text-[var(--color-warn)]",
};

// ─── Z-bar (samma som kvalitetslistan) ────────────────────────────────────────

function ZBar({ value }: { value: number | null }) {
  const pct = value != null ? Math.max(0, Math.min(100, value)) : 0;
  const color =
    pct >= 70 ? "var(--color-score-high)" :
    pct >= 50 ? "var(--color-score-mid)" :
    "var(--color-score-low)";
  return (
    <div className="w-10 h-1.5 rounded-full bg-[var(--color-bg-elevated)] overflow-hidden">
      <div className="h-full rounded-full" style={{ width: `${pct}%`, background: color }} />
    </div>
  );
}

// ─── MasterRank-rad ──────────────────────────────────────────────────────────

function MasterRow({ row }: { row: MasterRankItem }) {
  const isBubble = row.val_flags?.includes("EXTREME_OVERVAL") && row.tech_flags?.includes("OVERBOUGHT");
  const isNordic = /\.(ST|OL|HE|CO)$/.test(row.ticker);
  const upside = row.analyst_upside;

  return (
    <tr className="border-b border-[var(--color-border)] hover:bg-[var(--color-bg-elevated)] transition-colors">
      <td className="px-4 py-3">
        <a
          href={`/aktie/${row.ticker}`}
          className="flex items-center gap-1 font-semibold text-sm text-[var(--color-text-primary)] hover:text-[var(--color-accent)] transition-colors"
        >
          {row.ticker}
          <ExternalLink size={10} className="opacity-50" />
        </a>
        <div className="text-[10px] text-[var(--color-text-muted)] mt-0.5">
          {isNordic ? "Nordisk" : "Global"} · PIT: {row.pit_status ?? "—"}
        </div>
      </td>

      {/* MasterRank */}
      <td className="px-4 py-3 text-right">
        <span className={cn("text-sm font-bold tabular", scoreColorClass(row.master_rank))}>
          {row.master_rank != null ? Math.round(row.master_rank) : "—"}
        </span>
        <div className={cn("inline-block ml-2 px-1.5 py-0.5 rounded text-[10px] font-medium", TIER_COLORS[row.tier ?? ""] ?? "")}>
          {TIER_LABELS[row.tier ?? ""] ?? row.tier}
        </div>
      </td>

      {/* Värdering */}
      <td className="px-4 py-3 hidden md:table-cell">
        <div className="flex items-center gap-2">
          <ZBar value={row.val_hist_z} />
          <ZBar value={row.val_peers_z} />
        </div>
        {(row.val_flags ?? []).map((f) => (
          <div key={f} className={cn("text-[10px] mt-1 font-medium",
            f === "EXTREME_OVERVAL" ? "text-[var(--color-down)]" : "text-[var(--color-up)]")}>
            {VAL_FLAG_LABELS[f] ?? f}
          </div>
        ))}
      </td>

      {/* Analytiker */}
      <td className="px-4 py-3 hidden lg:table-cell">
        {upside != null ? (
          <div className={cn("text-sm font-semibold", upside > 10 ? "text-[var(--color-up)]" : "text-[var(--color-text-muted)]")}>
            {upside > 0 ? "+" : ""}{upside.toFixed(1)} %
          </div>
        ) : (
          <span className="text-xs text-[var(--color-text-muted)]">—</span>
        )}
        <div className="text-[10px] text-[var(--color-text-muted)] mt-0.5">
          {row.analyst_count != null ? `${row.analyst_count} analytiker` : "ingen täckning"}
        </div>
      </td>

      {/* Teknisk */}
      <td className="px-4 py-3 hidden sm:table-cell">
        <div className="text-sm tabular">
          RSI {row.rsi_14 != null ? Math.round(row.rsi_14) : "—"}
        </div>
        {(row.tech_flags ?? []).slice(0, 2).map((f) => (
          <div key={f} className="text-[10px] text-[var(--color-text-muted)]">{TECH_FLAG_LABELS[f] ?? f}</div>
        ))}
      </td>

      {/* Katalysator */}
      <td className="px-4 py-3 hidden xl:table-cell">
        {row.catalyst_next ? (
          <div className="text-xs">
            <div className="font-medium text-[var(--color-text-primary)]">{row.catalyst_next.split(":")[0]}</div>
            <div className="text-[10px] text-[var(--color-text-muted)]">
              {row.catalyst_days != null ? `om ${row.catalyst_days} d · ${row.catalyst_next.split(":")[1]}` : "om <45 d"}
            </div>
          </div>
        ) : (
          <span className="text-xs text-[var(--color-text-muted)]">—</span>
        )}
      </td>

      {/* Bubbla-triage */}
      <td className="px-4 py-3">
        {isBubble ? (
          <span className="inline-flex items-center gap-1 text-[10px] font-medium px-1.5 py-0.5 rounded bg-[var(--color-warn-soft)] text-[var(--color-warn)]">
            <AlertTriangle size={10} /> Bubbla-triage
          </span>
        ) : row.tier === "T1" ? (
          <span className="inline-flex items-center gap-1 text-[10px] font-medium px-1.5 py-0.5 rounded bg-[var(--color-up-soft)] text-[var(--color-up)]">
            <Trophy size={10} /> Kandidat
          </span>
        ) : null}
      </td>
    </tr>
  );
}

// ─── Main View ────────────────────────────────────────────────────────────────

export function TopplistorView() {
  const { data = [], isLoading, error } = useMarketIntelMasterRank(50);
  const [scope, setScope] = useState<"all" | "nordic" | "global">("all");

  const nordic = data.filter((r) => /\.(ST|OL|HE|CO)$/.test(r.ticker));
  const global = data.filter((r) => !/\.(ST|OL|HE|CO)$/.test(r.ticker));
  const rows =
    scope === "nordic" ? nordic :
    scope === "global" ? global :
    data;

  return (
    <div className="max-w-6xl space-y-6">

      {/* Header */}
      <div>
        <h1 className="text-xl font-semibold text-[var(--color-text-primary)]">Topplistor</h1>
        <p className="text-xs text-[var(--color-text-muted)] mt-0.5">
          MasterRank — den auktoritativa rankningen: kvalitet, värdering vs historik, analytikeruppsida, teknik och katalysator
        </p>
      </div>

      {/* Scope-toggle */}
      <div className="flex items-center gap-2 flex-wrap">
        {(["all", "nordic", "global"] as const).map((s) => (
          <button
            key={s}
            onClick={() => setScope(s)}
            className={cn(
              "px-3 py-1.5 rounded-lg text-xs font-medium transition-colors",
              scope === s
                ? "bg-[var(--color-accent-soft)] text-[var(--color-accent)]"
                : "bg-[var(--color-bg-elevated)] text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]",
            )}
          >
            {s === "all" ? "Alla" : s === "nordic" ? "Nordiska" : "Globala"}
          </button>
        ))}
      </div>

      {/* Info */}
      <div className="flex items-start gap-2 text-xs text-[var(--color-text-muted)] bg-[var(--color-bg-elevated)] rounded-lg p-3">
        <Info size={14} className="mt-0.5 shrink-0" />
        <p>
          MasterRank är en rankning av <strong>signaler</strong>, inte en rekommendation. &ldquo;Bubbla-triage&rdquo; betyder att
          aktien är övervärderad mot sin egen historik <em>och</em> tekniskt överköpt — ett starkt bolag vars pris
          sprungit ikapp nyheterna.
        </p>
      </div>

      {/* Table */}
      {isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 10 }).map((_, i) => (
            <div key={i} className="h-12 rounded-lg bg-[var(--color-bg-elevated)] animate-pulse" />
          ))}
        </div>
      ) : error ? (
        <div className="flex flex-col items-center py-16 gap-3 text-center">
          <AlertTriangle size={32} strokeWidth={1} className="text-[var(--color-warn)]" />
          <p className="text-sm text-[var(--color-text-muted)]">Kunde inte hämta MasterRank-data</p>
        </div>
      ) : rows.length === 0 ? (
        <div className="flex flex-col items-center py-16 gap-3 text-center">
          <Trophy size={36} strokeWidth={1} className="text-[var(--color-text-muted)]" />
          <p className="text-sm text-[var(--color-text-muted)]">Ingen MasterRank-data tillgänglig ännu</p>
          <p className="text-xs text-[var(--color-text-muted)] max-w-xs">
            Listan byggs fredags natt när QMJ, analytiker- och katalysatordata uppdateras.
          </p>
        </div>
      ) : (
        <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-bg-card)] overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--color-border)]">
                <th className="px-4 py-3 text-left text-xs font-medium text-[var(--color-text-muted)]">Aktie</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-[var(--color-text-muted)]">MasterRank</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-[var(--color-text-muted)] hidden md:table-cell">Värdering (hist/peers)</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-[var(--color-text-muted)] hidden lg:table-cell">Analytiker</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-[var(--color-text-muted)] hidden sm:table-cell">Teknisk</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-[var(--color-text-muted)] hidden xl:table-cell">Katalysator</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-[var(--color-text-muted)]">Status</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <MasterRow key={row.ticker} row={row} />
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Honesty footer */}
      <p className="text-xs text-[var(--color-text-muted)]">
        MasterRank byggs på evidens och mäts kontinuerligt — varje delscore:s Rank-IC loggas i factor_metrics.
        Historisk avkastning är ingen garanti. Småbolagsspread ~1 % per sida.
      </p>
    </div>
  );
}
