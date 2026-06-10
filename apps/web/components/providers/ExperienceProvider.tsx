"use client";

import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import { api } from "@/lib/api";
import { trackEvent, EVENT } from "@/lib/tracking";

export type ExperienceLevel = "beginner" | "intermediate" | "expert";

const LEVEL_ORDER: Record<ExperienceLevel, number> = { beginner: 0, intermediate: 1, expert: 2 };

interface ExperienceContextValue {
  level: ExperienceLevel;
  setLevel: (level: ExperienceLevel) => void;
  loading: boolean;
  onboardingCompleted: boolean;
  completeOnboarding: () => void;
}

const ExperienceContext = createContext<ExperienceContextValue>({
  level: "beginner",
  setLevel: () => {},
  loading: true,
  onboardingCompleted: false,
  completeOnboarding: () => {},
});

export function useExperience() {
  return useContext(ExperienceContext);
}

/**
 * Renders children only when experience level is "expert".
 * Use to hide advanced metrics/data from beginner view.
 */
export function ExpertOnly({ children }: { children: React.ReactNode }) {
  const { level } = useExperience();
  if (level !== "expert") return null;
  return <>{children}</>;
}

export function BeginnerOnly({ children }: { children: React.ReactNode }) {
  const { level } = useExperience();
  if (level !== "beginner") return null;
  return <>{children}</>;
}

export function NonExpertOnly({ children }: { children: React.ReactNode }) {
  const { level } = useExperience();
  if (level === "expert") return null;
  return <>{children}</>;
}

export function ExperienceProvider({ children }: { children: React.ReactNode }) {
  const [level, setLevelState] = useState<ExperienceLevel>("beginner");
  const [loading, setLoading] = useState(true);
  const [onboardingCompleted, setOnboardingCompleted] = useState(false);

  // Load profile on mount
  useEffect(() => {
    api<{ experience_level?: string; onboarding_completed?: boolean }>("/api/profile")
      .then((data) => {
        if (data.experience_level === "expert" || data.experience_level === "intermediate") {
          setLevelState(data.experience_level);
        }
        if (data.onboarding_completed) {
          setOnboardingCompleted(true);
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const setLevel = useCallback((newLevel: ExperienceLevel) => {
    const prevLevel = level;
    setLevelState(newLevel);
    api("/api/profile", {
      method: "PUT",
      body: JSON.stringify({ experience_level: newLevel }),
    }).catch(() => {});
    if (prevLevel !== newLevel) {
      trackEvent(EVENT.BEGINNER_TOGGLE, { from: prevLevel, to: newLevel });
    }
  }, [level]);

  const completeOnboarding = useCallback(() => {
    setOnboardingCompleted(true);
    api("/api/profile", {
      method: "PUT",
      body: JSON.stringify({ onboarding_completed: true }),
    }).catch(() => {});
  }, []);

  return (
    <ExperienceContext.Provider value={{ level, setLevel, loading, onboardingCompleted, completeOnboarding }}>
      {children}
    </ExperienceContext.Provider>
  );
}
