"use client";

import { cn } from "@/lib/utils";
import { InfoTooltip } from "@/components/ui/InfoTooltip";
import { segmentLabel } from "@/lib/format";

const SEGMENTS = ["large_cap", "mid_cap", "small_cap", "micro_cap"] as const;
type Segment = (typeof SEGMENTS)[number];

const PRESETS = [
  { label: "Stora & medelstora", segments: ["large_cap", "mid_cap"] as Segment[] },
  { label: "Småbolag", segments: ["small_cap", "micro_cap"] as Segment[] },
  { label: "Alla", segments: [...SEGMENTS] as Segment[] },
] as const;

interface Props {
  value: Segment[];
  onChange: (v: Segment[]) => void;
}

export function SegmentToggle({ value, onChange }: Props) {
  function toggle(seg: Segment) {
    const next = value.includes(seg)
      ? value.filter((s) => s !== seg)
      : [...value, seg];
    if (next.length > 0) onChange(next);
  }

  function applyPreset(segments: readonly Segment[]) {
    onChange([...segments]);
  }

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center gap-1">
        <span className="text-xs text-[var(--color-text-muted)]">Segment</span>
        <InfoTooltip text="Välj marknadssegment baserat på börsvärde." />
      </div>
      {/* Preset chips */}
      <div className="flex gap-1.5 flex-wrap">
        {PRESETS.map((preset) => {
          const active =
            preset.segments.length === value.length &&
            preset.segments.every((s) => value.includes(s));
          return (
            <button
              key={preset.label}
              onClick={() => applyPreset(preset.segments)}
              className={cn(
                "px-3 py-1 rounded-full text-xs font-medium transition-colors",
                active
                  ? "bg-[var(--color-accent)] text-white"
                  : "bg-[var(--color-bg-elevated)] text-[var(--color-text-secondary)] hover:bg-[var(--color-border-strong)]",
              )}
            >
              {preset.label}
            </button>
          );
        })}
      </div>

      {/* Individual segment chips */}
      <div className="flex gap-1.5 flex-wrap">
        {SEGMENTS.map((seg) => {
          const active = value.includes(seg);
          return (
            <button
              key={seg}
              onClick={() => toggle(seg)}
              className={cn(
                "px-2.5 py-1 rounded-md text-xs transition-colors border",
                active
                  ? "border-[var(--color-accent)] text-[var(--color-accent)] bg-[var(--color-accent-soft)]"
                  : "border-[var(--color-border)] text-[var(--color-text-muted)] hover:border-[var(--color-border-strong)]",
              )}
            >
              {segmentLabel(seg)}
            </button>
          );
        })}
      </div>
    </div>
  );
}
