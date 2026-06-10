"use client";

import { FileText } from "lucide-react";
import { useEarningsMemo } from "@/hooks/useEarningsMemo";
import { InfoTooltip } from "@/components/ui/InfoTooltip";

const TONE: Record<string, { label: string; cls: string }> = {
  positiv:  { label: "Positiv ton",  cls: "bg-[var(--color-up-soft)] text-[var(--color-up)]" },
  neutral:  { label: "Neutral ton",  cls: "bg-[var(--color-bg-elevated)] text-[var(--color-text-secondary)]" },
  defensiv: { label: "Defensiv ton", cls: "bg-[var(--color-warn-soft)] text-[var(--color-warn)]" },
};

/**
 * EarningsMemoCard — AI-genererat memo från senaste rapporten (Spec 08).
 * Visas bara om ett memo finns (annars renderas inget).
 */
export function EarningsMemoCard({ ticker }: { ticker: string }) {
  const { data, isLoading } = useEarningsMemo(ticker);

  if (isLoading) return <div className="h-40 rounded-xl skeleton" />;
  if (!data || !data.memo) return null;

  const m = data.memo;
  const tone = TONE[m.ledningston ?? "neutral"] ?? TONE.neutral;

  return (
    <div className="rounded-xl border p-5 bg-[var(--color-bg-surface)] border-[var(--color-border)] space-y-3">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <FileText size={15} strokeWidth={1.5} className="text-[var(--color-accent)]" />
          <h3 className="text-sm font-semibold text-[var(--color-text-primary)]">Rapportanalys</h3>
          <InfoTooltip text="AI-sammanfattning av bolagets senaste delårs-/årsrapport: ledningens ton, implicit guidning och nyckelcitat — grundat i rapporttexten." side="top" />
        </div>
        <span className={`text-[10px] font-medium px-2 py-0.5 rounded-md ${tone.cls}`}>{tone.label}</span>
      </div>

      {m.sammanfattning && (
        <p className="text-sm text-[var(--color-text-primary)] leading-relaxed">{m.sammanfattning}</p>
      )}

      {m.implicit_guidning && (
        <div>
          <p className="text-[11px] uppercase tracking-wide text-[var(--color-text-muted)] mb-0.5">Implicit guidning</p>
          <p className="text-xs text-[var(--color-text-secondary)]">{m.implicit_guidning}</p>
        </div>
      )}

      {m.nyckeltal_kommentar && (
        <div>
          <p className="text-[11px] uppercase tracking-wide text-[var(--color-text-muted)] mb-0.5">Nyckeltal</p>
          <p className="text-xs text-[var(--color-text-secondary)]">{m.nyckeltal_kommentar}</p>
        </div>
      )}

      {m.tre_citat && m.tre_citat.length > 0 && (
        <div>
          <p className="text-[11px] uppercase tracking-wide text-[var(--color-text-muted)] mb-1">Ur rapporten</p>
          <ul className="space-y-1">
            {m.tre_citat.slice(0, 3).map((c, i) => (
              <li key={i} className="text-xs italic text-[var(--color-text-secondary)] border-l-2 border-[var(--color-border-strong)] pl-2">
                {c}
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="flex items-center justify-between pt-1 text-[11px] text-[var(--color-text-muted)]">
        <span>{data.published_date ? `Rapport ${data.published_date}` : "Senaste rapporten"}</span>
        {m._grounding_warning && <span className="text-[var(--color-warn)]">AI-genererad — verifiera siffror</span>}
      </div>
    </div>
  );
}
