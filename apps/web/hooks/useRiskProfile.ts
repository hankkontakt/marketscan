"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

interface RiskProfile {
  user_id: string;
  profile: "trygg" | "balanserad" | "tillvaxt" | "aggressiv" | "maxrisk";
  risk_score: number;
  time_horizon_years: number | null;
  max_position_pct: number;
  target_volatility: number | null;
  answers: Record<string, number> | null;
}

export function useRiskProfile() {
  return useQuery<RiskProfile | null>({
    queryKey: ["risk-profile"],
    queryFn: () => api<RiskProfile | null>("/api/profile/risk").catch(() => null),
    staleTime: 60_000,
  });
}

export async function saveRiskProfile(data: {
  profile: string;
  risk_score: number;
  time_horizon_years?: number;
  answers?: Record<string, number>;
}) {
  return api("/api/profile/risk", {
    method: "POST",
    body: JSON.stringify(data),
  });
}
