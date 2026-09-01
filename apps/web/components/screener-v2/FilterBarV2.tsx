'use client';

import React from 'react';

interface FilterBarV2Props {
  segment: string | null;
  setSegment: (seg: string | null) => void;
  thesisBand: string | null;
  setThesisBand: (band: string | null) => void;
  setupState: string | null;
  setSetupState: (state: string | null) => void;
  riskState: string | null;
  setRiskState: (risk: string | null) => void;
  onReset: () => void;
}

const SEGMENTS = [
  { id: null, label: 'Alla segment' },
  { id: 'large_cap', label: 'Large Cap' },
  { id: 'mid_cap', label: 'Mid Cap' },
  { id: 'small_cap', label: 'Small Cap' },
];

const THESIS_BANDS = [
  { id: null, label: 'Alla teser' },
  { id: 'EXCEPTIONAL', label: 'Exceptionell (85+)' },
  { id: 'STRONG', label: 'Stark (75-84)' },
  { id: 'POSITIVE', label: 'Positiv (65-74)' },
];

const SETUP_STATES = [
  { id: null, label: 'Alla setups' },
  { id: 'CONFIRMED', label: 'Bekräftad trend' },
  { id: 'PULLBACK', label: 'Kontrollerad rekyl' },
  { id: 'EXTENDED', label: 'Utsträckt' },
  { id: 'DAMAGED', label: 'Skadad prisbild' },
];

const RISK_STATES = [
  { id: null, label: 'Alla risker' },
  { id: 'LOW', label: 'Låg risk' },
  { id: 'MEDIUM', label: 'Måttlig' },
  { id: 'HIGH', label: 'Förhöjd' },
];

export const FilterBarV2: React.FC<FilterBarV2Props> = ({
  segment,
  setSegment,
  thesisBand,
  setThesisBand,
  setupState,
  setSetupState,
  riskState,
  setRiskState,
  onReset,
}) => {
  return (
    <div className="w-full space-y-3 p-4 rounded-xl border border-zinc-200/80 dark:border-zinc-800/80 bg-white dark:bg-zinc-950 shadow-sm">
      {/* Segment Tabs */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center space-x-1.5 p-1 rounded-lg bg-zinc-100 dark:bg-zinc-900 text-xs">
          {SEGMENTS.map((seg) => {
            const isActive = segment === seg.id;
            return (
              <button
                key={seg.label}
                onClick={() => setSegment(seg.id)}
                className={`px-3 py-1.5 rounded-md font-medium transition-colors ${
                  isActive
                    ? 'bg-white dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100 shadow-sm'
                    : 'text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-100'
                }`}
              >
                {seg.label}
              </button>
            );
          })}
        </div>

        <button
          onClick={onReset}
          className="text-xs text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200 underline font-medium"
        >
          Återställ filter
        </button>
      </div>

      {/* Filter Row 2: Thesis Band, Setup State, Risk State */}
      <div className="flex flex-wrap items-center gap-2 pt-1 border-t border-zinc-100 dark:border-zinc-900 text-xs">
        <span className="text-zinc-400 font-medium">Tes:</span>
        {THESIS_BANDS.map((tb) => {
          const isActive = thesisBand === tb.id;
          return (
            <button
              key={tb.label}
              onClick={() => setThesisBand(tb.id)}
              className={`px-2.5 py-1 rounded-full border transition-all ${
                isActive
                  ? 'bg-emerald-500/10 border-emerald-500/40 text-emerald-700 dark:text-emerald-300 font-semibold'
                  : 'border-zinc-200 dark:border-zinc-800 text-zinc-500 hover:border-zinc-300 dark:hover:border-zinc-700'
              }`}
            >
              {tb.label}
            </button>
          );
        })}

        <div className="h-4 w-px bg-zinc-200 dark:bg-zinc-800 mx-1 hidden sm:block" />

        <span className="text-zinc-400 font-medium">Setup:</span>
        {SETUP_STATES.map((ss) => {
          const isActive = setupState === ss.id;
          return (
            <button
              key={ss.label}
              onClick={() => setSetupState(ss.id)}
              className={`px-2.5 py-1 rounded-full border transition-all ${
                isActive
                  ? 'bg-indigo-500/10 border-indigo-500/40 text-indigo-700 dark:text-indigo-300 font-semibold'
                  : 'border-zinc-200 dark:border-zinc-800 text-zinc-500 hover:border-zinc-300 dark:hover:border-zinc-700'
              }`}
            >
              {ss.label}
            </button>
          );
        })}

        <div className="h-4 w-px bg-zinc-200 dark:bg-zinc-800 mx-1 hidden sm:block" />

        <span className="text-zinc-400 font-medium">Risk:</span>
        {RISK_STATES.map((rs) => {
          const isActive = riskState === rs.id;
          return (
            <button
              key={rs.label}
              onClick={() => setRiskState(rs.id)}
              className={`px-2.5 py-1 rounded-full border transition-all ${
                isActive
                  ? 'bg-blue-500/10 border-blue-500/40 text-blue-700 dark:text-blue-300 font-semibold'
                  : 'border-zinc-200 dark:border-zinc-800 text-zinc-500 hover:border-zinc-300 dark:hover:border-zinc-700'
              }`}
            >
              {rs.label}
            </button>
          );
        })}
      </div>
    </div>
  );
};
