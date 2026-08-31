"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { formatPrice } from "@/lib/format";
import { ShieldCheck, ArrowRight, Sparkles, Scale, RefreshCw, CheckCircle2, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

interface ActionItem {
  action: "KÖP" | "SÄLJ" | string;
  asset_type: "FOND" | "AKTIE" | string;
  name: string;
  ticker?: string;
  shares?: number;
  amount_sek: number;
  reason: string;
}

interface RebalancePlanResponse {
  success: boolean;
  current_allocation: {
    total_value_sek: number;
    funds_value_sek: number;
    stocks_value_sek: number;
    funds_pct: number;
    stocks_pct: number;
    sector_weights: Record<string, number>;
  };
  target_allocation: {
    funds_pct: number;
    stocks_pct: number;
    max_sector_cap_pct: number;
  };
  smart_deposit_plan?: {
    deposit_sek: number;
    actions: ActionItem[];
    tax_and_fee_benefit: string;
  } | null;
  one_time_rebalance_orders: ActionItem[];
  risk_impact: {
    max_sector_before_pct: number;
    max_sector_after_pct: number;
    estimated_volatility_before_pct: number;
    estimated_volatility_after_pct: number;
    estimated_max_drawdown_before_pct: number;
    estimated_max_drawdown_after_pct: number;
  };
  summary_swedish: string;
}

export function RebalanceView() {
  const [depositAmount, setDepositAmount] = useState<string>("5000");
  const [mode, setMode] = useState<"deposit" | "onetime">("deposit");

  const { data: plan, isLoading } = useQuery<RebalancePlanResponse>({
    queryKey: ["portfolio-rebalance-plan", depositAmount],
    queryFn: () =>
      api<RebalancePlanResponse>("/api/portfolio/rebalance/plan", {
        method: "POST",
        body: JSON.stringify({
          target_funds_pct: 60.0,
          target_stocks_pct: 40.0,
          max_sector_cap_pct: 25.0,
          monthly_deposit_sek: depositAmount ? parseFloat(depositAmount) : null,
        }),
      }),
  });

  if (isLoading) {
    return (
      <div className="rounded-2xl border p-8 bg-[var(--color-bg-surface)] border-[var(--color-border)] text-center space-y-3">
        <Loader2 size={24} className="animate-spin mx-auto text-[var(--color-accent)]" />
        <p className="text-xs text-[var(--color-text-muted)]">Beräknar optimal fördelning...</p>
      </div>
    );
  }

  if (!plan || !plan.success) {
    return (
      <div className="rounded-2xl border p-8 bg-[var(--color-bg-surface)] border-[var(--color-border)] text-center space-y-2">
        <Scale size={28} className="mx-auto text-[var(--color-text-muted)]" />
        <h3 className="text-sm font-semibold text-[var(--color-text-primary)]">Inga innehav att rebalansera</h3>
        <p className="text-xs text-[var(--color-text-muted)]">
          Lägg till aktier eller fonder i din portfölj för att aktivera den skandinaviska rebalancern.
        </p>
      </div>
    );
  }

  const alloc = plan.current_allocation;
  const isBalanced = Math.abs(alloc.funds_pct - 60.0) <= 3.0;

  return (
    <div className="space-y-6">
      {/* ── 1. Lugn Översikt (Lysa-stil) ─────────────────────────────────── */}
      <div className="rounded-2xl border p-6 bg-[var(--color-bg-surface)] border-[var(--color-border)] space-y-5">
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-[var(--color-accent-soft)] flex items-center justify-center text-[var(--color-accent)]">
              <Scale size={20} strokeWidth={1.75} />
            </div>
            <div>
              <h2 className="text-base font-bold text-[var(--color-text-primary)]">
                Portföljbalans & Målfördelning
              </h2>
              <p className="text-xs text-[var(--color-text-muted)]">
                Klassisk Barbell 60/40 (60% Global basfond · 40% Tillväxtsatelliter)
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <span className={cn(
              "px-3 py-1 rounded-full text-xs font-semibold",
              isBalanced
                ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
                : "bg-amber-500/10 text-amber-600 dark:text-amber-400"
            )}>
              {isBalanced ? "✓ I Målbalans" : "Justering Rekommenderas"}
            </span>
          </div>
        </div>

        {/* Allocation Progress Comparison Bars */}
        <div className="space-y-3 pt-2">
          {/* Current */}
          <div className="space-y-1.5">
            <div className="flex justify-between text-xs">
              <span className="font-medium text-[var(--color-text-secondary)]">Nuvarande fördelning:</span>
              <span className="font-mono text-[var(--color-text-primary)]">
                {alloc.funds_pct}% Fonder / {alloc.stocks_pct}% Aktier
              </span>
            </div>
            <div className="h-3 rounded-full overflow-hidden flex bg-[var(--color-bg-elevated)] border border-[var(--color-border)]">
              <div
                style={{ width: `${alloc.funds_pct}%` }}
                className="bg-indigo-500 transition-all duration-500"
                title={`Fonder: ${alloc.funds_pct}%`}
              />
              <div
                style={{ width: `${alloc.stocks_pct}%` }}
                className="bg-[var(--color-accent)] transition-all duration-500"
                title={`Aktier: ${alloc.stocks_pct}%`}
              />
            </div>
          </div>

          {/* Target */}
          <div className="space-y-1.5 opacity-90">
            <div className="flex justify-between text-xs">
              <span className="text-[var(--color-text-muted)]">Målfördelning (60/40):</span>
              <span className="font-mono text-[var(--color-text-muted)]">60.0% Fonder / 40.0% Aktier</span>
            </div>
            <div className="h-2 rounded-full overflow-hidden flex bg-[var(--color-bg-elevated)] border border-[var(--color-border)]">
              <div style={{ width: "60%" }} className="bg-indigo-500/60" />
              <div style={{ width: "40%" }} className="bg-[var(--color-accent)]/60" />
            </div>
          </div>
        </div>

        {/* Summary note */}
        <p className="text-xs text-[var(--color-text-secondary)] leading-relaxed pt-1">
          {plan.summary_swedish}
        </p>
      </div>

      {/* ── 2. Åtgärdsval: Smart Nysparande vs Engångsjustering ───────────── */}
      <div className="rounded-2xl border p-6 bg-[var(--color-bg-surface)] border-[var(--color-border)] space-y-5">
        <div className="flex items-center justify-between flex-wrap gap-3 border-b border-[var(--color-border)] pb-4">
          <div className="flex gap-2">
            <button
              onClick={() => setMode("deposit")}
              className={cn(
                "px-4 py-2 rounded-xl text-xs font-semibold transition-colors flex items-center gap-1.5",
                mode === "deposit"
                  ? "bg-[var(--color-accent)] text-white shadow-sm"
                  : "bg-[var(--color-bg-elevated)] text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]"
              )}
            >
              <Sparkles size={13} />
              Smart Månadssparande (Skattefritt)
            </button>
            <button
              onClick={() => setMode("onetime")}
              className={cn(
                "px-4 py-2 rounded-xl text-xs font-semibold transition-colors flex items-center gap-1.5",
                mode === "onetime"
                  ? "bg-[var(--color-accent)] text-white shadow-sm"
                  : "bg-[var(--color-bg-elevated)] text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]"
              )}
            >
              <RefreshCw size={13} />
              Engångsrebalansering (Köp & Sälj)
            </button>
          </div>
        </div>

        {/* ── MODE 1: Smart Månadssparande ───────────────────────────────── */}
        {mode === "deposit" && (
          <div className="space-y-4">
            <div className="flex items-center gap-3 flex-wrap">
              <label className="text-xs text-[var(--color-text-secondary)] font-medium">
                Månadsinsättning att fördela:
              </label>
              <div className="relative">
                <input
                  type="number"
                  min="500"
                  step="500"
                  value={depositAmount}
                  onChange={(e) => setDepositAmount(e.target.value)}
                  className="w-36 h-9 px-3 pr-8 rounded-xl text-sm font-mono font-semibold border bg-[var(--color-bg-elevated)] border-[var(--color-border)] text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-accent)]"
                />
                <span className="absolute right-3 top-2 text-xs text-[var(--color-text-muted)]">kr</span>
              </div>
            </div>

            {plan.smart_deposit_plan?.actions && plan.smart_deposit_plan.actions.length > 0 ? (
              <div className="space-y-2.5 pt-2">
                <p className="text-xs text-emerald-600 dark:text-emerald-400 flex items-center gap-1 font-medium">
                  <CheckCircle2 size={13} />
                  {plan.smart_deposit_plan.tax_and_fee_benefit}
                </p>

                <div className="divide-y divide-[var(--color-border)] rounded-xl border border-[var(--color-border)] overflow-hidden bg-[var(--color-bg-elevated)]">
                  {plan.smart_deposit_plan.actions.map((act, i) => (
                    <div key={i} className="p-3.5 flex items-center justify-between gap-3 text-xs">
                      <div className="flex items-center gap-2.5">
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-600 dark:text-emerald-400">
                          {act.action}
                        </span>
                        <div>
                          <div className="font-semibold text-[var(--color-text-primary)]">
                            {act.name} {act.shares ? `(${act.shares} st)` : ""}
                          </div>
                          <div className="text-[11px] text-[var(--color-text-muted)]">{act.reason}</div>
                        </div>
                      </div>
                      <div className="font-mono font-bold text-sm text-[var(--color-text-primary)]">
                        +{formatPrice(act.amount_sek)}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <p className="text-xs text-[var(--color-text-muted)] py-4 text-center">
                Ange ett belopp för att räkna ut den optimala nysparande-fördelningen.
              </p>
            )}
          </div>
        )}

        {/* ── MODE 2: Engångsjustering (Självfinansierande) ────────────────── */}
        {mode === "onetime" && (
          <div className="space-y-4">
            <p className="text-xs text-[var(--color-text-secondary)]">
              Följande justeringar återställer portföljen självfinansierande. Småjusteringar under 1 000 kr ignoreras automatiskt för att spara courtage.
            </p>

            {plan.one_time_rebalance_orders.length > 0 ? (
              <div className="divide-y divide-[var(--color-border)] rounded-xl border border-[var(--color-border)] overflow-hidden bg-[var(--color-bg-elevated)]">
                {plan.one_time_rebalance_orders.map((ord, i) => {
                  const isSell = ord.action === "SÄLJ";
                  return (
                    <div key={i} className="p-3.5 flex items-center justify-between gap-3 text-xs">
                      <div className="flex items-center gap-2.5">
                        <span className={cn(
                          "px-2 py-0.5 rounded text-[10px] font-bold",
                          isSell
                            ? "bg-rose-500/20 text-rose-600 dark:text-rose-400"
                            : "bg-emerald-500/20 text-emerald-600 dark:text-emerald-400"
                        )}>
                          {ord.action}
                        </span>
                        <div>
                          <div className="font-semibold text-[var(--color-text-primary)]">
                            {ord.name} {ord.shares ? `(${ord.shares} st)` : ""}
                          </div>
                          <div className="text-[11px] text-[var(--color-text-muted)]">{ord.reason}</div>
                        </div>
                      </div>
                      <div className={cn(
                        "font-mono font-bold text-sm",
                        isSell ? "text-rose-500" : "text-emerald-500"
                      )}>
                        {isSell ? "-" : "+"}{formatPrice(ord.amount_sek)}
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-xs text-emerald-600 dark:text-emerald-400 flex items-center gap-2">
                <CheckCircle2 size={16} />
                <span>Inga engångsjusteringar krävs — portföljen ligger redan nära din målbalans.</span>
              </div>
            )}
          </div>
        )}
      </div>

      {/* ── 3. Risk & Sektorskydd Före vs Efter ──────────────────────────── */}
      <div className="rounded-2xl border p-6 bg-[var(--color-bg-surface)] border-[var(--color-border)] space-y-4">
        <h3 className="text-sm font-semibold text-[var(--color-text-primary)] flex items-center gap-2">
          <ShieldCheck size={16} className="text-[var(--color-accent)]" />
          Förväntad Riskeffekt efter Rebalansering
        </h3>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div className="p-3.5 rounded-xl border border-[var(--color-border)] bg-[var(--color-bg-elevated)]">
            <div className="text-[10px] text-[var(--color-text-muted)] mb-1">Max Sektorkoncentration</div>
            <div className="flex items-center gap-2 text-sm font-mono font-bold">
              <span className="text-amber-500">{plan.risk_impact.max_sector_before_pct}%</span>
              <ArrowRight size={12} className="text-[var(--color-text-muted)]" />
              <span className="text-emerald-500">{plan.risk_impact.max_sector_after_pct}%</span>
            </div>
          </div>

          <div className="p-3.5 rounded-xl border border-[var(--color-border)] bg-[var(--color-bg-elevated)]">
            <div className="text-[10px] text-[var(--color-text-muted)] mb-1">Portföljvolatilitet</div>
            <div className="flex items-center gap-2 text-sm font-mono font-bold">
              <span className="text-[var(--color-text-muted)]">{plan.risk_impact.estimated_volatility_before_pct}%</span>
              <ArrowRight size={12} className="text-[var(--color-text-muted)]" />
              <span className="text-emerald-500">{plan.risk_impact.estimated_volatility_after_pct}%</span>
            </div>
          </div>

          <div className="p-3.5 rounded-xl border border-[var(--color-border)] bg-[var(--color-bg-elevated)]">
            <div className="text-[10px] text-[var(--color-text-muted)] mb-1">Estimerad Max Drawdown</div>
            <div className="flex items-center gap-2 text-sm font-mono font-bold">
              <span className="text-rose-500">{plan.risk_impact.estimated_max_drawdown_before_pct}%</span>
              <ArrowRight size={12} className="text-[var(--color-text-muted)]" />
              <span className="text-emerald-500">{plan.risk_impact.estimated_max_drawdown_after_pct}%</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
