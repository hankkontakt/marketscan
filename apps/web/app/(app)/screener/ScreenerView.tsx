"use client";

import { useState, useCallback, useMemo } from "react";
import { Search, X, Bookmark, BookmarkCheck } from "lucide-react";
import { useScreener, useScanMeta } from "@/hooks/useScreener";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { SegmentToggle } from "@/components/screener/SegmentToggle";
import { FilterRail } from "@/components/screener/FilterRail";
import { ResultTable } from "@/components/screener/ResultTable";
import { InfoTooltip } from "@/components/ui/InfoTooltip";
import { SCREENER_PRESETS } from "@/lib/labels";
import { api } from "@/lib/api";
import { toast } from "sonner";
import type { ScanParams } from "@/lib/api";

const DEFAULT_FILTERS: ScanParams = {
  segments: ["large_cap", "mid_cap"],
  score_min: 0,
  limit: 200,
};

interface SavedScreen { id: string; name: string; filter_json: Record<string, unknown>; }

export function ScreenerView() {
  const [filters, setFilters] = useState<ScanParams>(DEFAULT_FILTERS);
  const [nlQuery, setNlQuery] = useState("");
  const [nlParsing, setNlParsing] = useState(false);
  const [nlInterpreted, setNlInterpreted] = useState<string>("");
  const [saveName, setSaveName] = useState("");
  const [showSaveForm, setShowSaveForm] = useState(false);
  const qc = useQueryClient();

  const { data = [], isLoading } = useScreener(filters);
  const { data: meta } = useScanMeta();

  const buckets = useMemo(() => {
    const b = new Array(10).fill(0);
    (data || []).forEach((r) => {
      const s = r.score_total;
      if (s != null) {
        const idx = Math.min(Math.floor(s / 10), 9);
        b[idx]++;
      }
    });
    return b;
  }, [data]);
  const maxBucket = Math.max(...buckets, 1);

  const { data: savedScreens = [] } = useQuery<SavedScreen[]>({
    queryKey: ["screens"],
    queryFn: () => api<SavedScreen[]>("/api/screens"),
    staleTime: 60_000,
  });

  const saveScreen = useMutation({
    mutationFn: (name: string) =>
      api("/api/screens", { method: "POST", body: JSON.stringify({ name, filter_json: filters }) }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["screens"] });
      setSaveName("");
      setShowSaveForm(false);
      toast.success("Vy sparad");
    },
  });

  const deleteScreen = useMutation({
    mutationFn: (id: string) => api(`/api/screens/${id}`, { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["screens"] }),
  });

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
      <div className="flex items-start justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-xl font-semibold text-[var(--color-text-primary)]">Aktier</h1>
          {meta && (
            <p className="text-xs mt-0.5 text-[var(--color-text-muted)]">
              {meta.total} aktier &middot; Senast uppdaterat {meta.scan_date}
            </p>
          )}
        </div>

        {/* Saved screens */}
        <div className="flex items-center gap-2 flex-wrap">
          {savedScreens.map((s) => (
            <button
              key={s.id}
              onClick={() => { setFilters({ ...DEFAULT_FILTERS, ...(s.filter_json as ScanParams) }); }}
              className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs border transition-colors
                         border-[var(--color-border)] text-[var(--color-text-secondary)]
                         hover:border-[var(--color-accent)] hover:text-[var(--color-accent)]"
            >
              <BookmarkCheck size={11} strokeWidth={1.5} />
              {s.name}
            </button>
          ))}

          {showSaveForm ? (
            <div className="flex items-center gap-1.5">
              <input
                autoFocus
                value={saveName}
                onChange={(e) => setSaveName(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter" && saveName.trim()) saveScreen.mutate(saveName.trim()); if (e.key === "Escape") setShowSaveForm(false); }}
                placeholder="Namn på vy..."
                className="h-7 px-2 rounded-lg text-xs border bg-[var(--color-bg-elevated)]
                           border-[var(--color-accent)] text-[var(--color-text-primary)] focus:outline-none w-32"
              />
              <button
                onClick={() => saveName.trim() && saveScreen.mutate(saveName.trim())}
                className="text-xs px-2 h-7 rounded-lg bg-[var(--color-accent)] text-white"
              >
                Spara
              </button>
              <button onClick={() => setShowSaveForm(false)}
                      className="text-xs text-[var(--color-text-muted)] hover:text-[var(--color-down)]">
                <X size={12} />
              </button>
            </div>
          ) : (
            <button
              onClick={() => setShowSaveForm(true)}
              className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs border transition-colors
                         border-[var(--color-border)] text-[var(--color-text-muted)]
                         hover:border-[var(--color-border-strong)] hover:text-[var(--color-text-secondary)]"
            >
              <Bookmark size={11} strokeWidth={1.5} />
              Spara vy
            </button>
          )}
        </div>
      </div>

      {/* Fritextsökning */}
      <div className="flex items-center gap-2">
        <div className="relative flex-1">
          <Search size={14} strokeWidth={1.5}
                  className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)]" />
          <input
            value={nlQuery}
            onChange={(e) => setNlQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && runNlSearch()}
            placeholder='Sök med egna ord, t.ex. "Undervärderade industribolag med hög utdelning"'
            className="w-full h-10 pl-9 pr-3 rounded-xl text-sm border
                       border-[var(--color-border)] bg-[var(--color-bg-surface)]
                       text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)]
                       focus:border-[var(--color-accent)] focus:outline-none transition-colors"
          />
        </div>
        <InfoTooltip text="Sök på naturligt språk, t.ex. 'billiga svenska kvalitetsbolag'." side="bottom" />
        <button
          onClick={runNlSearch}
          disabled={nlParsing || !nlQuery.trim()}
          className="px-5 h-10 rounded-xl text-sm font-medium transition-colors
                     bg-[var(--color-accent)] text-white
                     hover:bg-[var(--color-accent-hover)]
                     disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {nlParsing ? "Tolkar..." : "Sök"}
        </button>
      </div>
      {nlInterpreted && (
        <div className="flex items-center gap-2 px-1 text-xs text-[var(--color-text-muted)]">
          <span>Filter: {nlInterpreted}</span>
          <button
            onClick={() => { setNlInterpreted(""); setFilters(DEFAULT_FILTERS); setNlQuery(""); }}
            className="ml-auto hover:text-[var(--color-down)]"
          >
            <X size={12} />
          </button>
        </div>
      )}

      {/* Screener presets */}
      <div className="flex gap-1.5 flex-wrap">
        {SCREENER_PRESETS.map((preset) => (
          <button
            key={preset.label}
            onClick={() => {
              setFilters(prev => ({ ...prev, ...preset.params }));
            }}
            className="px-3 py-1.5 rounded-full text-xs font-medium transition-colors
                       border border-[var(--color-border)] text-[var(--color-text-secondary)]
                       hover:bg-[var(--color-accent-soft)] hover:text-[var(--color-accent)]
                       hover:border-[var(--color-accent)]"
          >
            {preset.label}
          </button>
        ))}
      </div>

      {/* Segment + filters in one block */}
      <div className="rounded-xl border p-4 space-y-4 bg-[var(--color-bg-surface)] border-[var(--color-border)]">
        <SegmentToggle
          value={(filters.segments ?? ["large_cap", "mid_cap"]) as ("large_cap" | "mid_cap" | "small_cap" | "micro_cap")[]}
          onChange={(segments) => updateFilters({ segments })}
        />
        <div className="border-t pt-4 border-[var(--color-border)]">
          <FilterRail
            filters={filters}
            onChange={updateFilters}
            onReset={() => { setFilters(DEFAULT_FILTERS); setNlInterpreted(""); setNlQuery(""); }}
            inline
          />
        </div>
      </div>

      {/* Results */}
      <ResultTable data={data} loading={isLoading} onReset={() => { setFilters(DEFAULT_FILTERS); setNlInterpreted(""); setNlQuery(""); }} />

      {/* Score histogram */}
      {data.length > 0 && (
        <div className="p-4 rounded-xl border border-[var(--color-border)] bg-[var(--color-bg-surface)]">
          <div className="text-xs font-semibold mb-2 text-[var(--color-text-muted)]">
            Poängfördelning ({data.length} aktier)
          </div>
          <div className="flex items-end gap-1 h-16">
            {buckets.map((b, i) => (
              <div key={i} className="flex-1 flex flex-col items-center gap-1">
                <div
                  className="w-full rounded-t"
                  style={{
                    height: `${(b / maxBucket) * 100}%`,
                    background: "var(--color-accent)",
                    opacity: 0.3 + (b / maxBucket) * 0.5,
                  }}
                />
                <span className="text-[10px] text-[var(--color-text-muted)]">{i * 10}-{i * 10 + 9}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
