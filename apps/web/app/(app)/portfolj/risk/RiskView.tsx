"use client";

import { useState } from "react";
import Link from "next/link";
import {
  ShieldCheck, TrendingDown, TrendingUp, BarChart3, Activity,
  ArrowLeft, RefreshCw, Target, Info, ChevronRight, Loader2,
} from "lucide-react";
import {
  useRiskAnalytics, useFactorExposure, useCorrelationMatrix,
  useOptimizedWeights, useRebalanceSuggestions, useRebalancingTargets,
} from "@/hooks/usePortfolio";
import {
  RadarChart, Radar, PolarGrid, PolarAngleAxis, ResponsiveContainer,
  BarChart, Bar, XAxis, YAxis, Tooltip, Cell, LineChart, Line,
} from "recharts";
import { cn } from "@/lib/utils";
import { toast } from "sonner";

// ─── Small helpers ────────────────────────────────────────────────────────────

function MetricTile({
  label, value, sub, good, bad, neutral
}: {
  label: string; value: string | null; sub?: string;
  good?: boolean; bad?: boolean; neutral?: boolean;
}) {
  const color = good ? "text-emerald-500" : bad ? "text-red-400" : "text-[var(--color-text-primary)]";
  return (
    <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-bg-card)] p-4 flex flex-col gap-1">
      <span className="text-xs text-[var(--color-text-muted)]">{label}</span>
      <span className={cn("text-2xl font-semibold tabular-nums", color)}>
        {value ?? "–"}
      </span>
      {sub && <span className="text-xs text-[var(--color-text-muted)]">{sub}</span>}
    </div>
  );
}

function SectionHeader({ icon: Icon, title, sub }: { icon: any; title: string; sub?: string }) {
  return (
    <div className="flex items-center gap-3 mb-4">
      <div className="p-2 rounded-lg bg-[var(--color-accent-soft)]">
        <Icon size={16} strokeWidth={1.5} className="text-[var(--color-accent)]" />
      </div>
      <div>
        <h2 className="text-sm font-semibold text-[var(--color-text-primary)]">{title}</h2>
        {sub && <p className="text-xs text-[var(--color-text-muted)]">{sub}</p>}
      </div>
    </div>
  );
}

// ─── Correlation heatmap ──────────────────────────────────────────────────────

function CorrelationHeatmap() {
  const { data, isLoading } = useCorrelationMatrix();
  if (isLoading) return <div className="h-48 flex items-center justify-center text-[var(--color-text-muted)] text-sm">Laddar korrelationer…</div>;
  if (!data || data.tickers.length < 2) return <p className="text-sm text-[var(--color-text-muted)]">Minst 2 innehav krävs för korrelationsmatris.</p>;

  const { tickers, matrix } = data;
  const n = tickers.length;

  function corrColor(v: number) {
    // Green = negative (diversifying), Red = positive (correlated)
    if (v >= 0.7) return "bg-red-500/80";
    if (v >= 0.4) return "bg-orange-400/70";
    if (v >= 0.1) return "bg-yellow-400/60";
    if (v >= -0.1) return "bg-[var(--color-bg-elevated)]";
    if (v >= -0.4) return "bg-emerald-400/60";
    return "bg-emerald-600/80";
  }

  return (
    <div className="overflow-x-auto">
      <table className="text-xs border-collapse min-w-full">
        <thead>
          <tr>
            <th className="w-10" />
            {tickers.map(t => (
              <th key={t} className="px-1 py-1 text-[var(--color-text-muted)] font-normal text-center w-12">{t}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {matrix.map((row, i) => (
            <tr key={tickers[i]}>
              <td className="pr-2 text-[var(--color-text-muted)] text-right">{tickers[i]}</td>
              {row.map((v, j) => (
                <td key={j} className={cn("text-center py-1 rounded", corrColor(v))}>
                  <span className={cn("font-mono", v === 1 ? "text-[var(--color-text-muted)]" : "text-[var(--color-text-primary)]")}>
                    {v.toFixed(2)}
                  </span>
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      <div className="flex items-center gap-4 mt-3 text-xs text-[var(--color-text-muted)]">
        <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-red-500/80 inline-block" /> Hög korrelation (risk)</span>
        <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-emerald-500/80 inline-block" /> Negativ (diversifiering)</span>
      </div>
    </div>
  );
}

// ─── Factor radar chart ───────────────────────────────────────────────────────

function FactorRadar() {
  const { data, isLoading } = useFactorExposure();
  if (isLoading) return <div className="h-48 flex items-center justify-center text-sm text-[var(--color-text-muted)]">Laddar faktorer…</div>;
  if (!data) return null;

  const factorLabels: Record<string, string> = {
    factor_value: "Värde",
    factor_momentum: "Momentum",
    factor_quality: "Kvalitet",
    factor_growth: "Tillväxt",
    factor_dividend: "Utdelning",
    factor_risk: "Risk",
  };

  const radarData = Object.entries(factorLabels).map(([key, label]) => ({
    subject: label,
    portfölj: (data as any)[key] ?? 0,
    benchmark: (data as any)[key.replace("factor_", "bench_")] ?? 0,
  }));

  return (
    <ResponsiveContainer width="100%" height={280}>
      <RadarChart data={radarData}>
        <PolarGrid stroke="var(--color-border)" />
        <PolarAngleAxis
          dataKey="subject"
          tick={{ fill: "var(--color-text-muted)", fontSize: 11 }}
        />
        <Radar
          name="Din portfölj"
          dataKey="portfölj"
          stroke="var(--color-accent)"
          fill="var(--color-accent)"
          fillOpacity={0.3}
        />
        <Radar
          name="Benchmark"
          dataKey="benchmark"
          stroke="#94a3b8"
          fill="#94a3b8"
          fillOpacity={0.15}
        />
        <Tooltip
          contentStyle={{
            background: "var(--color-bg-card)",
            border: "1px solid var(--color-border)",
            borderRadius: 8,
            fontSize: 12,
          }}
          formatter={(v: number) => v.toFixed(1)}
        />
      </RadarChart>
    </ResponsiveContainer>
  );
}

// ─── Rebalance drift bars ─────────────────────────────────────────────────────

function RebalanceDriftView() {
  const { data, isLoading } = useRebalanceSuggestions();

  if (isLoading) return <div className="h-32 flex items-center justify-center text-sm text-[var(--color-text-muted)]">Laddar rebalanseringsanalys…</div>;
  if (!data) return null;

  const actionColor = (a: string) =>
    a === "buy" ? "text-emerald-500" : a === "sell" ? "text-red-400" : "text-[var(--color-text-muted)]";

  const actionLabel = (a: string) =>
    a === "buy" ? "Köp" : a === "sell" ? "Sälj" : "Behåll";

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between text-xs text-[var(--color-text-muted)]">
        <span>Mål: <strong className="text-[var(--color-text-primary)]">{data.target_name}</strong></span>
        <span>Totalt värde: <strong className="text-[var(--color-text-primary)]">{data.total_value.toLocaleString("sv-SE", { maximumFractionDigits: 0 })} kr</strong></span>
      </div>

      {!data.drifted && (
        <div className="flex items-center gap-2 text-sm text-emerald-500 bg-emerald-500/10 rounded-lg p-3">
          <ShieldCheck size={15} />
          Portföljen är i balans — ingen åtgärd krävs
        </div>
      )}

      <div className="space-y-2">
        {data.holdings.map(h => (
          <div key={h.ticker} className="flex items-center gap-3 text-sm">
            <span className="w-14 font-mono text-[var(--color-text-secondary)]">{h.ticker}</span>
            <div className="flex-1 relative h-6 rounded bg-[var(--color-bg-elevated)] overflow-hidden">
              {/* Current allocation */}
              <div
                className="absolute inset-y-0 left-0 bg-[var(--color-accent)]/40"
                style={{ width: `${Math.min(h.current_pct, 100)}%` }}
              />
              {/* Target allocation */}
              {h.target_pct !== null && (
                <div
                  className="absolute inset-y-0 top-0 w-0.5 bg-[var(--color-accent)]"
                  style={{ left: `${Math.min(h.target_pct, 100)}%` }}
                />
              )}
            </div>
            <span className="w-12 text-right tabular-nums text-[var(--color-text-muted)]">{h.current_pct.toFixed(1)}%</span>
            <span className={cn("w-16 text-right font-medium", actionColor(h.action))}>
              {actionLabel(h.action)}
              {h.amount_sek ? ` ${Math.round(h.amount_sek).toLocaleString("sv-SE")} kr` : ""}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Optimal weights comparison ───────────────────────────────────────────────

function OptimizeView() {
  const { data: opts, isLoading } = useOptimizedWeights();
  const [activeMethod, setActiveMethod] = useState<"hrp" | "minvar" | "equal">("hrp");

  if (isLoading) return <div className="h-32 flex items-center justify-center text-sm text-[var(--color-text-muted)]">Laddar optimal portfölj…</div>;
  if (!opts || opts.length === 0) return null;

  const active = opts.find(o => o.method === activeMethod);
  if (!active) return null;

  const chartData = Object.entries(active.weights)
    .sort((a, b) => b[1] - a[1])
    .map(([ticker, w]) => ({ ticker, weight: Math.round(w * 100) }));

  const methodLabels: Record<string, string> = {
    hrp: "HRP (hierarkisk riskparitet)",
    minvar: "Minimal varians",
    equal: "Lika viktning",
  };

  return (
    <div className="space-y-4">
      <div className="flex gap-2">
        {(["hrp", "minvar", "equal"] as const).map(m => (
          <button
            key={m}
            onClick={() => setActiveMethod(m)}
            className={cn(
              "px-3 py-1.5 rounded-lg text-xs font-medium transition-colors",
              activeMethod === m
                ? "bg-[var(--color-accent)] text-white"
                : "bg-[var(--color-bg-elevated)] text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]"
            )}
          >
            {m.toUpperCase()}
          </button>
        ))}
      </div>
      <p className="text-xs text-[var(--color-text-muted)]">{methodLabels[activeMethod]}</p>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={chartData} layout="vertical" barSize={16}>
          <XAxis type="number" domain={[0, 100]} tick={{ fontSize: 10, fill: "var(--color-text-muted)" }}
            tickFormatter={v => `${v}%`} />
          <YAxis type="category" dataKey="ticker" tick={{ fontSize: 11, fill: "var(--color-text-secondary)" }} width={52} />
          <Tooltip
            contentStyle={{ background: "var(--color-bg-card)", border: "1px solid var(--color-border)", borderRadius: 8, fontSize: 12 }}
            formatter={(v: number) => [`${v}%`, "Vikt"]}
          />
          <Bar dataKey="weight" radius={[0, 4, 4, 0]}>
            {chartData.map((_, i) => (
              <Cell key={i} fill={`hsl(${220 + i * 12}, 70%, 60%)`} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

// ─── Main view ────────────────────────────────────────────────────────────────

export function RiskView() {
  const { data: risk, isLoading, isError } = useRiskAnalytics();

  const sharpeGood = (risk?.sharpe_ratio ?? 0) >= 1.0;
  const sharpeBad  = (risk?.sharpe_ratio ?? 0) < 0.5 && risk?.sharpe_ratio !== null;
  const drawGood   = (risk?.max_drawdown_pct ?? -100) > -15;
  const drawBad    = (risk?.max_drawdown_pct ?? 0) < -25;
  const volGood    = (risk?.volatility_ann ?? 100) < 15;

  return (
    <div className="max-w-4xl space-y-8">

      {/* Header */}
      <div className="flex items-center gap-3">
        <Link href="/portfolj" className="p-1.5 rounded-lg hover:bg-[var(--color-bg-elevated)] transition-colors">
          <ArrowLeft size={16} strokeWidth={1.5} className="text-[var(--color-text-muted)]" />
        </Link>
        <div>
          <h1 className="text-xl font-semibold text-[var(--color-text-primary)]">Riskanalys</h1>
          <p className="text-xs text-[var(--color-text-muted)]">
            {risk?.is_cached
              ? `Beräknad ${risk.computed_at ? new Date(risk.computed_at).toLocaleDateString("sv-SE") : "natt"}`
              : "Realtidsberäkning (cache saknas — kör nattlig analys)"}
          </p>
        </div>
      </div>

      {isError && (
        <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-400">
          Kunde inte ladda riskdata. Kontrollera att du har en portfölj med innehav.
        </div>
      )}

      {/* Key Metrics */}
      <section>
        <SectionHeader icon={ShieldCheck} title="Nyckeltal" sub="Baserat på nattlig beräkning med 1 år prishistorik" />
        {isLoading ? (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {Array.from({ length: 8 }).map((_, i) => (
              <div key={i} className="h-24 rounded-xl bg-[var(--color-bg-elevated)] animate-pulse" />
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <MetricTile
              label="Sharpe-kvot"
              value={risk?.sharpe_ratio?.toFixed(2) ?? null}
              sub="≥1.0 är bra"
              good={sharpeGood} bad={sharpeBad}
            />
            <MetricTile
              label="Sortino-kvot"
              value={risk?.sortino_ratio?.toFixed(2) ?? null}
              sub="Justerat för nedsidesvarians"
            />
            <MetricTile
              label="Max drawdown"
              value={risk?.max_drawdown_pct ? `${risk.max_drawdown_pct.toFixed(1)}%` : null}
              sub="Största fall från topp"
              good={drawGood} bad={drawBad}
            />
            <MetricTile
              label="Volatilitet (årl.)"
              value={risk?.volatility_ann ? `${risk.volatility_ann.toFixed(1)}%` : null}
              sub="Standardavvikelse"
              good={volGood}
            />
            <MetricTile
              label="VaR 95% (1-dag)"
              value={risk?.var_95_pct ? `${risk.var_95_pct.toFixed(2)}%` : null}
              sub="Value at Risk"
            />
            <MetricTile
              label="CVaR 95%"
              value={risk?.cvar_95_pct ? `${risk.cvar_95_pct.toFixed(2)}%` : null}
              sub="Förväntad förlust bortom VaR"
            />
            <MetricTile
              label="Beta (marknad)"
              value={risk?.beta_market?.toFixed(2) ?? null}
              sub="vs OMXS30"
              good={(risk?.beta_market ?? 2) < 1.2}
              bad={(risk?.beta_market ?? 0) > 1.5}
            />
            <MetricTile
              label="Koncentration HHI"
              value={risk?.sector_hhi ? `${(risk.sector_hhi * 100).toFixed(0)}` : null}
              sub="0=spridd, 100=koncentrerad"
              good={(risk?.sector_hhi ?? 1) < 0.25}
              bad={(risk?.sector_hhi ?? 0) > 0.5}
            />
          </div>
        )}
      </section>

      {/* Correlation Heatmap */}
      <section className="rounded-xl border border-[var(--color-border)] bg-[var(--color-bg-card)] p-5">
        <SectionHeader
          icon={Activity}
          title="Korrelationsmatris"
          sub="Hur innehaven rör sig i förhållande till varandra (1-år prishistorik)"
        />
        <CorrelationHeatmap />
      </section>

      {/* Factor exposure radar */}
      <section className="rounded-xl border border-[var(--color-border)] bg-[var(--color-bg-card)] p-5">
        <SectionHeader
          icon={BarChart3}
          title="Faktorexponering"
          sub="Din portfölj vs universumets genomsnitt — visar vilka faktorer du är överviktad i"
        />
        <FactorRadar />
        <p className="text-xs text-[var(--color-text-muted)] mt-2">
          Blå = din portfölj · Grå = benchmark (alla bolag i screener)
        </p>
      </section>

      {/* Optimal portfolio weights */}
      <section className="rounded-xl border border-[var(--color-border)] bg-[var(--color-bg-card)] p-5">
        <SectionHeader
          icon={Target}
          title="Optimal portföljviktning"
          sub="Föreslagna vikter enligt tre portföljoptimerings-metoder"
        />
        <OptimizeView />
        <div className="mt-3 text-xs text-[var(--color-text-muted)] space-y-1">
          <p><strong>HRP</strong> — Hierarkisk riskparitet: tar hänsyn till korrelationer, robust mot estimeringsbrus.</p>
          <p><strong>Minvar</strong> — Minimerar total portföljvarians (kvadratisk optimering).</p>
          <p><strong>Lika viktning</strong> — Enkel referensportfölj.</p>
        </div>
      </section>

      {/* Rebalancing */}
      <section className="rounded-xl border border-[var(--color-border)] bg-[var(--color-bg-card)] p-5">
        <SectionHeader
          icon={RefreshCw}
          title="Rebalanseringsanalys"
          sub="Avvikelse från optimala vikter — åtgärd krävs om drift > 5%"
        />
        <RebalanceDriftView />
        <div className="mt-4 pt-4 border-t border-[var(--color-border)]">
          <Link
            href="/portfolj/risk/rebalance"
            className="flex items-center gap-2 text-sm text-[var(--color-accent)] hover:underline"
          >
            Hantera målallokeringar <ChevronRight size={14} />
          </Link>
        </div>
      </section>

    </div>
  );
}
