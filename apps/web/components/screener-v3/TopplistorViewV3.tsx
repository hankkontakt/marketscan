"use client";

import React, { useCallback, useEffect, useState } from "react";
import { ApiError } from "@/lib/api";
import { v3Screener } from "@/lib/v3";
import type { DecisionProjectionV3 } from "@/lib/types/decision_v3";
import { DecisionTableV3 } from "@/components/screener-v3/DecisionTableV3";

/**
 * Topplistor v3 (plan section 27.2): the published decision universe ranked
 * by MasterRank thesis score — same snapshot, same semantics as the screener.
 */
export const TopplistorViewV3: React.FC = () => {
  const [rows, setRows] = useState<DecisionProjectionV3[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [asOf, setAsOf] = useState<string | null>(null);
  const [segment, setSegment] = useState("");

  const load = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await v3Screener(segment ? { segment } : {});
      setRows(data.rows ?? []);
      setAsOf(data.as_of ?? null);
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        setError("Ingen publicerad besluts-snapshot finns ännu.");
      } else if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Kunde inte hämta topplistorna.");
      }
      setRows([]);
    } finally {
      setIsLoading(false);
    }
  }, [segment]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <div className="w-full space-y-4 max-w-7xl mx-auto px-4 sm:px-6 py-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-zinc-900 dark:text-zinc-50">
            Topplistor
          </h1>
          <p className="text-xs text-zinc-500 mt-0.5">
            Publicerade beslut rankade efter tes — samma kanoniska snapshot som screenern
          </p>
        </div>
        <div className="text-xs font-mono text-zinc-400 text-right">
          {asOf ? `Snapshot ${new Date(asOf).toLocaleDateString("sv-SE")}` : `${rows.length} instrument`}
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2" role="group" aria-label="Segmentfilter">
        <select
          value={segment}
          onChange={(event) => setSegment(event.target.value)}
          aria-label="Segment"
          className="text-xs rounded-md border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 px-2.5 py-1.5 text-zinc-700 dark:text-zinc-300 focus:outline-none focus:ring-2 focus:ring-emerald-500/40"
        >
          <option value="">Segment: alla</option>
          <option value="large_cap">Large cap</option>
          <option value="mid_cap">Mid cap</option>
          <option value="small_cap">Small cap</option>
          <option value="micro_cap">Micro cap</option>
        </select>
      </div>

      {error && (
        <div className="w-full py-10 text-center text-sm text-amber-700 dark:text-amber-300 rounded-xl border border-amber-500/30 bg-amber-500/5">
          {error}
        </div>
      )}

      <DecisionTableV3 rows={rows} isLoading={isLoading} />
    </div>
  );
};