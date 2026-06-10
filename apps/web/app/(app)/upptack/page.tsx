"use client";

import Link from "next/link";
import { Compass } from "lucide-react";
import { cn } from "@/lib/utils";
import { useExperience } from "@/components/providers/ExperienceProvider";
import { THEMES } from "@/lib/themes";
import { ThemeCard } from "@/components/screener/ThemeCard";

export default function UpptackPage() {
  const { level } = useExperience();
  const isBeginner = level === "beginner";

  if (isBeginner) {
    return (
      <div className="max-w-xl mx-auto px-4 py-10 space-y-10">
        {/* Hero */}
        <div className="text-center space-y-3">
          <h1 className="text-2xl font-bold text-[var(--color-text-primary)]">
            Upptäck aktier
          </h1>
          <p className="text-sm text-[var(--color-text-secondary)] leading-relaxed max-w-md mx-auto">
              Här hittar du färdiga teman som hjälper dig att upptäcka aktier
              oavsett om du letar efter stabila utdelare, växande småbolag eller
              något däremellan. Klicka runt och se vad som passar dig.
            </p>
        </div>

        {/* Theme cards */}
        <div className="space-y-6">
          {THEMES.map((theme) => (
            <ThemeCard key={theme.id} theme={theme} />
          ))}
        </div>

        {/* Beginner footer */}
        <div className="text-center pt-4 pb-8">
          <p className="text-xs text-[var(--color-text-muted)]">
            När du känner dig redo kan du{" "}
            <Link
              href="/installningar"
              className="text-[var(--color-accent)] hover:underline"
            >
              växla till expertläge
            </Link>{" "}
            för att använda det fullständiga screener-verktyget med avancerade
            filter och sökningar.
          </p>
        </div>
      </div>
    );
  }

  // ── Non-beginner (intermediate / expert) ──────────────────────────────
  return (
    <div className="max-w-4xl mx-auto px-4 py-8 space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-[var(--color-text-primary)]">
          Upptäck aktier
        </h1>
        <p className="text-sm text-[var(--color-text-secondary)] mt-1">
          Färdiga teman baserade på våra screening-modeller
        </p>
      </div>

      {/* 2-column grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {THEMES.map((theme) => (
          <ThemeCard key={theme.id} theme={theme} />
        ))}
      </div>
    </div>
  );
}
