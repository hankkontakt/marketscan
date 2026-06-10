"use client";

import { useState, useEffect } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { TrendingUp, X } from "lucide-react";
import { useExperience } from "@/components/providers/ExperienceProvider";
import { trackEvent, EVENT } from "@/lib/tracking";

/**
 * OnboardingModal — shown once for new users.
 * 2-3 step light onboarding, no separate page.
 */
export function OnboardingModal() {
  const { loading, onboardingCompleted, completeOnboarding, setLevel, level } = useExperience();
  const [step, setStep] = useState(0);
  const [open, setOpen] = useState(false);

  // Show modal once profile is loaded and onboarding not completed
  useEffect(() => {
    if (!loading && !onboardingCompleted) {
      setOpen(true);
    }
  }, [loading, onboardingCompleted]);

  // Don't show if already completed or still loading
  if (loading || onboardingCompleted || !open) return null;

  const steps = [
    {
      title: "Välkommen till MarketScan",
      description: "Din personliga aktieanalys. Vi hjälper dig screena, analysera och följa dina aktier.",
    },
    {
      title: "Vilken erfarenhetsnivå passar dig?",
      description: "Du kan alltid ändra detta senare i Inställningar.",
      options: [
        {
          value: "beginner" as const,
          label: "Nybörjare",
          desc: "Enklare vyer, färre siffror, mer vägledning och förklaringar.",
        },
        {
          value: "expert" as const,
          label: "Erfaren",
          desc: "Fler nyckeltal, tätare vyer, avancerade verktyg som backtest och portföljoptimering.",
        },
      ],
    },
    {
      title: "Klart!",
      description: "Utforska aktier, bygg din portfölj och få AI-baserad analys. Börja med att titta på översikten.",
    },
  ];

  const current = steps[step];

  function handleContinue() {
    if (step < steps.length - 1) {
      setStep(step + 1);
    } else {
      trackEvent(EVENT.ONBOARDING_COMPLETED, { level });
      completeOnboarding();
      setOpen(false);
    }
  }

  function handleSkip() {
    trackEvent(EVENT.ONBOARDING_COMPLETED, { level, skipped: true });
    // If user skipped before selecting a level, default to beginner
    if (step < 1) {
      setLevel("beginner");
    }
    completeOnboarding();
    setOpen(false);
  }

  return (
    <Dialog.Root open={open} onOpenChange={setOpen}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-black/30 backdrop-blur-sm" />
        <Dialog.Content
          className="fixed z-50 top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2
                     w-full max-w-md rounded-2xl shadow-2xl p-6
                     bg-[var(--color-bg-surface)] border border-[var(--color-border-strong)]"
        >
          <div className="flex items-center gap-2 mb-4">
            <TrendingUp size={20} strokeWidth={1.5} className="text-[var(--color-accent)]" />
            <span className="text-sm font-semibold text-[var(--color-text-primary)]">MarketScan</span>
          </div>

          {/* Step indicator */}
          <div className="flex gap-1.5 mb-4">
            {steps.map((_, i) => (
              <div
                key={i}
                className="h-1 flex-1 rounded-full transition-colors"
                style={{
                  background: i <= step ? "var(--color-accent)" : "var(--color-border)",
                }}
              />
            ))}
          </div>

          <Dialog.Title className="text-lg font-semibold text-[var(--color-text-primary)] mb-2">
            {current.title}
          </Dialog.Title>

          <p className="text-sm leading-relaxed text-[var(--color-text-secondary)] mb-4">
            {current.description}
          </p>

          {/* Options (step 1) */}
          {"options" in current && current.options && (
            <div className="space-y-2 mb-4">
              {current.options.map((opt) => (
                <button
                  key={opt.value}
                  onClick={() => {
                    setLevel(opt.value);
                    handleContinue();
                  }}
                  className="w-full text-left p-3 rounded-xl border transition-colors
                             border-[var(--color-border)] hover:border-[var(--color-accent)]
                             hover:bg-[var(--color-accent-soft)]"
                >
                  <div className="text-sm font-medium text-[var(--color-text-primary)]">{opt.label}</div>
                  <div className="text-xs text-[var(--color-text-muted)] mt-0.5">{opt.desc}</div>
                </button>
              ))}
            </div>
          )}

          {/* Navigation buttons */}
          <div className="flex items-center justify-between gap-2">
            <button
              onClick={handleSkip}
              className="text-xs text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)] transition-colors"
            >
              Hoppa över
            </button>

            {(!("options" in current) || !current.options) && (
              <button
                onClick={handleContinue}
                className="px-4 py-2 rounded-lg text-xs font-medium text-white
                           bg-[var(--color-accent)] hover:bg-[var(--color-accent-hover)] transition-colors"
              >
                {step < steps.length - 1 ? "Fortsätt" : "Kom igång"}
              </button>
            )}
          </div>

          <Dialog.Close asChild>
            <button
              className="absolute top-4 right-4 w-6 h-6 flex items-center justify-center rounded-md
                         text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]
                         hover:bg-[var(--color-bg-elevated)] transition-colors"
              onClick={handleSkip}
            >
              <X size={14} strokeWidth={1.5} />
            </button>
          </Dialog.Close>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
