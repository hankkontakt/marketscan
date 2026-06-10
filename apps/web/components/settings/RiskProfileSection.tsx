"use client";

import { useState } from "react";
import { TrendingUp, Shield, Info } from "lucide-react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { SectionCard, SectionTitle } from "./SectionCard";
import { InfoTooltip } from "@/components/ui/InfoTooltip";
import { api } from "@/lib/api";
import { toast } from "sonner";

interface RiskProfile {
  profile: string;
  risk_score: number;
  max_position_pct: number;
  target_volatility: number | null;
}

const QUESTIONS = [
  { id: "q1", label: "Hur lång är din sparhorisont?", options: ["<1 år", "1–3 år", "3–5 år", "5–10 år", ">10 år"], values: [1, 2, 3, 4, 5] },
  { id: "q2", label: "Hur skulle du reagera om din portfölj sjönk 20% på en månad?", options: ["Sälja allt", "Bli orolig men avvakta", "Göra ingenting", "Köpa mer", "Köpa mycket mer"], values: [1, 2, 3, 4, 5] },
  { id: "q3", label: "Hur stabil är din inkomst?", options: ["Mycket ostabil", "Varierande", "Ganska stabil", "Stabil", "Mycket stabil"], values: [1, 2, 3, 4, 5] },
  { id: "q4", label: "Hur bedömer du dina investeringskunskaper?", options: ["Ingen erfarenhet", "Nybörjare", "Viss erfarenhet", "Erfaren", "Professionell"], values: [1, 2, 3, 4, 5] },
  { id: "q5", label: "Vad är ditt främsta mål med sparandet?", options: ["Bevara kapital", "Låg avkastning", "Balanserad tillväxt", "Hög avkastning", "Maximera avkastning"], values: [1, 2, 3, 4, 5] },
  { id: "q6", label: "Hur stor del av ditt sparande kan du tänka dig att förlora på ett år?", options: ["0%", "Högst 5%", "Högst 10%", "Högst 25%", "Över 25%"], values: [1, 2, 3, 4, 5] },
];

const PROFILE_LABELS: Record<string, string> = {
  trygg: "Trygg",
  balanserad: "Balanserad",
  tillvaxt: "Tillväxt",
  aggressiv: "Aggressiv",
  maxrisk: "Maxrisk",
};

export function RiskProfileSection() {
  const qc = useQueryClient();
  const [answers, setAnswers] = useState<Record<string, number>>({});

  const { data: profile, isLoading } = useQuery<RiskProfile | null>({
    queryKey: ["risk-profile"],
    queryFn: () => api<RiskProfile | null>("/api/profile/risk").catch(() => null),
    staleTime: 60_000,
  });

  const saveMutation = useMutation({
    mutationFn: (data: { answers: Record<string, number> }) =>
      api("/api/profile/risk", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["risk-profile"] });
      toast.success("Riskprofil sparad!");
    },
    onError: () => toast.error("Kunde inte spara riskprofil"),
  });

  const handleAnswer = (qId: string, value: number) => {
    setAnswers((prev) => ({ ...prev, [qId]: value }));
  };

  const handleSave = () => {
    if (Object.keys(answers).length < 6) {
      toast.error("Svara på alla frågor först");
      return;
    }
    saveMutation.mutate({ answers });
  };

  if (isLoading) {
    return (
      <SectionCard>
        <SectionTitle icon={TrendingUp} title="Riskprofil" />
        <p className="text-xs text-[var(--color-text-muted)]">Laddar...</p>
      </SectionCard>
    );
  }

  return (
    <SectionCard>
      <SectionTitle icon={TrendingUp} title="Riskprofil" />

      {profile && (
        <div className="flex items-center gap-3 p-3 rounded-lg bg-[var(--color-bg-elevated)]">
          <Shield size={16} className="text-[var(--color-accent)]" />
          <div className="text-xs">
            <span className="font-medium text-[var(--color-text-primary)]">
              {PROFILE_LABELS[profile.profile] ?? profile.profile}
            </span>
            <span className="text-[var(--color-text-muted)] ml-2">
              (riskpoäng: {profile.risk_score}/100, max position: {profile.max_position_pct * 100}%)
            </span>
          </div>
          <button
            onClick={() => setAnswers({})}
            className="ml-auto text-xs text-[var(--color-accent)] hover:underline"
          >
            Gör om testet
          </button>
        </div>
      )}

      <p className="text-xs text-[var(--color-text-muted)] leading-relaxed">
        Svara på 6 frågor för att få en rekommenderad riskprofil.
        Profilen används av portföljbyggaren för att anpassa Black-Litterman-modellens parametrar.
      </p>

      <div className="space-y-4">
        {QUESTIONS.map((q) => (
          <div key={q.id} className="space-y-2">
            <p className="text-xs font-medium text-[var(--color-text-secondary)]">{q.label}</p>
            <div className="flex flex-wrap gap-1.5">
              {q.options.map((opt, i) => (
                <button
                  key={opt}
                  onClick={() => handleAnswer(q.id, q.values[i])}
                  className={`px-2.5 py-1 rounded-lg text-xs transition-colors border ${
                    answers[q.id] === q.values[i]
                      ? "bg-[var(--color-accent)] text-white border-[var(--color-accent)]"
                      : "bg-[var(--color-bg-surface)] text-[var(--color-text-secondary)] border-[var(--color-border)] hover:border-[var(--color-accent)]"
                  }`}
                >
                  {opt}
                </button>
              ))}
            </div>
          </div>
        ))}
      </div>

      <button
        onClick={handleSave}
        disabled={saveMutation.isPending || Object.keys(answers).length < 6}
        className="px-4 py-2 rounded-lg text-sm font-medium bg-[var(--color-accent)] text-white
                   disabled:opacity-40 hover:opacity-90 transition-opacity"
      >
        {saveMutation.isPending ? "Sparar..." : "Spara riskprofil"}
      </button>
    </SectionCard>
  );
}
