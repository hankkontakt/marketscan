"use client";

import { useState } from "react";
import { Activity, TrendingUp, Clock, Target, BarChart3, ChevronDown } from "lucide-react";
import { useSignalAnalytics, useSignalAnalyticsDetail } from "@/hooks/useStrategies";
import type { SignalAnalytics } from "@/types/strategy";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  Cell, ReferenceLine,
} from "recharts";
import { cn } from "@/lib/utils";

// ─── Helpers ──────────────────────────────────────────────────────────────────

function pctColor(v: number | null) {
  if (v == null) return "text-[var(--color-text-muted)]";
  if (v > 3) return "text-emerald-400";
  if (v > 0) return "text-emerald-300";
  if (v < -3) return "text-red-400";
  return "text-red-300";
}

function WinRateBadge({ v }: { v: number | null }) {
  if (v == null) return <span className="text-[var(--color-text-muted)]">–</span>;
  return (
    <span className={cn("font-medium", v >= 55 ? "text-emerald-400" : v >= 45 ? "text-yellow-400" : "text-red-400")}>
      {v.toFixed(0)}%
    </span>
  );
}

// ─── Row — one signal transition ─────────────────────────────────────────────

function TransitionRow({
  item,
  selected,
  onClick,
}: {
  item: SignalAnalytics;
  selected: boolean;
  onClick: () => void;
}) {
  return (
    <tr
      onClick={onClick}
      className={cn(
        "border-b border-[var(--color-border)] cursor-pointer hover:bg-[var(--color-bg-elevated)] transition-colors",
        selected && "bg-[var(--color-accent-soft)]"
      )}
    >
      <td className="px-4 py-2.5 font-medium text-sm text-[var(--color-text-primary)]">
        {item.label}
      </td>
      <td className="px-4 py-2.5 text-xs text-[var(--color-text-muted)] tabular-nums text-right">
        {item.sample_count}
      </td>
      <td className="px-4 py-2.5 text-xs text-right">
        <WinRateBadge v={item.win_rate_20d} />
      </td>
      <td className={cn("px-4 py-2.5 text-xs tabular-nums text-right", pctColor(item.avg_return_20d))}>
        {item.avg_return_20d != null ? `${item.avg_return_20d > 0 ? "+" : ""}${item.avg_return_20d.toFixed(2)}%` : "–"}
      </td>
      <td className={cn("px-4 py-2.5 text-xs tabular-nums text-right", pctColor(item.avg_return_60d))}>
        {item.avg_return_60d != null ? `${item.avg_return_60d > 0 ? "+" : ""}${item.avg_return_60d.toFixed(2)}%` : "–"}
      </td>
      <td className="px-4 py-2.5 text-xs text-right text-[var(--color-text-muted)]">
        {item.median_hold_days != null ? `${item.median_hold_days.toFixed(0)} d` : "–"}
      </td>
      <td className="px-4 py-2.5 text-center">
        <ChevronDown size={14} className={cn("text-[var(--color-text-muted)] transition-transform", selected && "rotate-180")} />
      </td>
    </tr>
  );
}

// ─── Detail panel ─────────────────────────────────────────────────────────────

function DetailPanel({ item }: { item: SignalAnalytics }) {
  const { data, isLoading } = useSignalAnalyticsDetail(item.field, item.from_signal, item.to_signal);

  const barData = [
    { label: "5 dagar",  value: item.avg_return_5d },
    { label: "10 dagar", value: item.avg_return_10d },
    { label: "20 dagar", value: item.avg_return_20d },
    { label: "60 dagar", value: item.avg_return_60d },
  ].filter(d => d.value != null);

  return (
    <tr>
      <td colSpan={7} className="p-0">
        <div className="px-6 py-4 bg-[var(--color-bg-elevated)] space-y-4 border-b border-[var(--color-border)]">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs">
            <div>
              <div className="text-[var(--color-text-muted)]">Median hålltid</div>
              <div className="text-[var(--color-text-primary)] font-medium">
                {item.median_hold_days != null ? `${item.median_hold_days.toFixed(0)} dagar` : "–"}
              </div>
            </div>
            <div>
              <div className="text-[var(--color-text-muted)]">75:e percentil hålltid</div>
              <div className="text-[var(--color-text-primary)] font-medium">
                {item.pct75_hold_days != null ? `${item.pct75_hold_days.toFixed(0)} dagar` : "–"}
              </div>
            </div>
            <div>
              <div className="text-[var(--color-text-muted)]">Win rate 20d</div>
              <div><WinRateBadge v={item.win_rate_20d} /></div>
            </div>
            <div>
              <div className="text-[var(--color-text-muted)]">Antal observationer</div>
              <div className="text-[var(--color-text-primary)] font-medium">{item.sample_count}</div>
            </div>
          </div>

          {/* Forward return chart */}
          {barData.length > 0 && (
            <div>
              <p className="text-xs text-[var(--color-text-muted)] mb-2">Genomsnittlig framåtavkastning</p>
              <ResponsiveContainer width="100%" height={140}>
                <BarChart data={barData} barSize={32}>
                  <XAxis dataKey="label" tick={{ fontSize: 10, fill: "var(--color-text-muted)" }} tickLine={false} axisLine={false} />
                  <YAxis tick={{ fontSize: 10, fill: "var(--color-text-muted)" }} tickLine={false} axisLine={false} tickFormatter={v => `${v}%`} />
                  <ReferenceLine y={0} stroke="var(--color-border)" />
                  <Tooltip
                    contentStyle={{ background: "var(--color-bg-card)", border: "1px solid var(--color-border)", borderRadius: 8, fontSize: 12 }}
                    formatter={(v: number) => [`${v > 0 ? "+" : ""}${(v as number).toFixed(2)}%`, "Avkastning"]}
                  />
                  <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                    {barData.map((d, i) => (
                      <Cell key={i} fill={(d.value ?? 0) >= 0 ? "hsl(160, 60%, 55%)" : "hsl(0, 70%, 60%)"} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Recent examples */}
          {!isLoading && data?.examples && data.examples.length > 0 && (
            <div>
              <p className="text-xs text-[var(--color-text-muted)] mb-2">Senaste exempel</p>
              <div className="space-y-1">
                {data.examples.slice(0, 6).map((ex, i) => (
                  <div key={i} className="flex items-center gap-3 text-xs">
                    <span className="font-mono text-[var(--color-text-secondary)] w-16">{ex.ticker}</span>
                    <span className="text-[var(--color-text-muted)] w-20">{ex.transition_date}</span>
                    <span className="text-[var(--color-text-muted)]">
                      {ex.price_at != null ? `${ex.price_at.toFixed(2)} kr` : "–"}
                    </span>
                    <span className="text-[var(--color-text-muted)]">
                      {ex.score_total_at != null ? `betyg ${ex.score_total_at.toFixed(0)}` : ""}
                    </span>
                    {ex.current_signal && (
                      <span className={cn(
                        "ml-auto px-1.5 py-0.5 rounded text-xs",
                        ex.current_signal === "STARK" ? "bg-emerald-500/10 text-emerald-400"
                          : ex.current_signal === "SVAG" ? "bg-red-500/10 text-red-400"
                          : "bg-[var(--color-bg-elevated)] text-[var(--color-text-muted)]"
                      )}>
                        nu: {ex.current_signal}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Sector breakdown */}
          {item.sector_breakdown && Object.keys(item.sector_breakdown).length > 0 && (
            <div>
              <p className="text-xs text-[var(--color-text-muted)] mb-2">Avkastning per sektor (20d)</p>
              <div className="flex flex-wrap gap-2">
                {Object.entries(item.sector_breakdown)
                  .sort((a, b) => b[1] - a[1])
                  .map(([sector, ret]) => (
                    <span
                      key={sector}
                      className={cn(
                        "text-xs px-2 py-0.5 rounded-full",
                        ret > 0 ? "bg-emerald-500/10 text-emerald-400" : "bg-red-500/10 text-red-400"
                      )}
                    >
                      {sector}: {ret > 0 ? "+" : ""}{ret.toFixed(1)}%
                    </span>
                  ))}
              </div>
            </div>
          )}
        </div>
      </td>
    </tr>
  );
}

// ─── Main view ────────────────────────────────────────────────────────────────

export function SignalAnalyticsView() {
  const [fieldFilter, setFieldFilter] = useState<"entry_signal" | "trend_signal" | undefined>(undefined);
  const [selectedKey, setSelectedKey] = useState<string | null>(null);
  const { data = [], isLoading } = useSignalAnalytics(fieldFilter, 3);

  function toggleRow(item: SignalAnalytics) {
    const key = `${item.field}:${item.from_signal}:${item.to_signal}`;
    setSelectedKey(prev => (prev === key ? null : key));
  }

  const selectedItem = selectedKey
    ? data.find(d => `${d.field}:${d.from_signal}:${d.to_signal}` === selectedKey)
    : null;

  return (
    <div className="max-w-4xl space-y-6">

      {/* Header */}
      <div>
        <h1 className="text-xl font-semibold text-[var(--color-text-primary)]">Signalanalys</h1>
        <p className="text-xs text-[var(--color-text-muted)] mt-0.5">
          Statistik för hur aktier beter sig efter signalövergångar — baserat på score_history
        </p>
      </div>

      {/* Info */}
      <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-bg-card)] p-4 text-xs text-[var(--color-text-muted)] space-y-1">
        <p className="font-medium text-[var(--color-text-secondary)]">Vad är signalanalys?</p>
        <p>
          Varje gång en aktie byter signal (t.ex. VÄNTA→STARK) registreras det i signal_transitions.
          Här aggregeras statistik för hur priset förändrats i genomsnitt 5, 10, 20 och 60 dagar efter transitionen,
          hur länge signalen vanligtvis håller, och var vinster/förluster sker.
        </p>
        <p className="text-[var(--color-text-muted)]">
          Obs: Datan byggs upp löpande — ju mer historik, desto mer tillförlitliga siffror.
          Minst 3 observationer krävs för att en transition visas.
        </p>
      </div>

      {/* Filter */}
      <div className="flex gap-2">
        {([
          [undefined,         "Alla typer"],
          ["entry_signal",    "Inträde-signal"],
          ["trend_signal",    "Trend-signal"],
        ] as const).map(([val, label]) => (
          <button
            key={String(val)}
            onClick={() => setFieldFilter(val)}
            className={cn(
              "px-3 py-1.5 rounded-lg text-xs font-medium transition-colors",
              fieldFilter === val
                ? "bg-[var(--color-accent)] text-white"
                : "bg-[var(--color-bg-elevated)] text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]"
            )}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Table */}
      {isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="h-12 rounded-lg bg-[var(--color-bg-elevated)] animate-pulse" />
          ))}
        </div>
      ) : data.length === 0 ? (
        <div className="flex flex-col items-center py-16 gap-3 text-center">
          <Activity size={36} strokeWidth={1} className="text-[var(--color-text-muted)]" />
          <p className="text-sm text-[var(--color-text-muted)]">
            Inga signaltransitioner hittades ännu.
          </p>
          <p className="text-xs text-[var(--color-text-muted)] max-w-xs">
            Data samlas in löpande av score_tracker.py. Kom tillbaka efter att screener körts ett antal gånger.
          </p>
        </div>
      ) : (
        <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-bg-card)] overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--color-border)]">
                <th className="px-4 py-3 text-left text-xs font-medium text-[var(--color-text-muted)]">Transition</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-[var(--color-text-muted)]">N</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-[var(--color-text-muted)]">Win% (20d)</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-[var(--color-text-muted)]">Avg retur 20d</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-[var(--color-text-muted)]">Avg retur 60d</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-[var(--color-text-muted)]">Median hålltid</th>
                <th className="px-4 py-3 w-8" />
              </tr>
            </thead>
            <tbody>
              {data.map(item => {
                const key = `${item.field}:${item.from_signal}:${item.to_signal}`;
                const isSelected = selectedKey === key;
                return (
                  <>
                    <TransitionRow
                      key={key}
                      item={item}
                      selected={isSelected}
                      onClick={() => toggleRow(item)}
                    />
                    {isSelected && selectedItem && (
                      <DetailPanel key={`detail-${key}`} item={selectedItem} />
                    )}
                  </>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
