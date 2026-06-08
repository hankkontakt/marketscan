"use client";

import Link from "next/link";
import { ArrowLeft, Loader2, AlertCircle, TrendingUp, TrendingDown } from "lucide-react";
import { useBacktestResults } from "@/hooks/useStrategies";
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer,
  CartesianGrid, ReferenceLine,
} from "recharts";
import { cn } from "@/lib/utils";

function MetricCard({ label, value, positive }: { label: string; value: string | null; positive?: boolean | null }) {
  const c = positive === true ? "text-emerald-400" : positive === false ? "text-red-400" : "text-[var(--color-text-primary)]";
  return (
    <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-bg-card)] p-4">
      <div className="text-xs text-[var(--color-text-muted)] mb-1">{label}</div>
      <div className={cn("text-2xl font-semibold tabular-nums", c)}>{value ?? "–"}</div>
    </div>
  );
}

export function StrategyResultView({ strategyId }: { strategyId: string }) {
  const { data, isLoading, isError } = useBacktestResults(strategyId);

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-24 gap-3 text-[var(--color-text-muted)]">
        <Loader2 size={28} strokeWidth={1.5} className="animate-spin" />
        <p className="text-sm">Laddar backtest-resultat…</p>
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="flex flex-col items-center justify-center py-16 gap-3">
        <AlertCircle size={28} className="text-red-400" />
        <p className="text-sm text-[var(--color-text-muted)]">Kunde inte ladda resultat</p>
        <Link href="/strategi-lab" className="text-sm text-[var(--color-accent)] hover:underline">← Tillbaka</Link>
      </div>
    );
  }

  if ((data as any).status === "no_runs") {
    return (
      <div className="flex flex-col items-center justify-center py-16 gap-3">
        <p className="text-sm text-[var(--color-text-muted)]">Inga backtester körda ännu</p>
        <Link href="/strategi-lab" className="text-sm text-[var(--color-accent)] hover:underline">← Tillbaka</Link>
      </div>
    );
  }

  const { run, equity_curve } = data;
  const isPending = run.status === "pending" || run.status === "running";

  // Normalize equity curve to 100 at start
  const base = equity_curve[0]?.portfolio_value ?? 100_000;
  const chartData = equity_curve.map(e => ({
    date: e.date,
    value: base > 0 ? Math.round((e.portfolio_value / base) * 100 * 10) / 10 : 0,
    positions: e.num_positions,
  }));

  const totalPos = run.total_return_pct != null ? run.total_return_pct > 0 : null;

  return (
    <div className="max-w-4xl space-y-6">

      {/* Header */}
      <div className="flex items-center gap-3">
        <Link href="/strategi-lab" className="p-1.5 rounded-lg hover:bg-[var(--color-bg-elevated)] transition-colors">
          <ArrowLeft size={16} strokeWidth={1.5} className="text-[var(--color-text-muted)]" />
        </Link>
        <div>
          <h1 className="text-xl font-semibold text-[var(--color-text-primary)]">Backtest-resultat</h1>
          <p className="text-xs text-[var(--color-text-muted)]">
            {run.start_date} → {run.end_date} · status: {run.status}
          </p>
        </div>
        {isPending && (
          <div className="ml-auto flex items-center gap-2 text-xs text-blue-400">
            <Loader2 size={12} className="animate-spin" />
            Beräknar… (uppdateras automatiskt)
          </div>
        )}
      </div>

      {/* Metrics */}
      {run.status === "completed" && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <MetricCard label="Total avkastning" value={run.total_return_pct != null ? `${run.total_return_pct > 0 ? "+" : ""}${run.total_return_pct.toFixed(1)}%` : null} positive={totalPos} />
          <MetricCard label="CAGR" value={run.cagr_pct != null ? `${run.cagr_pct.toFixed(1)}%/år` : null} positive={run.cagr_pct != null ? run.cagr_pct > 0 : null} />
          <MetricCard label="Sharpe-kvot" value={run.sharpe_ratio?.toFixed(2) ?? null} positive={run.sharpe_ratio != null ? run.sharpe_ratio >= 1 : null} />
          <MetricCard label="Max drawdown" value={run.max_drawdown_pct != null ? `${run.max_drawdown_pct.toFixed(1)}%` : null} positive={run.max_drawdown_pct != null ? run.max_drawdown_pct > -15 : null} />
          <MetricCard label="Volatilitet" value={run.volatility_ann != null ? `${run.volatility_ann.toFixed(1)}%` : null} />
          <MetricCard label="Win rate" value={run.win_rate_pct != null ? `${run.win_rate_pct.toFixed(1)}%` : null} positive={run.win_rate_pct != null ? run.win_rate_pct > 50 : null} />
          <MetricCard label="Antal affärer" value={run.total_trades != null ? String(run.total_trades) : null} />
          <MetricCard label="Genomsnittlig hålltid" value={run.avg_hold_days != null ? `${run.avg_hold_days.toFixed(0)} dagar` : null} />
        </div>
      )}

      {/* Equity curve */}
      {equity_curve.length > 1 && (
        <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-bg-card)] p-5">
          <h2 className="text-sm font-semibold text-[var(--color-text-primary)] mb-4">
            Portföljutveckling (normaliserad till 100)
          </h2>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={chartData}>
              <CartesianGrid stroke="var(--color-border)" strokeDasharray="3 3" strokeOpacity={0.5} />
              <XAxis
                dataKey="date"
                tickFormatter={d => d?.slice(0, 7)}
                tick={{ fontSize: 10, fill: "var(--color-text-muted)" }}
                tickLine={false}
                axisLine={false}
                interval="preserveStartEnd"
              />
              <YAxis
                tick={{ fontSize: 10, fill: "var(--color-text-muted)" }}
                tickLine={false}
                axisLine={false}
                tickFormatter={v => `${v}`}
              />
              <ReferenceLine y={100} stroke="var(--color-border)" strokeDasharray="4 2" />
              <Tooltip
                contentStyle={{
                  background: "var(--color-bg-card)",
                  border: "1px solid var(--color-border)",
                  borderRadius: 8,
                  fontSize: 12,
                }}
                formatter={(v: number) => [`${v}`, "Index"]}
                labelFormatter={l => `Datum: ${l}`}
              />
              <Line
                type="monotone"
                dataKey="value"
                stroke="var(--color-accent)"
                strokeWidth={1.5}
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Number of positions over time */}
      {equity_curve.length > 1 && (
        <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-bg-card)] p-5">
          <h2 className="text-sm font-semibold text-[var(--color-text-primary)] mb-4">Antal positioner</h2>
          <ResponsiveContainer width="100%" height={120}>
            <LineChart data={chartData}>
              <XAxis dataKey="date" tickFormatter={d => d?.slice(0, 7)} tick={{ fontSize: 10, fill: "var(--color-text-muted)" }} tickLine={false} axisLine={false} interval="preserveStartEnd" />
              <YAxis tick={{ fontSize: 10, fill: "var(--color-text-muted)" }} tickLine={false} axisLine={false} allowDecimals={false} />
              <Tooltip contentStyle={{ background: "var(--color-bg-card)", border: "1px solid var(--color-border)", borderRadius: 8, fontSize: 12 }} formatter={(v: number) => [v, "Positioner"]} />
              <Line type="step" dataKey="positions" stroke="#94a3b8" strokeWidth={1.5} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

    </div>
  );
}
