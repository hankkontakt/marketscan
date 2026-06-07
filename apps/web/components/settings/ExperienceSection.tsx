"use client";

import { GraduationCap } from "lucide-react";
import { useExperience } from "@/components/providers/ExperienceProvider";
import { SectionCard, SectionTitle } from "./SectionCard";

export function ExperienceSection() {
  const { level, setLevel } = useExperience();

  return (
    <SectionCard>
      <SectionTitle icon={GraduationCap} title="Erfarenhetsnivå" />

      <div className="space-y-3">
        <p className="text-xs text-[var(--color-text-muted)]">
          Välj hur mycket information som visas. Du kan ändra när som helst.
        </p>

        <div className="flex gap-3">
          <button
            onClick={() => setLevel("beginner")}
            className={`flex-1 p-3 rounded-xl border text-left text-xs transition-all ${
              level === "beginner"
                ? "border-[var(--color-accent)] bg-[var(--color-accent-soft)]"
                : "border-[var(--color-border)] hover:border-[var(--color-border-strong)]"
            }`}
            style={{
              background: level === "beginner" ? "var(--color-accent-soft)" : "var(--color-bg-surface)",
              color: "var(--color-text-primary)",
            }}
          >
            <div className="font-medium mb-1">Nybörjare</div>
            <div className="text-[var(--color-text-muted)]">
              Enklare vyer, färre siffror, mer vägledning
            </div>
          </button>

          <button
            onClick={() => setLevel("expert")}
            className={`flex-1 p-3 rounded-xl border text-left text-xs transition-all ${
              level === "expert"
                ? "border-[var(--color-accent)] bg-[var(--color-accent-soft)]"
                : "border-[var(--color-border)] hover:border-[var(--color-border-strong)]"
            }`}
            style={{
              background: level === "expert" ? "var(--color-accent-soft)" : "var(--color-bg-surface)",
              color: "var(--color-text-primary)",
            }}
          >
            <div className="font-medium mb-1">Erfaren</div>
            <div className="text-[var(--color-text-muted)]">
              All data synlig, fler nyckeltal, avancerade verktyg
            </div>
          </button>
        </div>
      </div>
    </SectionCard>
  );
}
