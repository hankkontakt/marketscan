"use client";

import React from "react";
import Link from "next/link";
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
} from "./badges";

interface DecisionTableV3Props {
  rows: DecisionProjectionV3[];
  isLoading?: boolean;
}

/**
 * V3 screener table (plan section 27.1): Aktie | Thesis | Setup | Risk | Data
 * | Kurs/Idag. Inactive listings render an explicit tradability state — never
 * a weak rating. No legacy buy language ("Köpläge") anywhere.
 */
export const DecisionTableV3: React.FC<DecisionTableV3Props> = ({ rows, isLoading }) => {
  if (isLoading) {
    return (
      <div className="w-full py-16 text-center text-zinc-500" role="status">
        <div className="inline-block h-8 w-8 animate-spin rounded-full border-2 border-emerald-500 border-t-transparent" />
        <p className="mt-3 text-sm">Laddar beslutstabell...</p>
      </div>
    );
  }

  if (!rows || rows.length === 0) {
    return (
      <div className="w-full py-16 text-center text-zinc-500 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-zinc-50/50 dark:bg-zinc-900/50">
        <p className="text-sm font-medium">Inga publicerade beslut matchade dina filter.</p>
        <p className="text-xs text-zinc-400 mt-1">
          Justera filtren ovan, eller vänta tills nästa snapshot är publicerad.
        </p>
      </div>
    );
  }

  return (
    <div className="w-full overflow-x-auto rounded-xl border border-zinc-200/80 dark:border-zinc-800/80 bg-white dark:bg-zinc-950 shadow-sm">
      <table className="w-full text-left text-sm border-collapse">
        <caption className="sr-only">Publicerade beslutssignaler: tes, setup, risk, datakvalitet och kurs</caption>
        <thead>
          <tr className="border-b border-zinc-200 dark:border-zinc-800 bg-zinc-50/75 dark:bg-zinc-900/75 text-xs font-semibold text-zinc-500 uppercase tracking-wider">
            <th scope="col" className="py-3.5 px-4">Aktie</th>
            <th scope="col" className="py-3.5 px-4">Thesis</th>
            <th scope="col" className="py-3.5 px-4">Setup</th>
            <th scope="col" className="py-3.5 px-4">Risk</th>
            <th scope="col" className="py-3.5 px-4">Data</th>
            <th scope="col" className="py-3.5 px-4 text-right">Kurs / Idag</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-zinc-100 dark:divide-zinc-900">
          {rows.map((row) => {
            const tradable = row.tradability_state === "ACTIVE";
            const thesis = badgeFor(THESIS_BAND_CONFIG, row.thesis_band, FALLBACK_THESIS);
            const setup = badgeFor(SETUP_STATE_CONFIG, row.setup_state, FALLBACK_SETUP);
            const risk = badgeFor(RISK_STATE_CONFIG, row.risk_state, FALLBACK_RISK);
            const tradability = badgeFor(TRADABILITY_CONFIG, row.tradability_state, FALLBACK_TRADABILITY);
            const dataGrade = DATA_GRADE_CONFIG[row.data_grade] ?? { label: row.data_grade, bg: "bg-zinc-500/15", text: "text-zinc-500" };
            const muted = !tradable || !row.is_actionable;

            return (
              <tr
                key={row.decision_id}
                className={`transition-colors group ${muted ? "opacity-60" : "hover:bg-zinc-50/80 dark:hover:bg-zinc-900/50 cursor-pointer"}`}
              >
                <td className="py-3.5 px-4">
                  <Link href={`/aktie/${encodeURIComponent(row.ticker)}`} className="block" tabIndex={muted ? -1 : undefined}>
                    <div className="flex items-center space-x-2">
                      <span className="font-semibold text-zinc-900 dark:text-zinc-100 group-hover:text-emerald-600 dark:group-hover:text-emerald-400 transition-colors">
                        {row.ticker}
                      </span>
                      {!tradable && (
                        <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium border ${tradability.bg} ${tradability.text} ${tradability.border}`}>
                          {tradability.label}
                        </span>
                      )}
                    </div>
                    <div className="text-xs text-zinc-500 truncate max-w-[200px] mt-0.5">
                      {row.name ?? row.mic}
                    </div>
                  </Link>
                </td>

                <td className="py-3.5 px-4">
                  <div className="flex items-center space-x-2.5">
                    {row.master_rank_score != null && (
                      <span className="w-10 text-right font-mono font-bold text-zinc-900 dark:text-zinc-100">
                        {row.master_rank_score.toFixed(0)}
                      </span>
                    )}
                    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${thesis.bg} ${thesis.text} ${thesis.border}`}>
                      {thesis.label}
                    </span>
                  </div>
                </td>

                <td className="py-3.5 px-4">
                  <span className={`inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium border ${setup.bg} ${setup.text} ${setup.border}`}>
                    {setup.label}
                  </span>
                </td>

                <td className="py-3.5 px-4">
                  <span className={`inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium border ${risk.bg} ${risk.text} ${risk.border}`}>
                    {risk.label}
                  </span>
                </td>

                <td className="py-3.5 px-4">
                  <div className="flex items-center space-x-1.5">
                    <span
                      className={`inline-flex items-center justify-center w-5 h-5 rounded text-xs font-bold ${dataGrade.bg} ${dataGrade.text}`}
                      title={`Datakvalitet ${row.data_grade} (${Math.round((row.coverage ?? 0) * 100)}% täckning)`}
                    >
                      {dataGrade.label}
                    </span>
                    <span className="text-[10px] text-zinc-400">
                      {Math.round((row.coverage ?? 0) * 100)}%
                    </span>
                  </div>
                </td>

                <td className="py-3.5 px-4 text-right">
                  {row.price != null ? (
                    <>
                      <div className="font-mono font-medium text-zinc-900 dark:text-zinc-100">
                        {row.price.toLocaleString("sv-SE", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}{" "}
                        {row.currency}
                      </div>
                      {row.change_pct != null && (
                        <div className={`text-xs font-mono font-medium ${row.change_pct >= 0 ? "text-emerald-600" : "text-rose-600"}`}>
                          {row.change_pct >= 0 ? "+" : ""}
                          {(row.change_pct * 100).toFixed(2)}%
                        </div>
                      )}
                    </>
                  ) : (
                    <span className="text-xs text-zinc-400">—</span>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};