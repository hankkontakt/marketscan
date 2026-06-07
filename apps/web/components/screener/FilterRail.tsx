"use client";

import { useState } from "react";
import { ChevronDown, Filter, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { InfoTooltip } from "@/components/ui/InfoTooltip";
import { useSectors } from "@/hooks/useScreener";
import type { ScanParams } from "@/lib/api";

interface Props {
  filters: ScanParams;
  onChange: (f: Partial<ScanParams>) => void;
  onReset: () => void;
  inline?: boolean; // when true: no outer card wrapper
}

const SIGNALS = [
  { value: "STARK", label: "Starkt köpläge" },
  { value: "OK",    label: "Bra läge" },
  { value: "VÄNTA", label: "Avvakta" },
];

const TRENDS = [
  { value: "Upptrend", label: "Upptrend" },
  { value: "Sidled",   label: "Sidled" },
  { value: "Nedtrend", label: "Nedtrend" },
];

export function FilterRail({ filters, onChange, onReset, inline }: Props) {
  const { data: sectors = [] } = useSectors();
  const [expanded, setExpanded] = useState(false);

  const hasActive =
    filters.entry_signal || filters.trend_signal || filters.sector ||
    (filters.score_min ?? 0) > 0 || filters.piotroski_min ||
    filters.pe_max || filters.roe_min || filters.dividend_yield_min ||
    filters.exclude_low_liquidity;

  const inner = (
    <>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-sm font-medium text-[var(--color-text-primary)]">
          <Filter size={14} strokeWidth={1.5} />
          Filter
          {hasActive && (
            <span className="px-1.5 py-0.5 rounded text-[10px] font-mono
                             bg-[var(--color-accent-soft)] text-[var(--color-accent)]">
              aktiva
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {hasActive && (
            <button onClick={onReset}
                    className="text-xs text-[var(--color-text-muted)] hover:text-[var(--color-down)] flex items-center gap-1">
              <X size={12} /> Rensa
            </button>
          )}
          <button onClick={() => setExpanded(!expanded)}
                  className="text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]">
            <ChevronDown size={16} className={cn("transition-transform", expanded && "rotate-180")} />
          </button>
        </div>
      </div>

      {/* Always visible */}
      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1">
          <label className="flex items-center text-[11px] text-[var(--color-text-muted)]">
            Köpläge
            <InfoTooltip text="Välj entry-signal: STARK, OK, VÄNTA, eller EJ AKTUELL." />
          </label>
          <FilterSelect label="Entry-signal"
            value={filters.entry_signal ?? ""}
            onChange={(v) => onChange({ entry_signal: v || undefined })}
            options={[{ value: "", label: "Alla" }, ...SIGNALS]}
          />
        </div>
        <div className="space-y-1">
          <label className="flex items-center text-[11px] text-[var(--color-text-muted)]">
            Trend
            <InfoTooltip text="Filtrera på trendriktning: upptrend, sidled, eller nedtrend." />
          </label>
          <FilterSelect label="Trend"
            value={filters.trend_signal ?? ""}
            onChange={(v) => onChange({ trend_signal: v || undefined })}
            options={[{ value: "", label: "Alla" }, ...TRENDS]}
          />
        </div>
      </div>

      {/* Expanded filters */}
      {expanded && (
        <div className="grid grid-cols-2 gap-3 pt-2 border-t border-[var(--color-border)]">
          <div className="space-y-1">
            <label className="flex items-center text-[11px] text-[var(--color-text-muted)]">
              Sektor
              <InfoTooltip text="Filtrera på marknadssektor." />
            </label>
            <FilterSelect label="Sektor"
              value={filters.sector ?? ""}
              onChange={(v) => onChange({ sector: v || undefined })}
              options={[{ value: "", label: "Alla sektorer" }, ...sectors.map(s => ({ value: s, label: s }))]}
            />
          </div>
          <div className="space-y-1">
            <label className="flex items-center text-[11px] text-[var(--color-text-muted)]">
              Totalbetyg min
              <InfoTooltip text="Minsta totalbetyg. 60+ = positivt, 70+ = starkt." />
            </label>
            <FilterNumber label="Totalbetyg min"
              value={filters.score_min}
              onChange={(v) => onChange({ score_min: v })}
              min={0} max={100} step={5}
            />
          </div>
          <FilterNumber
            label="Piotroski F min"
            value={filters.piotroski_min}
            onChange={(v) => onChange({ piotroski_min: v })}
            min={0} max={9} step={1}
          />
          <FilterNumber
            label="P/E max"
            value={filters.pe_max}
            onChange={(v) => onChange({ pe_max: v })}
            min={0} max={100} step={1}
          />
          <FilterNumber
            label="ROE min (%)"
            value={filters.roe_min != null ? filters.roe_min * 100 : undefined}
            onChange={(v) => onChange({ roe_min: v != null ? v / 100 : undefined })}
            min={0} max={50} step={1}
          />
          <FilterNumber
            label="Direktavkastning min (%)"
            value={filters.dividend_yield_min != null ? filters.dividend_yield_min * 100 : undefined}
            onChange={(v) => onChange({ dividend_yield_min: v != null ? v / 100 : undefined })}
            min={0} max={15} step={0.5}
          />

          {/* Exclude low liquidity */}
          <label className="flex items-center gap-2 text-xs col-span-2 cursor-pointer text-[var(--color-text-secondary)]">
            <input
              type="checkbox"
              checked={filters.exclude_low_liquidity ?? false}
              onChange={(e) => onChange({ exclude_low_liquidity: e.target.checked })}
              className="accent-[var(--color-accent)]"
            />
            Exkludera låg likviditet
          </label>
        </div>
      )}
    </>
  );

  if (inline) return <div className="space-y-4">{inner}</div>;

  return (
    <div className="rounded-xl border p-4 space-y-4 bg-[var(--color-bg-surface)] border-[var(--color-border)]">
      {inner}
    </div>
  );
}

function FilterSelect({ label, value, onChange, options }: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: { value: string; label: string }[];
}) {
  return (
    <div className="space-y-1">
      <label className="text-[11px] text-[var(--color-text-muted)]">{label}</label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full h-8 px-2 rounded-lg text-xs border cursor-pointer
                   bg-[var(--color-bg-elevated)] border-[var(--color-border)]
                   text-[var(--color-text-primary)]
                   focus:border-[var(--color-accent)] focus:outline-none"
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>{o.label}</option>
        ))}
      </select>
    </div>
  );
}

function FilterNumber({ label, value, onChange, min, max, step }: {
  label: string;
  value: number | undefined;
  onChange: (v: number | undefined) => void;
  min: number; max: number; step: number;
}) {
  return (
    <div className="space-y-1">
      <label className="text-[11px] text-[var(--color-text-muted)]">{label}</label>
      <input
        type="number"
        value={value ?? ""}
        min={min} max={max} step={step}
        onChange={(e) => onChange(e.target.value ? Number(e.target.value) : undefined)}
        className="w-full h-8 px-2 rounded-lg text-xs border
                   bg-[var(--color-bg-elevated)] border-[var(--color-border)]
                   text-[var(--color-text-primary)] font-mono
                   focus:border-[var(--color-accent)] focus:outline-none"
        placeholder="—"
      />
    </div>
  );
}
