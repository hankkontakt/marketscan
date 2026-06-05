"use client";

import { useState, useCallback } from "react";
import { Search, Sparkles, X } from "lucide-react";
import { useScreener, useScanMeta } from "@/hooks/useScreener";
import { SegmentToggle } from "@/components/screener/SegmentToggle";
import { FilterRail } from "@/components/screener/FilterRail";
import { ResultTable } from "@/components/screener/ResultTable";
import { api } from "@/lib/api";
import type { ScanParams } from "@/lib/api";

const DEFAULT_FILTERS: ScanParams = {
  segments: ["large_cap", "mid_cap"],
  score_min: 0,
  limit: 200,
};

export function ScreenerView() {
  const [filters, setFilters] = useState<ScanParams>(DEFAULT_FILTERS);
  const [nlQuery, setNlQuery] = useState("");
  const [nlParsing, setNlParsing] = useState(false);
  const [nlInterpreted, setNlInterpreted] = useState<string>("");

  const { data = [], isLoading } = useScreener(filters);
  const { data: meta } = useScanMeta();

  const updateFilters = useCallback((partial: Partial<ScanParams>) => {
    setFilters((f) => ({ ...f, ...partial }));
    setNlInterpreted("");
  }, []);

  async function runNlSearch() {
    if (!nlQuery.trim()) return;
    setNlParsing(true);
    try {
      const parsed = await api<Partial<ScanParams>>("/api/ai/parse-filter", {
        method: "POST",
        body: JSON.stringify({ query: nlQuery }),
      });
      if (Object.keys(parsed).length > 0) {
        setFilters({ ...DEFAULT_FILTERS, ...parsed });
        setNlInterpreted(
          Object.entries(parsed)
            .map(([k, v]) => `${k}: ${JSON.stringify(v)}`)
            .join(", "),
        );
      }
    } catch {
      // ignore
    } finally {
      setNlParsing(false);
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-xl font-semibold text-[var(--color-text-primary)]">Screener</h1>
          {meta && (
            <p className="text-xs mt-0.5 text-[var(--color-text-muted)]">
              {meta.total} aktier &middot; Senast uppdaterat {meta.scan_date}
            </p>
          )}
        </div>
      </div>

      {/* NL search */}
      <div className="rounded-xl p-4 space-y-3 border"
           style={{ background: "var(--color-bg-surface)", borderColor: "var(--color-border)" }}>
        <div className="flex items-center gap-1.5 text-xs font-medium"
             style={{ color: "var(--color-text-secondary)" }}>
          <Sparkles size={13} strokeWidth={1.5} />
          Naturlig sökning
        </div>
        <div className="flex gap-2">
          <div className="relative flex-1">
            <Search size={14} strokeWidth={1.5}
                    className="absolute left-3 top-1/2 -translate-y-1/2"
                    style={{ color: "var(--color-text-muted)" }} />
            <input
              value={nlQuery}
              onChange={(e) => setNlQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && runNlSearch()}
              placeholder={`Prova: "Undervärderade industribolag med hög utdelning" eller "Starkt köpläge bland teknikbolag"`}
              className="w-full h-9 pl-9 pr-3 rounded-lg text-xs border
                         bg-[var(--color-bg-elevated)] border-[var(--color-border)]
                         text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)]
                         focus:border-[var(--color-accent)] focus:outline-none"
            />
          </div>
          <button
            onClick={runNlSearch}
            disabled={nlParsing || !nlQuery.trim()}
            className="px-4 h-9 rounded-lg text-xs font-medium transition-colors
                       bg-[var(--color-accent)] text-white
                       hover:bg-[var(--color-accent-hover)]
                       disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {nlParsing ? "Tolkar..." : "Sök"}
          </button>
        </div>
        {nlInterpreted && (
          <div className="flex items-start gap-2 text-[11px] text-[var(--color-text-muted)]">
            <span>Tolkning: {nlInterpreted}</span>
            <button
              onClick={() => { setNlInterpreted(""); setFilters(DEFAULT_FILTERS); setNlQuery(""); }}
              className="ml-auto shrink-0 hover:text-[var(--color-down)]"
            >
              <X size={12} />
            </button>
          </div>
        )}
      </div>

      {/* Segment toggle */}
      <div className="rounded-xl p-4 border"
           style={{ background: "var(--color-bg-surface)", borderColor: "var(--color-border)" }}>
        <div className="text-xs font-medium mb-3 text-[var(--color-text-secondary)]">Segment</div>
        <SegmentToggle
          value={(filters.segments ?? ["large_cap", "mid_cap"]) as ("large_cap" | "mid_cap" | "small_cap" | "micro_cap")[]}
          onChange={(segments) => updateFilters({ segments })}
        />
      </div>

      {/* Filters */}
      <FilterRail
        filters={filters}
        onChange={updateFilters}
        onReset={() => { setFilters(DEFAULT_FILTERS); setNlInterpreted(""); setNlQuery(""); }}
      />

      {/* Results */}
      <ResultTable data={data} loading={isLoading} />
    </div>
  );
}
