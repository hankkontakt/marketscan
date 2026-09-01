'use client';

import React, { useState, useEffect } from 'react';
import { DecisionRowV2, ScreenerResponseV2 } from '@/lib/types/decision_v2';
import { FilterBarV2 } from './FilterBarV2';
import { DecisionTableV2 } from './DecisionTableV2';

export const ScreenerViewV2: React.FC = () => {
  const [rows, setRows] = useState<DecisionRowV2[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [segment, setSegment] = useState<string | null>(null);
  const [thesisBand, setThesisBand] = useState<string | null>(null);
  const [setupState, setSetupState] = useState<string | null>(null);
  const [riskState, setRiskState] = useState<string | null>(null);

  useEffect(() => {
    let isCancelled = false;
    const fetchDecisions = async () => {
      setIsLoading(true);
      try {
        const params = new URLSearchParams();
        if (segment) params.set('segment', segment);
        if (thesisBand) params.set('thesis_band', thesisBand);
        if (setupState) params.set('setup_state', setupState);
        if (riskState) params.set('risk_state', riskState);

        const res = await fetch(`/api/v2/decisions/screener?${params.toString()}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data: ScreenerResponseV2 = await res.json();
        if (!isCancelled) {
          setRows(data.rows || []);
        }
      } catch (err) {
        console.error('Failed to load screener v2 decisions:', err);
      } finally {
        if (!isCancelled) {
          setIsLoading(false);
        }
      }
    };

    fetchDecisions();
    return () => {
      isCancelled = true;
    };
  }, [segment, thesisBand, setupState, riskState]);

  const handleReset = () => {
    setSegment(null);
    setThesisBand(null);
    setSetupState(null);
    setRiskState(null);
  };

  return (
    <div className="w-full space-y-4 max-w-7xl mx-auto px-4 sm:px-6 py-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-zinc-900 dark:text-zinc-50">
            MarketScan Screener v2
          </h1>
          <p className="text-xs text-zinc-500 mt-0.5">
            Deterministiska beslutssignaler med fullständig faktorinsyn och likviditetskontroll
          </p>
        </div>
        <div className="text-xs font-mono text-zinc-400">
          {rows.length} instrument rankade
        </div>
      </div>

      <FilterBarV2
        segment={segment}
        setSegment={setSegment}
        thesisBand={thesisBand}
        setThesisBand={setThesisBand}
        setupState={setupState}
        setSetupState={setSetupState}
        riskState={riskState}
        setRiskState={setRiskState}
        onReset={handleReset}
      />

      <DecisionTableV2 rows={rows} isLoading={isLoading} />
    </div>
  );
};
