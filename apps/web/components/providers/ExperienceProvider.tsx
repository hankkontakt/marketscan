"use client";

import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import { api } from "@/lib/api";

export type ExperienceLevel = "beginner" | "expert";

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

export function ExperienceProvider({ children }: { children: React.ReactNode }) {
  const [level, setLevelState] = useState<ExperienceLevel>("beginner");
  const [loading, setLoading] = useState(true);
  const [onboardingCompleted, setOnboardingCompleted] = useState(false);

  // Load profile on mount
  useEffect(() => {
    api<{ experience_level?: string; onboarding_completed?: boolean }>("/api/profile")
      .then((data) => {
        if (data.experience_level === "expert") {
          setLevelState("expert");
        }
        if (data.onboarding_completed) {
          setOnboardingCompleted(true);
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const setLevel = useCallback((newLevel: ExperienceLevel) => {
    setLevelState(newLevel);
    api("/api/profile", {
      method: "PUT",
      body: JSON.stringify({ experience_level: newLevel }),
    }).catch(() => {});
  }, []);

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
