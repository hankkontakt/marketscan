"use client";

import * as Tabs from "@radix-ui/react-tabs";
import {
  Brain, TrendingUp, Target, BarChart2, ListChecks,
  RefreshCw, CheckCircle, XCircle, Clock,
} from "lucide-react";
import {
  useMlSummary, useMlOutcomes, useMlDeciles,
  useMlIcTrend, useMlTopPicks,
  type OutcomeRow, type DecileRow, type IcPoint, type TopPickRow,
} from "@/hooks/useMlPerformance";
import {
  AreaChart, Area, BarChart, Bar, ScatterChart, Scatter,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  ReferenceLine, Cell,
} from "recharts";
import { cn } from "@/lib/utils";
import { formatPct } from "@/lib/format";

// ── KPI-kort ──────────────────────────────────────────────────────────────────

function KpiCard({
  label, value, sub, good, bad,
}: {
  label: string;
  value: React.ReactNode;
  sub?: string;
  good?: boolean;
  bad?: boolean;
}) {
  return (
    <div className="rounded-xl border bg-[var(--color-bg-surface)] border-[var(--color-border)] p-4 flex flex-col gap-1">
      <span className="text-xs text-[var(--color-text-muted)]">{label}</span>
      <span
        className={cn(
          "text-xl font-semibold",
          good && "text-[var(--color-success)]",
          bad  && "text-[var(--color-danger)]",
          !good && !bad && "text-[var(--color-text-primary)]",
        )}
      >
        {value}
      </span>
      {sub && <span className="text-xs text-[var(--color-text-muted)]">{sub}</span>}
    </div>
  );
}

// ── Skeletons ─────────────────────────────────────────────────────────────────

function Skeleton({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        "animate-pulse rounded bg-[var(--color-bg-elevated)]",
        className,
      )}
    />
  );
}

// ── Översikts-panel ───────────────────────────────────────────────────────────

function OverviewPanel() {
  const { data, isLoading, error } = useMlSummary();

  if (isLoading)
    return (
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {Array.from({ length: 8 }).map((_, i) => (
          <Skeleton key={i} className="h-20" />
        ))}
      </div>
    );

  if (error || !data)
    return (
      <p className="text-sm text-[var(--color-text-muted)]">
        Kunde inte hämta modell-metrics. Kontrollera att API:et körs.
      </p>
    );

  const icOk = data.ic != null && data.ic > 0.05;
  const liveIcOk = data.live_ic != null && data.live_ic > 0.05;
  const pctEvaluated =
    data.outcomes_total > 0
      ? Math.round((data.outcomes_evaluated / data.outcomes_total) * 100)
      : 0;

  return (
    <div className="space-y-6">
      {/* Modell-info */}
      <div className="rounded-xl border bg-[var(--color-bg-surface)] border-[var(--color-border)] p-4">
        <div className="flex items-center gap-2 mb-3">
          <Brain size={16} className="text-[var(--color-accent)]" />
          <span className="text-sm font-medium text-[var(--color-text-primary)]">
            Aktiv modell
          </span>
          <span className="ml-auto text-xs text-[var(--color-text-muted)]">
            {data.model_type ?? "okänd"}
          </span>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-2 text-xs text-[var(--color-text-secondary)]">
          <span>Tränad: {data.trained_at ? data.trained_at.slice(0, 10) : "–"}</span>
          <span>Rader: {data.n_rows?.toLocaleString("sv-SE") ?? "–"}</span>
          <span>Features: {data.n_features ?? "–"}</span>
          <span>Folds: {data.n_folds ?? "–"}</span>
          <span>Version: {data.model_version}</span>
        </div>
      </div>

      {/* KPI-grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <KpiCard
          label="Walk-forward IC"
          value={data.ic != null ? data.ic.toFixed(4) : "–"}
          sub="Mål: > 0.050"
          good={icOk}
          bad={data.ic != null && data.ic <= 0.027}
        />
        <KpiCard
          label="WF Hit-rate"
          value={data.hit_rate != null ? `${(data.hit_rate * 100).toFixed(1)}%` : "–"}
          sub="Mål: > 53%"
          good={data.hit_rate != null && data.hit_rate > 0.53}
        />
        <KpiCard
          label="Decil-spread"
          value={data.decile_spread != null ? data.decile_spread.toFixed(4) : "–"}
          sub="Topp − Botten decil"
          good={data.decile_spread != null && data.decile_spread > 0.01}
        />
        <KpiCard
          label="Live IC"
          value={data.live_ic != null ? data.live_ic.toFixed(4) : "väntar…"}
          sub={`${data.outcomes_evaluated} utvärderade`}
          good={liveIcOk}
          bad={data.live_ic != null && data.live_ic <= 0}
        />
        <KpiCard
          label="Prediktioner loggade"
          value={data.outcomes_total.toLocaleString("sv-SE")}
          sub="Totalt i prediction_outcomes"
        />
        <KpiCard
          label="Utfall insamlade"
          value={`${pctEvaluated}%`}
          sub={`${data.outcomes_evaluated} / ${data.outcomes_total}`}
          good={pctEvaluated >= 50}
        />
        <KpiCard
          label="Live Hit-rate"
          value={data.live_hit_rate != null ? `${(data.live_hit_rate * 100).toFixed(1)}%` : "–"}
          sub="Baserat på realiserade utfall"
          good={data.live_hit_rate != null && data.live_hit_rate > 0.53}
        />
        <KpiCard
          label="Status"
          value={icOk ? "✅ Godkänd" : "⚠️ Under mål"}
          sub={icOk ? "IC > 0.05" : "IC ≤ 0.05, förbättring behövs"}
          good={icOk}
          bad={!icOk}
        />
      </div>
    </div>
  );
}

// ── IC-trend ──────────────────────────────────────────────────────────────────

function IcTrendPanel() {
  const { data, isLoading } = useMlIcTrend(12);

  if (isLoading) return <Skeleton className="h-64" />;
  if (!data?.length)
    return (
      <div className="h-64 flex items-center justify-center text-sm text-[var(--color-text-muted)]">
        Inte tillräckligt med utfallsdata än (behövs ≥ 30 dagars prediktioner + 30d väntetid)
      </div>
    );

  return (
    <div>
      <h3 className="text-sm font-medium text-[var(--color-text-secondary)] mb-3">
        IC-trend per månad (live från prediction_outcomes)
      </h3>
      <ResponsiveContainer width="100%" height={240}>
        <AreaChart data={data} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
          <XAxis
            dataKey="month"
            tick={{ fontSize: 10, fill: "var(--color-text-muted)" }}
            tickFormatter={(v) => v.slice(5)} // "01" istf "2026-01"
          />
          <YAxis
            tick={{ fontSize: 10, fill: "var(--color-text-muted)" }}
            domain={[-0.1, 0.2]}
            tickFormatter={(v) => v.toFixed(2)}
          />
          <Tooltip
            contentStyle={{
              background: "var(--color-bg-elevated)",
              border: "1px solid var(--color-border)",
              borderRadius: 8,
              fontSize: 12,
            }}
            formatter={(v: number) => [v.toFixed(4), "IC"]}
          />
          <ReferenceLine y={0.05} stroke="var(--color-success)" strokeDasharray="4 4" label={{ value: "Mål 0.05", fontSize: 10, fill: "var(--color-success)" }} />
          <ReferenceLine y={0} stroke="var(--color-danger)" strokeDasharray="2 2" />
          <Area
            type="monotone"
            dataKey="ic"
            stroke="var(--color-accent)"
            fill="var(--color-accent-soft)"
            strokeWidth={2}
            dot={{ r: 3, fill: "var(--color-accent)" }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

// ── Decil-analys ──────────────────────────────────────────────────────────────

function DecilePanel() {
  const { data, isLoading } = useMlDeciles(90);

  if (isLoading) return <Skeleton className="h-56" />;
  if (!data?.length)
    return (
      <div className="h-56 flex items-center justify-center text-sm text-[var(--color-text-muted)]">
        Inte tillräckligt med utfallsdata än
      </div>
    );

  const maxAbs = Math.max(...data.map((d) => Math.abs(d.avg_return)));

  return (
    <div>
      <h3 className="text-sm font-medium text-[var(--color-text-secondary)] mb-3">
        Genomsnittsavkastning per decil (ml_rank-quintiler)
      </h3>
      <ResponsiveContainer width="100%" height={200}>
        <BarChart data={data} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
          <XAxis
            dataKey="label"
            tick={{ fontSize: 10, fill: "var(--color-text-muted)" }}
          />
          <YAxis
            tick={{ fontSize: 10, fill: "var(--color-text-muted)" }}
            tickFormatter={(v) => `${(v * 100).toFixed(1)}%`}
            domain={[-maxAbs * 1.2, maxAbs * 1.2]}
          />
          <Tooltip
            contentStyle={{
              background: "var(--color-bg-elevated)",
              border: "1px solid var(--color-border)",
              borderRadius: 8,
              fontSize: 12,
            }}
            formatter={(v: number) => [`${(v * 100).toFixed(2)}%`, "Avg 30d-avk."]}
          />
          <ReferenceLine y={0} stroke="var(--color-text-muted)" />
          <Bar dataKey="avg_return" radius={[4, 4, 0, 0]}>
            {data.map((entry, index) => (
              <Cell
                key={index}
                fill={
                  entry.avg_return > 0
                    ? "var(--color-success)"
                    : "var(--color-danger)"
                }
                fillOpacity={0.7 + (index / data.length) * 0.3}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
      <p className="text-xs text-[var(--color-text-muted)] mt-2 text-center">
        Topp-decil bör ha positiv avkastning, botten-decil negativ. Stor spread = bra modell.
      </p>
    </div>
  );
}

// ── Predicted vs Actual scatter ───────────────────────────────────────────────

function ScatterPanel() {
  const { data, isLoading } = useMlOutcomes(90, true);

  if (isLoading) return <Skeleton className="h-56" />;
  if (!data?.length)
    return (
      <div className="h-56 flex items-center justify-center text-sm text-[var(--color-text-muted)]">
        Inga utvärderade prediktioner än (väntar på 30-dagars horisont)
      </div>
    );

  const chartData = data
    .filter(
      (r) =>
        r.predicted_return != null && r.realized_return_30d != null,
    )
    .slice(0, 300)
    .map((r) => ({
      x: r.predicted_return,
      y: r.realized_return_30d,
      ticker: r.ticker,
    }));

  if (!chartData.length) return null;

  return (
    <div>
      <h3 className="text-sm font-medium text-[var(--color-text-secondary)] mb-3">
        Predikterat vs faktiskt (30d-avkastning)
      </h3>
      <ResponsiveContainer width="100%" height={220}>
        <ScatterChart margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
          <XAxis
            dataKey="x"
            type="number"
            name="Predikterat"
            tick={{ fontSize: 10, fill: "var(--color-text-muted)" }}
            tickFormatter={(v) => v.toFixed(2)}
          />
          <YAxis
            dataKey="y"
            type="number"
            name="Faktiskt"
            tick={{ fontSize: 10, fill: "var(--color-text-muted)" }}
            tickFormatter={(v) => `${(v * 100).toFixed(0)}%`}
          />
          <Tooltip
            contentStyle={{
              background: "var(--color-bg-elevated)",
              border: "1px solid var(--color-border)",
              borderRadius: 8,
              fontSize: 11,
            }}
            formatter={(v: number, name: string) => [
              name === "Faktiskt"
                ? `${(v * 100).toFixed(1)}%`
                : v.toFixed(4),
              name,
            ]}
          />
          <ReferenceLine y={0} stroke="var(--color-text-muted)" strokeDasharray="2 2" />
          <Scatter
            data={chartData}
            fill="var(--color-accent)"
            fillOpacity={0.5}
          />
        </ScatterChart>
      </ResponsiveContainer>
      <p className="text-xs text-[var(--color-text-muted)] mt-1 text-center">
        Positiv lutning = modellen rankar rätt riktning
      </p>
    </div>
  );
}

// ── Topp-picks tabell ─────────────────────────────────────────────────────────

function TopPicksPanel() {
  const { data, isLoading } = useMlTopPicks(30);

  if (isLoading)
    return (
      <div className="space-y-2">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} className="h-10" />
        ))}
      </div>
    );

  if (!data?.length)
    return (
      <p className="text-sm text-[var(--color-text-muted)]">
        Inga topp-prediktioner (ml_rank ≥ 90) de senaste 30 dagarna.
      </p>
    );

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs">
        <thead>
          <tr className="border-b border-[var(--color-border)] text-[var(--color-text-muted)]">
            <th className="text-left py-2 pr-4">Aktie</th>
            <th className="text-right pr-4">ML-rank</th>
            <th className="text-right pr-4">Pred.</th>
            <th className="text-right pr-4">Faktisk 30d</th>
            <th className="text-center">Status</th>
          </tr>
        </thead>
        <tbody>
          {data.map((row) => (
            <tr
              key={`${row.ticker}-${row.predicted_at}`}
              className="border-b border-[var(--color-border)] hover:bg-[var(--color-bg-elevated)] transition-colors"
            >
              <td className="py-2 pr-4 font-medium text-[var(--color-text-primary)]">
                {row.ticker}
                <span className="ml-1 text-[var(--color-text-muted)]">
                  {row.predicted_at.slice(5)}
                </span>
              </td>
              <td className="text-right pr-4 text-[var(--color-accent)]">
                {row.ml_rank}
              </td>
              <td className="text-right pr-4 tabular-nums">
                {row.predicted_return.toFixed(4)}
              </td>
              <td className="text-right pr-4 tabular-nums">
                {row.realized_return_30d != null ? (
                  <span
                    className={
                      row.realized_return_30d >= 0
                        ? "text-[var(--color-success)]"
                        : "text-[var(--color-danger)]"
                    }
                  >
                    {row.realized_return_30d >= 0 ? "+" : ""}
                    {(row.realized_return_30d * 100).toFixed(1)}%
                  </span>
                ) : (
                  <span className="text-[var(--color-text-muted)]">–</span>
                )}
              </td>
              <td className="text-center">
                {row.outcome_status === "win" && (
                  <CheckCircle size={13} className="text-[var(--color-success)] mx-auto" />
                )}
                {row.outcome_status === "loss" && (
                  <XCircle size={13} className="text-[var(--color-danger)] mx-auto" />
                )}
                {row.outcome_status === "pending" && (
                  <Clock size={13} className="text-[var(--color-text-muted)] mx-auto" />
                )}
                {row.outcome_status === "evaluated" && (
                  <CheckCircle size={13} className="text-[var(--color-text-muted)] mx-auto" />
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Tab-rubrik helper ─────────────────────────────────────────────────────────

const TAB_STYLE = cn(
  "flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs transition-colors",
  "data-[state=active]:bg-[var(--color-accent)] data-[state=active]:text-white",
  "data-[state=inactive]:bg-[var(--color-bg-surface)] data-[state=inactive]:text-[var(--color-text-secondary)]",
  "data-[state=inactive]:border data-[state=inactive]:border-[var(--color-border)]",
  "data-[state=inactive]:hover:border-[var(--color-border-strong)]",
);

// ── Huvudvy ───────────────────────────────────────────────────────────────────

export function AiPrestandaView() {
  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Brain size={20} strokeWidth={1.5} className="text-[var(--color-accent)]" />
        <h1 className="text-xl font-semibold text-[var(--color-text-primary)]">
          AI-prestanda
        </h1>
        <span className="ml-auto text-xs px-2 py-0.5 rounded bg-[var(--color-warn-soft)] text-[var(--color-warn)]">
          Admin-only
        </span>
      </div>

      <p className="text-sm text-[var(--color-text-secondary)]">
        Spårar ML-scoringmodellens prestation i realtid. Data från{" "}
        <code className="text-xs bg-[var(--color-bg-elevated)] px-1 rounded">
          prediction_outcomes
        </code>{" "}
        — loggas vid varje pipeline-körning, utfallet fylls i automatiskt efter 30 dagar.
      </p>

      <Tabs.Root defaultValue="oversikt">
        <Tabs.List className="flex gap-1 flex-wrap">
          <Tabs.Trigger value="oversikt" className={TAB_STYLE}>
            <Target size={13} strokeWidth={1.5} />
            Översikt
          </Tabs.Trigger>
          <Tabs.Trigger value="ic-trend" className={TAB_STYLE}>
            <TrendingUp size={13} strokeWidth={1.5} />
            IC-trend
          </Tabs.Trigger>
          <Tabs.Trigger value="deciler" className={TAB_STYLE}>
            <BarChart2 size={13} strokeWidth={1.5} />
            Decil-analys
          </Tabs.Trigger>
          <Tabs.Trigger value="scatter" className={TAB_STYLE}>
            <RefreshCw size={13} strokeWidth={1.5} />
            Pred vs Faktisk
          </Tabs.Trigger>
          <Tabs.Trigger value="picks" className={TAB_STYLE}>
            <ListChecks size={13} strokeWidth={1.5} />
            Topp-picks
          </Tabs.Trigger>
        </Tabs.List>

        <div className="mt-4 rounded-xl border border-[var(--color-border)] bg-[var(--color-bg-surface)] p-5 space-y-6">
          <Tabs.Content value="oversikt">
            <OverviewPanel />
          </Tabs.Content>
          <Tabs.Content value="ic-trend">
            <IcTrendPanel />
          </Tabs.Content>
          <Tabs.Content value="deciler">
            <DecilePanel />
          </Tabs.Content>
          <Tabs.Content value="scatter">
            <ScatterPanel />
          </Tabs.Content>
          <Tabs.Content value="picks">
            <TopPicksPanel />
          </Tabs.Content>
        </div>
      </Tabs.Root>
    </div>
  );
}
