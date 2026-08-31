"use client";

import { useState } from "react";
import { ShieldCheck, ShieldAlert, AlertTriangle, CheckCircle2, XCircle, ChevronDown, ChevronUp, Loader2, Sparkles } from "lucide-react";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

interface ForensicAuditData {
  ticker: string;
  company_name: string;
  traffic_light: "GRÖN" | "GUL" | "RÖD" | string;
  audit_score: number;
  dilution_emission_risk: string;
  cash_runway_months?: number | null;
  capitalized_rd_pct_of_ebit?: number | null;
  real_ebit_adjusted_msek?: number | null;
  covenant_and_debt_risks: string[];
  accounting_red_flags: string[];
  positive_qualities: string[];
  verdict_summary_sv: string;
  cached_date: string;
}

interface Props {
  ticker: string;
  companyName?: string;
}

export function ForensicAuditCard({ ticker, companyName }: Props) {
  const [data, setData] = useState<ForensicAuditData | null>(null);
  const [loading, setLoading] = useState(false);
  const [showDetails, setShowDetails] = useState(false);

  async function handleRunAudit() {
    setLoading(true);
    try {
      const res = await api<ForensicAuditData>(`/api/ai/forensic-audit/${ticker}`, {
        method: "POST",
        body: JSON.stringify({ company_name: companyName, period_label: "LTM" }),
      });
      setData(res);
      toast.success("Forensisk delårs-audit slutförd!");
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Kunde inte köra forensisk audit");
    } finally {
      setLoading(false);
    }
  }

  const isGreen = data?.traffic_light === "GRÖN";
  const isRed = data?.traffic_light === "RÖD";

  return (
    <div className="rounded-2xl border p-5 bg-[var(--color-bg-surface)] border-[var(--color-border)] space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-2.5">
          <div className={cn(
            "w-8 h-8 rounded-lg flex items-center justify-center",
            data ? (isGreen ? "bg-emerald-500/10 text-emerald-500" : isRed ? "bg-rose-500/10 text-rose-500" : "bg-amber-500/10 text-amber-500")
                 : "bg-[var(--color-accent-soft)] text-[var(--color-accent)]"
          )}>
            {data ? (isGreen ? <ShieldCheck size={18} /> : isRed ? <ShieldAlert size={18} /> : <AlertTriangle size={18} />)
                  : <Sparkles size={16} />}
          </div>
          <div>
            <h3 className="text-sm font-semibold text-[var(--color-text-primary)]">
              Forensisk Delårs-Audit
            </h3>
            <p className="text-[11px] text-[var(--color-text-muted)]">
              Granskar fotnoter, aktiverad FoU, kassarunway och emissionsrisk
            </p>
          </div>
        </div>

        {!data && (
          <button
            onClick={handleRunAudit}
            disabled={loading}
            className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl text-xs font-medium bg-[var(--color-accent)] text-white hover:opacity-90 transition-opacity disabled:opacity-50 shadow-sm"
          >
            {loading ? <Loader2 size={13} className="animate-spin" /> : <Sparkles size={13} />}
            {loading ? "Granskar rapport..." : "Kör Delårs-Audit"}
          </button>
        )}
      </div>

      {/* Audit Result Display */}
      {data && (
        <div className="space-y-4 pt-1">
          {/* Top summary row */}
          <div className="flex items-center justify-between p-3 rounded-xl bg-[var(--color-bg-elevated)] border border-[var(--color-border)] flex-wrap gap-2">
            <div className="flex items-center gap-2">
              <span className={cn(
                "px-2.5 py-1 rounded-md text-xs font-bold uppercase tracking-wide",
                isGreen ? "bg-emerald-500/20 text-emerald-600 dark:text-emerald-400" :
                isRed ? "bg-rose-500/20 text-rose-600 dark:text-rose-400" :
                "bg-amber-500/20 text-amber-600 dark:text-amber-400"
              )}>
                {data.traffic_light} RISK
              </span>
              <span className="text-xs text-[var(--color-text-secondary)]">
                Emissionsrisk: <strong className="text-[var(--color-text-primary)]">{data.dilution_emission_risk}</strong>
              </span>
            </div>

            <div className="text-right">
              <span className="text-[11px] text-[var(--color-text-muted)]">Hälsopoäng: </span>
              <span className="font-mono font-bold text-sm text-[var(--color-text-primary)]">
                {data.audit_score}/100
              </span>
            </div>
          </div>

          {/* Key Metrics Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
            <div className="p-2.5 rounded-xl border border-[var(--color-border)] bg-[var(--color-bg-elevated)] text-center">
              <div className="text-[10px] text-[var(--color-text-muted)] mb-0.5">Kassarunway</div>
              <div className="font-mono font-semibold text-xs text-[var(--color-text-primary)]">
                {data.cash_runway_months ? `${data.cash_runway_months} mån` : "Trygg (>24m)"}
              </div>
            </div>

            <div className="p-2.5 rounded-xl border border-[var(--color-border)] bg-[var(--color-bg-elevated)] text-center">
              <div className="text-[10px] text-[var(--color-text-muted)] mb-0.5">Aktiverad FoU</div>
              <div className="font-mono font-semibold text-xs text-[var(--color-text-primary)]">
                {data.capitalized_rd_pct_of_ebit ? `${data.capitalized_rd_pct_of_ebit.toFixed(1)}% av EBIT` : "0% (Ingen FoU)"}
              </div>
            </div>

            <div className="p-2.5 rounded-xl border border-[var(--color-border)] bg-[var(--color-bg-elevated)] text-center">
              <div className="text-[10px] text-[var(--color-text-muted)] mb-0.5">Lånevillkor</div>
              <div className="font-mono font-semibold text-xs text-[var(--color-text-primary)]">
                {data.covenant_and_debt_risks.length > 0 ? `${data.covenant_and_debt_risks.length} varning` : "Inga brutna"}
              </div>
            </div>

            <div className="p-2.5 rounded-xl border border-[var(--color-border)] bg-[var(--color-bg-elevated)] text-center">
              <div className="text-[10px] text-[var(--color-text-muted)] mb-0.5">Reviderad</div>
              <div className="font-mono font-semibold text-xs text-[var(--color-text-primary)] truncate">
                {data.cached_date}
              </div>
            </div>
          </div>

          {/* Verdict text */}
          <div className="p-3.5 rounded-xl border border-[var(--color-border)] bg-[var(--color-bg-elevated)]">
            <p className="text-xs text-[var(--color-text-primary)] leading-relaxed">
              {data.verdict_summary_sv}
            </p>
          </div>

          {/* Toggle details */}
          {(data.accounting_red_flags.length > 0 || data.positive_qualities.length > 0) && (
            <div>
              <button
                onClick={() => setShowDetails(!showDetails)}
                className="flex items-center gap-1 text-xs text-[var(--color-accent)] hover:underline"
              >
                {showDetails ? (
                  <>Dölj detaljerad granskningslista <ChevronUp size={12} /></>
                ) : (
                  <>Visa detaljerad granskningslista ({data.accounting_red_flags.length + data.positive_qualities.length} punkter) <ChevronDown size={12} /></>
                )}
              </button>

              {showDetails && (
                <div className="mt-3 space-y-2 text-xs">
                  {data.accounting_red_flags.map((flag, i) => (
                    <div key={`flag-${i}`} className="flex items-start gap-2 p-2 rounded-lg bg-rose-500/5 text-rose-600 dark:text-rose-400 border border-rose-500/10">
                      <XCircle size={14} className="shrink-0 mt-0.5" />
                      <span>{flag}</span>
                    </div>
                  ))}
                  {data.positive_qualities.map((pos, i) => (
                    <div key={`pos-${i}`} className="flex items-start gap-2 p-2 rounded-lg bg-emerald-500/5 text-emerald-600 dark:text-emerald-400 border border-emerald-500/10">
                      <CheckCircle2 size={14} className="shrink-0 mt-0.5" />
                      <span>{pos}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
