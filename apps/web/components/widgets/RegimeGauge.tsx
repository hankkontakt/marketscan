"use client";

import { useMacroRegime } from "@/hooks/useMarkets";
import { InfoTooltip } from "@/components/ui/InfoTooltip";

/**
 * RegimeGauge — halvcirkel-mätare för marknadsregim (björn/neutral/tjur).
 * Visualiserar HMM-/makroregimen. Nålvinkel styrs av regime.color så den är
 * robust oavsett exakt regim-sträng (TJUR/BJÖRN/OSÄKER/NEUTRAL).
 */
export function RegimeGauge() {
  const { data: regime, isLoading } = useMacroRegime();

  const color = regime?.color ?? "neutral";
  // Nålvinkel i grader: -90 (vänster/björn) … 0 (topp/neutral) … +90 (höger/tjur)
  const angle =
    color === "green" ? 55 :
    color === "red"   ? -55 :
    color === "amber" ? -20 :
    0;

  const arcColor =
    color === "green" ? "var(--color-up)" :
    color === "red"   ? "var(--color-down)" :
    color === "amber" ? "var(--color-warn)" :
    "var(--color-text-muted)";

  // Geometri för SVG-nål (mittpunkt 100,90, radie 70)
  const rad = ((angle - 90) * Math.PI) / 180;
  const nx = 100 + 62 * Math.cos(rad);
  const ny = 90 + 62 * Math.sin(rad);

  return (
    <div className="rounded-xl border bg-[var(--color-bg-surface)] border-[var(--color-border)] p-4 flex flex-col items-center">
      <div className="flex items-center gap-1.5 self-start mb-1">
        <span className="text-[11px] text-[var(--color-text-muted)] font-medium uppercase tracking-wide">
          Marknadsregim
        </span>
        <InfoTooltip text="Systemets bedömda marknadsläge (björn/neutral/tjur) från makro-/HMM-modellen. Påverkar hur scoringen viktar momentum vs lågvolatilitet." side="top" />
      </div>

      <svg viewBox="0 0 200 110" className="w-full max-w-[180px]">
        {/* Bakgrundsbåge */}
        <path d="M 20 90 A 80 80 0 0 1 180 90" fill="none"
              stroke="var(--color-bg-elevated)" strokeWidth="10" strokeLinecap="round" />
        {/* Zon-markeringar */}
        <path d="M 20 90 A 80 80 0 0 1 70 26" fill="none" stroke="var(--color-down)" strokeWidth="10" strokeLinecap="round" opacity="0.25" />
        <path d="M 130 26 A 80 80 0 0 1 180 90" fill="none" stroke="var(--color-up)" strokeWidth="10" strokeLinecap="round" opacity="0.25" />
        {/* Nål */}
        <line x1="100" y1="90" x2={nx} y2={ny} stroke={arcColor} strokeWidth="3" strokeLinecap="round" />
        <circle cx="100" cy="90" r="5" fill={arcColor} />
      </svg>

      <span className="text-sm font-semibold mt-1" style={{ color: arcColor }}>
        {isLoading ? "…" : (regime?.label ?? "Okänt läge")}
      </span>
      {regime?.description && (
        <span className="text-[11px] text-[var(--color-text-muted)] text-center mt-0.5 line-clamp-2">
          {regime.description}
        </span>
      )}
    </div>
  );
}
