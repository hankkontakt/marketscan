"use client";

import Link from "next/link";
import { useRiskAnalytics } from "@/hooks/usePortfolio";
import { useRiskProfile } from "@/hooks/useRiskProfile";
import { InfoTooltip } from "@/components/ui/InfoTooltip";

const PROFILE_LABELS: Record<string, string> = {
  trygg: "Trygg", balanserad: "Balanserad", tillvaxt: "Tillväxt",
  aggressiv: "Aggressiv", maxrisk: "Maxrisk",
};

/**
 * RiskGauge — portföljens årsvolatilitet vs din målvolatilitet (från riskprofilen).
 * Grön om inom mål, gul om över. Saknas data → uppmaning att göra risktestet.
 */
export function RiskGauge() {
  const { data: risk } = useRiskAnalytics();
  const { data: profile } = useRiskProfile();

  const currentVol = risk?.volatility_ann ?? null;          // 0..1 (årlig)
  const targetVol = profile?.target_volatility ?? null;     // 0..1
  const profileLabel = profile ? (PROFILE_LABELS[profile.profile] ?? profile.profile) : null;

  const hasData = currentVol != null && targetVol != null;
  const overTarget = hasData && currentVol > targetVol;
  const barColor = !hasData ? "var(--color-text-muted)"
    : overTarget ? "var(--color-warn)" : "var(--color-up)";

  // Skala 0–40 % årsvol
  const MAX = 0.40;
  const curPct = hasData ? Math.min(100, (currentVol! / MAX) * 100) : 0;
  const tgtPct = targetVol != null ? Math.min(100, (targetVol / MAX) * 100) : 0;

  return (
    <div className="rounded-xl border bg-[var(--color-bg-surface)] border-[var(--color-border)] p-4">
      <div className="flex items-center gap-1.5 mb-3">
        <span className="text-[11px] text-[var(--color-text-muted)] font-medium uppercase tracking-wide">
          Risknivå
        </span>
        <InfoTooltip text="Din portföljs årliga volatilitet jämfört med målvolatiliteten för din riskprofil. Över målet = mer svängig än din profil avser." side="top" />
      </div>

      {!hasData ? (
        <div className="py-2">
          <p className="text-sm text-[var(--color-text-secondary)]">
            {currentVol == null ? "Lägg till innehav för att mäta din risk." : "Sätt en riskprofil för att jämföra."}
          </p>
          <Link href="/installningar" className="text-xs text-[var(--color-accent)] hover:underline mt-1 inline-block">
            Gör risktestet →
          </Link>
        </div>
      ) : (
        <>
          <div className="flex items-end justify-between mb-1">
            <span className="text-xl font-bold font-mono tabular" style={{ color: barColor }}>
              {(currentVol! * 100).toFixed(0)}%
            </span>
            <span className="text-xs text-[var(--color-text-muted)]">
              mål {(targetVol! * 100).toFixed(0)}% · {profileLabel}
            </span>
          </div>
          <div className="relative h-2 rounded-full overflow-hidden bg-[var(--color-bg-elevated)]">
            <div className="h-full rounded-full transition-all" style={{ width: `${curPct}%`, background: barColor }} />
            {/* Målmarkör */}
            <div className="absolute top-0 bottom-0 w-0.5 bg-[var(--color-text-primary)]" style={{ left: `${tgtPct}%` }} />
          </div>
          <p className="text-[11px] text-[var(--color-text-muted)] mt-1.5">
            {overTarget ? "Över din målnivå — överväg att minska svängiga innehav." : "Inom din målnivå."}
          </p>
        </>
      )}
    </div>
  );
}
