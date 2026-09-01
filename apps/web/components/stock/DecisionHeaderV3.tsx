"use client";

import React, { useEffect, useState } from "react";
import { ApiError } from "@/lib/api";
import { DECISIONS_V3_ENABLED, v3StockByTicker } from "@/lib/v3";
import type { DecisionProjectionV3 } from "@/lib/types/decision_v3";
import {
  THESIS_BAND_CONFIG,
  SETUP_STATE_CONFIG,
  RISK_STATE_CONFIG,
  DATA_GRADE_CONFIG,
  TRADABILITY_CONFIG,
  badgeFor,
  FALLBACK_THESIS,
  FALLBACK_SETUP,
  FALLBACK_RISK,
  FALLBACK_TRADABILITY,
} from "@/components/screener-v3/badges";

interface DecisionHeaderV3Props {
  ticker: string;
}

/**
 * Stock-page decision header (plan section 28): THESIS / SETUP / RISK / DATA
 * from the same published snapshot as the screener. Returns null when the V3
 * gate is off or no published decision exists — the V1 header remains the
 * fallback, so this never breaks the existing page.
 */
export const DecisionHeaderV3: React.FC<DecisionHeaderV3Props> = ({ ticker }) => {
  const [decision, setDecision] = useState<DecisionProjectionV3 | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    if (!DECISIONS_V3_ENABLED) return;
    let isCancelled = false;
    v3StockByTicker(ticker)
      .then((data) => {
        if (!isCancelled) setDecision(data);
      })
      .catch((err) => {
        // 404 (no published decision) and disabled routes degrade silently to V1.
        if (!(err instanceof ApiError && (err.status === 404 || err.status === 503))) {
          console.error("V3 decision header failed:", err);
        }
        if (!isCancelled) setFailed(true);
      });
    return () => {
      isCancelled = true;
    };
  }, [ticker]);

  if (!DECISIONS_V3_ENABLED || !decision || failed) return null;

  const thesis = badgeFor(THESIS_BAND_CONFIG, decision.thesis_band, FALLBACK_THESIS);
  const setup = badgeFor(SETUP_STATE_CONFIG, decision.setup_state, FALLBACK_SETUP);
  const risk = badgeFor(RISK_STATE_CONFIG, decision.risk_state, FALLBACK_RISK);
  const tradability = badgeFor(TRADABILITY_CONFIG, decision.tradability_state, FALLBACK_TRADABILITY);
  const dataGrade = DATA_GRADE_CONFIG[decision.data_grade] ?? { label: decision.data_grade, bg: "bg-zinc-500/15", text: "text-zinc-500" };

  return (
    <div className="px-6 py-3 border-b border-[var(--color-border)] bg-[var(--color-bg-surface)]">
      <div className="flex flex-wrap items-center gap-x-5 gap-y-2">
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-[var(--color-text-muted)]">Thesis</span>
          <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium border ${thesis.bg} ${thesis.text} ${thesis.border}`}>
            {thesis.label}
            {decision.master_rank_score != null && <span className="font-mono">{decision.master_rank_score.toFixed(0)}</span>}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-[var(--color-text-muted)]">Setup</span>
          <span className={`inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium border ${setup.bg} ${setup.text} ${setup.border}`}>
            {setup.label}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-[var(--color-text-muted)]">Risk</span>
          <span className={`inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium border ${risk.bg} ${risk.text} ${risk.border}`}>
            {risk.label}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-[var(--color-text-muted)]">Data</span>
          <span className={`inline-flex items-center justify-center w-5 h-5 rounded text-xs font-bold ${dataGrade.bg} ${dataGrade.text}`}>
            {dataGrade.label}
          </span>
          <span className="text-[10px] text-[var(--color-text-muted)]">
            {Math.round((decision.coverage ?? 0) * 100)}% täckning
          </span>
        </div>
        {decision.tradability_state !== "ACTIVE" && (
          <span className={`inline-flex items-center px-2 py-0.5 rounded-md text-[10px] font-medium border ${tradability.bg} ${tradability.text} ${tradability.border}`}>
            {tradability.label}
          </span>
        )}
        {decision.stale_critical_count > 0 && (
          <span className="text-[10px] text-[var(--color-warn)]">
            {decision.stale_critical_count} kritisk(a) datakälla(er) inaktuell(a)
          </span>
        )}
        <span className="ml-auto text-[10px] font-mono text-[var(--color-text-muted)]">
          Beslut {new Date(decision.published_at).toLocaleDateString("sv-SE")}
        </span>
      </div>
    </div>
  );
};