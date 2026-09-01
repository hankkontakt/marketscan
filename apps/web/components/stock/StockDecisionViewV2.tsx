'use client';

import React from 'react';
import { StockDecisionV2 } from '@/lib/types/decision_v2';
import {
  THESIS_BAND_CONFIG,
  SETUP_STATE_CONFIG,
  RISK_STATE_CONFIG,
  DATA_GRADE_CONFIG,
} from '@/components/screener-v2/DecisionBadges';

interface StockDecisionViewV2Props {
  decision: StockDecisionV2;
}

const FACTOR_NAMES_SV: Record<string, string> = {
  quality: 'Kvalitet & Lönsamhet',
  growth: 'Tillväxtkvalitet',
  valuation: 'Värdering & Multiplar',
  momentum: 'Momentum & Relativ Styrka',
  revisions: 'Estimatrevideringar',
  capital_alloc: 'Kapitalallokering & Utdelning',
  catalysts: 'Händelseutfall & Rapporter',
};

const FACTOR_WEIGHTS_DISPLAY: Record<string, string> = {
  quality: '25%',
  growth: '20%',
  valuation: '20%',
  momentum: '15%',
  revisions: '10%',
  capital_alloc: '5%',
  catalysts: '5%',
};

export const StockDecisionViewV2: React.FC<StockDecisionViewV2Props> = ({ decision }) => {
  const thesisConfig = THESIS_BAND_CONFIG[decision.master_rank.band] || THESIS_BAND_CONFIG.MIXED;
  const setupConfig = SETUP_STATE_CONFIG[decision.setup.state] || SETUP_STATE_CONFIG.NEUTRAL;
  const riskConfig = RISK_STATE_CONFIG[decision.risk.state] || RISK_STATE_CONFIG.MEDIUM;
  const dataGradeConfig = DATA_GRADE_CONFIG[decision.data_grade.grade] || DATA_GRADE_CONFIG.C;

  return (
    <div className="w-full space-y-6">
      {/* 1. Top Unified Decision Card */}
      <div className="rounded-2xl border border-zinc-200/80 dark:border-zinc-800/80 bg-white dark:bg-zinc-950 p-6 shadow-sm">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
          {/* Company & Price */}
          <div className="space-y-1">
            <div className="flex items-center space-x-3">
              <h1 className="text-2xl font-bold tracking-tight text-zinc-900 dark:text-zinc-50">
                {decision.ticker}
              </h1>
              <span className="text-xs px-2 py-0.5 rounded-full bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-300 font-medium">
                {decision.country}
              </span>
              <span className="text-xs px-2 py-0.5 rounded-full bg-zinc-100 dark:bg-zinc-800 text-zinc-500 capitalize">
                {decision.segment.replace('_', ' ')}
              </span>
            </div>
            <p className="text-sm text-zinc-500">{decision.name}</p>
            <div className="flex items-baseline space-x-2 pt-1 font-mono">
              <span className="text-xl font-bold text-zinc-900 dark:text-zinc-100">
                {decision.price.value.toFixed(2)} {decision.price.currency}
              </span>
              <span
                className={`text-sm font-semibold ${
                  decision.price.change_pct >= 0 ? 'text-emerald-600' : 'text-rose-600'
                }`}
              >
                {decision.price.change_pct >= 0 ? '+' : ''}
                {(decision.price.change_pct * 100).toFixed(2)}%
              </span>
            </div>
          </div>

          {/* Decision Verdict Badges */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {/* MasterRank */}
            <div className="p-3 rounded-xl bg-zinc-50 dark:bg-zinc-900/60 border border-zinc-100 dark:border-zinc-800 flex flex-col items-start justify-center">
              <span className="text-[11px] uppercase tracking-wider text-zinc-400 font-medium">
                MasterRank
              </span>
              <div className="flex items-baseline space-x-1.5 mt-0.5">
                <span className="text-2xl font-bold font-mono text-zinc-900 dark:text-zinc-50">
                  {decision.master_rank.score.toFixed(0)}
                </span>
                <span className="text-xs text-zinc-400">/100</span>
              </div>
              <span
                className={`mt-1.5 px-2 py-0.5 rounded-md text-[11px] font-semibold border ${thesisConfig.bg} ${thesisConfig.text} ${thesisConfig.border}`}
              >
                {thesisConfig.label}
              </span>
            </div>

            {/* Setup */}
            <div className="p-3 rounded-xl bg-zinc-50 dark:bg-zinc-900/60 border border-zinc-100 dark:border-zinc-800 flex flex-col items-start justify-center">
              <span className="text-[11px] uppercase tracking-wider text-zinc-400 font-medium">
                Timing & Setup
              </span>
              <span
                className={`mt-2 px-2 py-0.5 rounded-md text-xs font-semibold border ${setupConfig.bg} ${setupConfig.text} ${setupConfig.border}`}
              >
                {setupConfig.label}
              </span>
              <span className="text-[10px] text-zinc-400 mt-1 truncate max-w-[110px]">
                {decision.setup.reason_codes[0]?.replace(/_/g, ' ') || 'Normal'}
              </span>
            </div>

            {/* Risk */}
            <div className="p-3 rounded-xl bg-zinc-50 dark:bg-zinc-900/60 border border-zinc-100 dark:border-zinc-800 flex flex-col items-start justify-center">
              <span className="text-[11px] uppercase tracking-wider text-zinc-400 font-medium">
                Riskprofil
              </span>
              <span
                className={`mt-2 px-2 py-0.5 rounded-md text-xs font-semibold border ${riskConfig.bg} ${riskConfig.text} ${riskConfig.border}`}
              >
                {riskConfig.label}
              </span>
              <span className="text-[10px] text-zinc-400 mt-1 truncate max-w-[110px]">
                {decision.risk.dominant_risk.replace(/_/g, ' ')}
              </span>
            </div>

            {/* Data Grade */}
            <div className="p-3 rounded-xl bg-zinc-50 dark:bg-zinc-900/60 border border-zinc-100 dark:border-zinc-800 flex flex-col items-start justify-center">
              <span className="text-[11px] uppercase tracking-wider text-zinc-400 font-medium">
                Datakvalitet
              </span>
              <div className="flex items-center space-x-1.5 mt-1.5">
                <span
                  className={`w-6 h-6 flex items-center justify-center rounded text-sm font-bold ${dataGradeConfig.bg} ${dataGradeConfig.text}`}
                >
                  {decision.data_grade.grade}
                </span>
                <span className="text-xs text-zinc-500 font-mono">
                  {(decision.data_grade.weighted_coverage * 100).toFixed(0)}% täckning
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Warnings Banner if any */}
        {decision.warnings.length > 0 && (
          <div className="mt-4 p-3 rounded-lg bg-amber-500/10 border border-amber-500/30 text-xs text-amber-800 dark:text-amber-200">
            {decision.warnings.join(' • ')}
          </div>
        )}
      </div>

      {/* 2. Drivers Summary (Varför & Varför inte) */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Positiva Drivare */}
        <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 dark:bg-emerald-950/20 p-5">
          <h3 className="text-sm font-semibold text-emerald-800 dark:text-emerald-300 flex items-center">
            <span className="mr-1.5">✦</span> Positiva tesdrivare
          </h3>
          <div className="mt-3 space-y-2">
            {decision.positive_drivers.length === 0 ? (
              <p className="text-xs text-zinc-400">Inga starka positiva avvikelser från baslinjen.</p>
            ) : (
              decision.positive_drivers.map((d) => (
                <div
                  key={d.factor_name}
                  className="flex items-center justify-between text-xs py-1 border-b border-emerald-500/10 last:border-0"
                >
                  <span className="font-medium text-zinc-800 dark:text-zinc-200">
                    {d.label_sv}
                  </span>
                  <div className="flex items-center space-x-2 font-mono">
                    <span className="text-emerald-600 dark:text-emerald-400 font-semibold">
                      +{d.contribution.toFixed(1)}p
                    </span>
                    <span className="text-[10px] text-zinc-400">
                      ({(d.reliability * 100).toFixed(0)}% rel)
                    </span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Negativa Drivare */}
        <div className="rounded-xl border border-rose-500/20 bg-rose-500/5 dark:bg-rose-950/20 p-5">
          <h3 className="text-sm font-semibold text-rose-800 dark:text-rose-300 flex items-center">
            <span className="mr-1.5">⚠</span> Risker & negativa motvindar
          </h3>
          <div className="mt-3 space-y-2">
            {decision.negative_drivers.length === 0 ? (
              <p className="text-xs text-zinc-400">Inga väsentliga negativa avvikelser.</p>
            ) : (
              decision.negative_drivers.map((d) => (
                <div
                  key={d.factor_name}
                  className="flex items-center justify-between text-xs py-1 border-b border-rose-500/10 last:border-0"
                >
                  <span className="font-medium text-zinc-800 dark:text-zinc-200">
                    {d.label_sv}
                  </span>
                  <div className="flex items-center space-x-2 font-mono">
                    <span className="text-rose-600 dark:text-rose-400 font-semibold">
                      {d.contribution.toFixed(1)}p
                    </span>
                    <span className="text-[10px] text-zinc-400">
                      ({(d.reliability * 100).toFixed(0)}% rel)
                    </span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* 3. 7 Structural Factor Breakdown Grid */}
      <div className="rounded-xl border border-zinc-200/80 dark:border-zinc-800/80 bg-white dark:bg-zinc-950 p-5 shadow-sm">
        <h3 className="text-sm font-bold text-zinc-900 dark:text-zinc-100 mb-4">
          Faktormodell v2 (7 strukturella prioriteter)
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {Object.entries(FACTOR_NAMES_SV).map(([key, label]) => {
            const rawScore = decision.factor_scores[key];
            const rel = decision.factor_reliabilities[key] || 0.0;
            const weightDisplay = FACTOR_WEIGHTS_DISPLAY[key] || '0%';

            return (
              <div
                key={key}
                className="p-3.5 rounded-xl border border-zinc-100 dark:border-zinc-800 bg-zinc-50/50 dark:bg-zinc-900/40 flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-zinc-800 dark:text-zinc-200">
                      {label}
                    </span>
                    <span className="text-[10px] font-mono text-zinc-400">{weightDisplay}</span>
                  </div>
                  <div className="mt-2 flex items-baseline space-x-1.5 font-mono">
                    <span className="text-xl font-bold text-zinc-900 dark:text-zinc-100">
                      {rawScore !== null && rawScore !== undefined
                        ? rawScore.toFixed(0)
                        : '—'}
                    </span>
                    <span className="text-xs text-zinc-400">/100</span>
                  </div>
                </div>

                <div className="mt-3 pt-2 border-t border-zinc-100 dark:border-zinc-800 flex items-center justify-between text-[11px] text-zinc-500">
                  <span>Reliabilitet</span>
                  <span className="font-mono font-medium">{(rel * 100).toFixed(0)}%</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
