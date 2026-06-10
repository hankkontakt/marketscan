"use client";

import { useQuery } from "@tanstack/react-query";
import { MessageSquare, Sparkles } from "lucide-react";
import Link from "next/link";
import { api } from "@/lib/api";
import { usePortfolio, useRiskAnalytics } from "@/hooks/usePortfolio";
import { useRiskProfile } from "@/hooks/useRiskProfile";
import { useMacroRegime } from "@/hooks/useMarkets";
import { MarkdownLite } from "@/components/ui/MarkdownLite";

interface CoachResponse {
  briefing: string;
  facts: Record<string, unknown>;
  date: string;
  disclaimer: string;
  empty: boolean;
}

/**
 * PortfolioCoachCard — proaktiv daglig AI-coach. Skickar innehav + riskprofil +
 * volatilitet + regim till /api/ai/daily-coach (servern beräknar alla fakta) och
 * visar en kort, grundad briefing. Cachas server-side per dag/portföljläge.
 */
export function PortfolioCoachCard() {
  const { data: portfolio } = usePortfolio();
  const { data: risk } = useRiskAnalytics();
  const { data: profile } = useRiskProfile();
  const { data: regime } = useMacroRegime();

  const holdings = (portfolio?.holdings ?? [])
    .filter(h => h.shares && h.price)
    .map(h => ({ ticker: h.ticker, shares: h.shares, price: h.price }));

  const payload = {
    holdings,
    risk_profile: profile
      ? { profile: profile.profile, max_position_pct: profile.max_position_pct, target_volatility: profile.target_volatility }
      : null,
    volatility_ann: risk?.volatility_ann ?? null,
    regime_label: regime?.label ?? null,
  };

  // Stabil nyckel: tickers+shares (regenererar vid portföljändring)
  const stateKey = holdings.map(h => `${h.ticker}:${h.shares}`).sort().join(",");

  const { data, isLoading } = useQuery<CoachResponse>({
    queryKey: ["daily-coach", stateKey],
    queryFn: () => api<CoachResponse>("/api/ai/daily-coach", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
    enabled: holdings.length > 0,
    staleTime: 6 * 60 * 60_000,
    retry: 1,
  });

  return (
    <div className="rounded-xl border bg-[var(--color-bg-surface)] border-[var(--color-border)] p-4">
      <div className="flex items-center gap-2 mb-2">
        <Sparkles size={14} strokeWidth={1.5} className="text-[var(--color-accent)]" />
        <h2 className="text-sm font-semibold text-[var(--color-text-primary)]">Din portföljcoach</h2>
      </div>

      {holdings.length === 0 ? (
        <div>
          <p className="text-sm text-[var(--color-text-secondary)]">
            Lägg till innehav för en daglig coach-briefing om risk, övervikter och förbättringar.
          </p>
          <Link href="/portfolj" className="text-xs text-[var(--color-accent)] hover:underline mt-1 inline-block">
            Gå till portföljen →
          </Link>
        </div>
      ) : isLoading ? (
        <div className="space-y-2">
          {[1, 2, 3].map(i => <div key={i} className="h-3 rounded skeleton" />)}
        </div>
      ) : data?.briefing ? (
        <>
          <MarkdownLite
            text={data.briefing}
            className="text-sm text-[var(--color-text-primary)] leading-relaxed"
          />
          <p className="text-[11px] text-[var(--color-text-muted)] mt-3 flex items-start gap-1.5">
            <MessageSquare size={11} strokeWidth={1.5} className="mt-0.5 shrink-0" />
            {data.disclaimer}
          </p>
        </>
      ) : (
        <p className="text-sm text-[var(--color-text-muted)]">Coach-briefing ej tillgänglig just nu.</p>
      )}
    </div>
  );
}
