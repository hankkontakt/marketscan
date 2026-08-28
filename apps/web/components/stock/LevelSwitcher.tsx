"use client";

import { cn } from "@/lib/utils";
import { useExperience, type ExperienceLevel } from "@/components/providers/ExperienceProvider";

const LEVELS: { id: ExperienceLevel; label: string }[] = [
  { id: "beginner", label: "Enkelt" },
  { id: "intermediate", label: "Mellan" },
  { id: "expert", label: "Avancerat" },
];

/**
 * Level switcher — lets the user change the experience level (and with it
 * the detail density of this page) without leaving it. Persists via the
 * existing useExperience().setLevel API.
 */
export function LevelSwitcher({ className }: { className?: string }) {
  const { level, setLevel, loading } = useExperience();

  if (loading) return null;

  return (
    <div
      className={cn("flex items-center gap-1 flex-wrap", className)}
      role="group"
      aria-label="Välj visningsnivå för aktiesidan"
    >
      <span className="text-[10px] font-medium text-[var(--color-text-muted)] mr-0.5">
        Visa som
      </span>
      {LEVELS.map((l) => (
        <button
          key={l.id}
          onClick={() => setLevel(l.id)}
          aria-pressed={level === l.id}
          className={cn(
            "px-2.5 py-1 rounded-md text-xs font-medium transition-colors border",
            level === l.id
              ? "border-[var(--color-accent)] text-[var(--color-accent)] bg-[var(--color-accent-soft)]"
              : "border-[var(--color-border)] text-[var(--color-text-muted)] hover:border-[var(--color-border-strong)] hover:text-[var(--color-text-secondary)]",
          )}
        >
          {l.label}
        </button>
      ))}
    </div>
  );
}
