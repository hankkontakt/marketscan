"use client";

import { useState } from "react";
import { Briefcase, RefreshCw, AlertTriangle, Info } from "lucide-react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useRiskProfile } from "@/hooks/useRiskProfile";
import { toast } from "sonner";

interface PerPosition {
  ticker: string;
  weight: number;
  name?: string | null;
}

interface ConstructResponse {
  method: string;
  weights: PerPosition[];
  expected_return: number;
  expected_volatility: number;
  sharpe: number;
  var_95: number;
  disclaimer: string;
}

function DonutChart({ weights }: { weights: PerPosition[] }) {
  const total = weights.reduce((s, w) => s + w.weight, 0);
  if (total === 0) return null;

  const COLORS = [
    "var(--color-accent)", "var(--color-up)", "var(--color-warn)",
    "var(--color-down)", "#8b5cf6", "#06b6d4", "#f43f5e",
    "#10b981", "#f59e0b", "#6366f1",
  ];

  let cumulative = 0;
  const segments = weights.map((w, i) => {
    const pct = (w.weight / total) * 100;
    const start = cumulative;
    cumulative += pct;
    return { ...w, pct, start, color: COLORS[i % COLORS.length] };
  });

  return (
    <div className="flex items-center gap-6">
      <svg width="140" height="140" viewBox="0 0 100 100" className="shrink-0">
        {segments.map((s, i) => {
          const r = 38;
          const circumference = 2 * Math.PI * r;
          const offset = circumference - (s.pct / 100) * circumference;
          const rot = (s.start / 100) * 360 - 90;
          return (
            <circle
              key={i}
              cx="50" cy="50" r={r}
              fill="none"
              stroke={s.color}
              strokeWidth={12}
              strokeDasharray={circumference}
              strokeDashoffset={offset}
              transform={`rotate(${rot} 50 50)`}
              className="transition-all duration-500"
            />
          );
        })}
      </svg>
      <div className="space-y-1">
        {segments.map((s, i) => (
          <div key={i} className="flex items-center gap-2 text-xs">
            <span className="w-2.5 h-2.5 rounded-sm shrink-0" style={{ background: s.color }} />
            <span className="text-[var(--color-text-secondary)]">{s.ticker}</span>
            <span className="font-mono text-[var(--color-text-primary)]">{s.pct.toFixed(1)}%</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export function PortfolioBuilderView() {
  const qc = useQueryClient();
  const [useProfile, setUseProfile] = useState(true);

  const { data: profile } = useRiskProfile();
  const [result, setResult] = useState<ConstructResponse | null>(null);

  const constructMutation = useMutation({
    mutationFn: () =>
      api<ConstructResponse>("/api/portfolio/construct", {
        method: "POST",
        body: JSON.stringify({ use_profile: useProfile }),
      }),
    onSuccess: (data) => {
      setResult(data);
      toast.success("Portföljförslag skapat!");
    },
    onError: (err: Error) => toast.error(`Kunde inte skapa portfölj: ${err.message}`),
  });

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-[var(--color-accent-soft)] flex items-center justify-center">
          <Briefcase size={20} className="text-[var(--color-accent)]" />
        </div>
        <div>
          <h1 className="text-lg font-bold text-[var(--color-text-primary)]">Portföljbyggare</h1>
          <p className="text-xs text-[var(--color-text-muted)]">
            Konstruera en portfölj baserad på riskprofil och AI-analys (Black-Litterman)
          </p>
        </div>
      </div>

      {/* Controls */}
      <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-bg-surface)] p-4 space-y-4">
        <div className="flex items-center gap-4">
          <label className="flex items-center gap-2 text-xs cursor-pointer">
            <input
              type="checkbox"
              checked={useProfile}
              onChange={(e) => setUseProfile(e.target.checked)}
              className="accent-[var(--color-accent)]"
            />
            Använd riskprofil
            {profile && (
              <span className="text-[var(--color-text-muted)]">
                ({(profile as { profile: string }).profile}, {(profile as { risk_score: number }).risk_score}p)
              </span>
            )}
          </label>

          <button
            onClick={() => constructMutation.mutate()}
            disabled={constructMutation.isPending}
            className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium
                       bg-[var(--color-accent)] text-white disabled:opacity-40"
          >
            {constructMutation.isPending ? (
              <RefreshCw size={14} className="animate-spin" />
            ) : (
              <Briefcase size={14} />
            )}
            {constructMutation.isPending ? "Beräknar..." : "Föreslå portfölj"}
          </button>
        </div>

        {!profile && useProfile && (
          <div className="flex items-center gap-2 text-xs text-[var(--color-warn)]">
            <AlertTriangle size={12} />
            Ingen riskprofil sparad — använder "Balanserad". Gå till Inställningar → Riskprofil.
          </div>
        )}
      </div>

      {/* Results */}
      {result && (
        <>
          <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-bg-surface)] p-4 space-y-4">
            <h2 className="text-sm font-semibold text-[var(--color-text-primary)]">
              Portföljförslag ({result.method === "black_litterman" ? "Black-Litterman" : "Riskparitet"})
            </h2>

            <DonutChart weights={result.weights} />

            {/* Stats */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {[
                { label: "Förväntad avkastning", value: `${(result.expected_return * 100).toFixed(1)}%` },
                { label: "Volatilitet", value: `${(result.expected_volatility * 100).toFixed(1)}%` },
                { label: "Sharpe-kvot", value: result.sharpe.toFixed(2) },
                { label: "VaR (95%)", value: `${(result.var_95 * 100).toFixed(1)}%` },
              ].map((stat) => (
                <div key={stat.label} className="p-2 rounded-lg bg-[var(--color-bg-elevated)]">
                  <div className="text-[10px] text-[var(--color-text-muted)]">{stat.label}</div>
                  <div className="font-mono text-sm font-medium text-[var(--color-text-primary)]">{stat.value}</div>
                </div>
              ))}
            </div>

            {/* Viktlista */}
            <div className="space-y-1">
              {result.weights.filter((w) => w.weight > 0.001).map((w) => (
                <div key={w.ticker} className="flex items-center justify-between py-1 text-xs">
                  <span className="font-medium text-[var(--color-text-primary)]">{w.ticker}</span>
                  <span className="font-mono text-[var(--color-text-secondary)]">{(w.weight * 100).toFixed(1)}%</span>
                </div>
              ))}
            </div>
          </div>

          {/* Disclaimer */}
          <div className="flex items-start gap-2 text-xs text-[var(--color-text-muted)] p-3 rounded-xl bg-[var(--color-bg-elevated)]">
            <AlertTriangle size={12} className="mt-0.5 shrink-0" />
            <p>{result.disclaimer}</p>
          </div>
        </>
      )}
    </div>
  );
}
