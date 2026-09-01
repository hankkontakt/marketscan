'use client';

import React from 'react';
import Link from 'next/link';
import { DecisionRowV2 } from '@/lib/types/decision_v2';
import {
  THESIS_BAND_CONFIG,
  SETUP_STATE_CONFIG,
  RISK_STATE_CONFIG,
  DATA_GRADE_CONFIG,
} from './DecisionBadges';

interface DecisionTableV2Props {
  rows: DecisionRowV2[];
  isLoading?: boolean;
}

export const DecisionTableV2: React.FC<DecisionTableV2Props> = ({ rows, isLoading }) => {
  if (isLoading) {
    return (
      <div className="w-full py-16 text-center text-zinc-500">
        <div className="inline-block h-8 w-8 animate-spin rounded-full border-2 border-emerald-500 border-t-transparent" />
        <p className="mt-3 text-sm">Laddar beslutstabell...</p>
      </div>
    );
  }

  if (!rows || rows.length === 0) {
    return (
      <div className="w-full py-16 text-center text-zinc-500 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-zinc-50/50 dark:bg-zinc-900/50">
        <p className="text-sm font-medium">Inga bolag matchade dina filterkriterier.</p>
        <p className="text-xs text-zinc-400 mt-1">Justera filtren ovan för att se fler resultat.</p>
      </div>
    );
  }

  return (
    <div className="w-full overflow-x-auto rounded-xl border border-zinc-200/80 dark:border-zinc-800/80 bg-white dark:bg-zinc-950 shadow-sm">
      <table className="w-full text-left text-sm border-collapse">
        <thead>
          <tr className="border-b border-zinc-200 dark:border-zinc-800 bg-zinc-50/75 dark:bg-zinc-900/75 text-xs font-semibold text-zinc-500 uppercase tracking-wider">
            <th className="py-3.5 px-4">Instrument</th>
            <th className="py-3.5 px-4">MasterRank & Tes</th>
            <th className="py-3.5 px-4">Setup (Timing)</th>
            <th className="py-3.5 px-4">Risk & Kvalitet</th>
            <th className="py-3.5 px-4">Främsta Drivare</th>
            <th className="py-3.5 px-4 text-right">Kurs</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-zinc-100 dark:divide-zinc-900 font-sans">
          {rows.map((row) => {
            const thesisConfig = THESIS_BAND_CONFIG[row.master_rank.band] || THESIS_BAND_CONFIG.MIXED;
            const setupConfig = SETUP_STATE_CONFIG[row.setup.state] || SETUP_STATE_CONFIG.NEUTRAL;
            const riskConfig = RISK_STATE_CONFIG[row.risk.state] || RISK_STATE_CONFIG.MEDIUM;
            const dataGradeConfig = DATA_GRADE_CONFIG[row.data_grade.grade] || DATA_GRADE_CONFIG.C;

            return (
              <tr
                key={row.listing_id || row.ticker}
                className="hover:bg-zinc-50/80 dark:hover:bg-zinc-900/50 transition-colors cursor-pointer group"
              >
                {/* 1. Instrument */}
                <td className="py-3.5 px-4">
                  <Link href={`/stocks/${encodeURIComponent(row.ticker)}`} className="block">
                    <div className="flex items-center space-x-2">
                      <span className="font-semibold text-zinc-900 dark:text-zinc-100 group-hover:text-emerald-600 dark:group-hover:text-emerald-400 transition-colors">
                        {row.ticker}
                      </span>
                      <span className="text-xs px-1.5 py-0.5 rounded bg-zinc-100 dark:bg-zinc-800 text-zinc-500">
                        {row.country}
                      </span>
                    </div>
                    <div className="text-xs text-zinc-500 truncate max-w-[180px] mt-0.5">
                      {row.name}
                    </div>
                  </Link>
                </td>

                {/* 2. MasterRank & Thesis */}
                <td className="py-3.5 px-4">
                  <div className="flex items-center space-x-2.5">
                    <div className="w-10 text-right font-mono font-bold text-zinc-900 dark:text-zinc-100">
                      {row.master_rank.score.toFixed(0)}
                    </div>
                    <div className="flex flex-col">
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${thesisConfig.bg} ${thesisConfig.text} ${thesisConfig.border}`}
                      >
                        {thesisConfig.label}
                      </span>
                      <span className="text-[10px] text-zinc-400 mt-0.5">
                        Top {100 - row.master_rank.segment_percentile}% i segment
                      </span>
                    </div>
                  </div>
                </td>

                {/* 3. Setup (Timing) */}
                <td className="py-3.5 px-4">
                  <div className="flex flex-col items-start">
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium border ${setupConfig.bg} ${setupConfig.text} ${setupConfig.border}`}
                    >
                      {setupConfig.label}
                    </span>
                    {row.setup.reason_codes.length > 0 && (
                      <span className="text-[10px] text-zinc-400 mt-0.5">
                        {row.setup.reason_codes[0].replace(/_/g, ' ').toLowerCase()}
                      </span>
                    )}
                  </div>
                </td>

                {/* 4. Risk & Data Grade */}
                <td className="py-3.5 px-4">
                  <div className="flex items-center space-x-2">
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium border ${riskConfig.bg} ${riskConfig.text} ${riskConfig.border}`}
                    >
                      {riskConfig.label}
                    </span>
                    <span
                      className={`inline-flex items-center justify-center w-5 h-5 rounded text-xs font-bold ${dataGradeConfig.bg} ${dataGradeConfig.text}`}
                      title={`Datakvalitet Grade ${row.data_grade.grade} (${(row.data_grade.weighted_coverage * 100).toFixed(0)}% täckning)`}
                    >
                      {dataGradeConfig.label}
                    </span>
                  </div>
                </td>

                {/* 5. Främsta Drivare */}
                <td className="py-3.5 px-4 max-w-xs">
                  <div className="flex flex-wrap gap-1">
                    {row.positive_drivers.slice(0, 2).map((d) => (
                      <span
                        key={d.factor_name}
                        className="text-[11px] px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 font-medium"
                      >
                        +{d.label_sv}
                      </span>
                    ))}
                    {row.negative_drivers.slice(0, 1).map((d) => (
                      <span
                        key={d.factor_name}
                        className="text-[11px] px-1.5 py-0.5 rounded bg-rose-500/10 text-rose-700 dark:text-rose-300 font-medium"
                      >
                        -{d.label_sv}
                      </span>
                    ))}
                  </div>
                </td>

                {/* 6. Price */}
                <td className="py-3.5 px-4 text-right">
                  <div className="font-mono font-medium text-zinc-900 dark:text-zinc-100">
                    {row.price.value.toFixed(2)} {row.price.currency}
                  </div>
                  <div
                    className={`text-xs font-mono font-medium ${
                      row.price.change_pct >= 0 ? 'text-emerald-600' : 'text-rose-600'
                    }`}
                  >
                    {row.price.change_pct >= 0 ? '+' : ''}
                    {(row.price.change_pct * 100).toFixed(2)}%
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};
