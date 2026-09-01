"use client";

import React, { useCallback, useEffect, useState } from "react";
import { ApiError } from "@/lib/api";
import { v3Screener } from "@/lib/v3";
import type { DecisionProjectionV3 } from "@/lib/types/decision_v3";
import { DecisionTableV3 } from "./DecisionTableV3";

const FILTER_OPTIONS = {
  thesis_band: [
    { value: "", label: "Thesis: alla" },
    { value: "BULLISH", label: "Stark tes" },
    { value: "CONSTRUCTIVE", label: "Konstruktiv" },
    { value: "NEUTRAL", label: "Neutral" },
    { value: "AVOID", label: "Undvik" },
  ],
  setup_state: [
    { value: "", label: "Setup: alla" },
    { value: "READY", label: "Bekräftad" },
    { value: "WATCH", label: "Bevaka" },
    { value: "WAIT", label: "Vänta" },
    { value: "INSUFFICIENT", label: "Otillräcklig data" },
  ],
  risk_state: [
    { value: "", label: "Risk: alla" },
    { value: "NORMAL", label: "Låg" },
    { value: "ELEVATED", label: "Medel" },
    { value: "CRITICAL", label: "Kritisk" },
  ],
  data_grade: [
    { value: "", label: "Data: alla" },
    { value: "A", label: "A" },
    { value: "B", label: "B" },
    { value: "C", label: "C" },
    { value: "D", label: "D" },
  ],
  segment: [
    { value: "", label: "Segment: alla" },
    { value: "large_cap", label: "Large cap" },
    { value: "mid_cap", label: "Mid cap" },
    { value: "small_cap", label: "Small cap" },
    { value: "micro_cap", label: "Micro cap" },
  ],
} as const;

type FilterKey = keyof typeof FILTER_OPTIONS;

export const ScreenerViewV3: React.FC = () => {
  const [rows, setRows] = useState<DecisionProjectionV3[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [asOf, setAsOf] = useState<string | null>(null);
  const [snapshotId, setSnapshotId] = useState<string | null>(null);
  const [filters, setFilters] = useState<Record<FilterKey, string>>({
    thesis_band: "",
    setup_state: "",
    risk_state: "",
    data_grade: "",
    segment: "",
  });

  const load = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const params: Record<string, string> = {};
      for (const [key, value] of Object.entries(filters)) {
        if (value) params[key] = value;
      }
      const data = await v3Screener(params);
      setRows(data.rows ?? []);
      setAsOf(data.as_of ?? null);
      setSnapshotId(data.snapshot_id ?? null);
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        setError("Ingen publicerad besluts-snapshot finns ännu. Data publiceras av pipelinen.");
      } else if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Kunde inte hämta beslutssignaler.");
      }
      setRows([]);
    } finally {
      setIsLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    void load();
  }, [load]);

  const setFilter = (key: FilterKey, value: string) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
  };

  const reset = () => {
    setFilters({ thesis_band: "", setup_state: "", risk_state: "", data_grade: "", segment: "" });
  };

  return (
    <div className="w-full space-y-4 max-w-7xl mx-auto px-4 sm:px-6 py-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-zinc-900 dark:text-zinc-50">
            Screener — beslutssignaler
          </h1>
          <p className="text-xs text-zinc-500 mt-0.5">
            Thesis · Setup · Risk · Data — en kanonisk publicerad snapshot
          </p>
        </div>
        <div className="text-xs font-mono text-zinc-400 text-right">
          {asOf ? (
            <>
              <div>Snapshot {new Date(asOf).toLocaleString("sv-SE")}</div>
              <div className="truncate max-w-[220px]">{snapshotId}</div>
            </>
          ) : (
            <div>{rows.length} instrument</div>
          )}
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2" role="group" aria-label="Filter">
        {(Object.keys(FILTER_OPTIONS) as FilterKey[]).map((key) => (
          <select
            key={key}
            value={filters[key]}
            onChange={(event) => setFilter(key, event.target.value)}
            aria-label={FILTER_OPTIONS[key][0].label.replace(": alla", "")}
            className="text-xs rounded-md border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 px-2.5 py-1.5 text-zinc-700 dark:text-zinc-300 focus:outline-none focus:ring-2 focus:ring-emerald-500/40"
          >
            {FILTER_OPTIONS[key].map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        ))}
        <button
          type="button"
          onClick={reset}
          className="text-xs px-2.5 py-1.5 rounded-md border border-zinc-200 dark:border-zinc-800 text-zinc-500 hover:text-zinc-700 dark:hover:text-zinc-300 transition-colors"
        >
          Återställ
        </button>
        <button
          type="button"
          onClick={() => void load()}
          className="text-xs px-2.5 py-1.5 rounded-md border border-zinc-200 dark:border-zinc-800 text-zinc-500 hover:text-zinc-700 dark:hover:text-zinc-300 transition-colors"
        >
          Uppdatera
        </button>
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