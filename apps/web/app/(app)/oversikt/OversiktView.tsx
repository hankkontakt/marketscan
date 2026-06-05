"use client";

import Link from "next/link";
import { TrendingUp, TrendingDown, Bell, FileText, Trophy, Briefcase } from "lucide-react";
import { useScreener } from "@/hooks/useScreener";
import { usePortfolio } from "@/hooks/usePortfolio";
import { AreaChart, Area, ResponsiveContainer, Tooltip } from "recharts";
import {
  formatPctChange, formatPrice, signalLabel, signalClass, scoreColorClass, formatScore, changeClass,
} from "@/lib/format";
import { cn } from "@/lib/utils";

export function OversiktView() {
  const { data: topPicks = [], isLoading } = useScreener({
    segments: ["large_cap", "mid_cap", "small_cap"],
    entry_signal: "STARK",
    score_min: 70,
    limit: 5,
  });
  const { data: portfolio } = usePortfolio();

  const holdings = portfolio?.holdings ?? [];
  const totalValue = holdings.reduce((s, h) => s + (h.price ?? 0) * h.shares, 0);
  const totalCost = holdings.reduce((s, h) => s + (h.cost_basis ?? 0) * h.shares, 0);
  const totalReturn = totalCost > 0 ? (totalValue - totalCost) / totalCost : null;

  const date = new Date().toLocaleDateString("sv-SE", {
    weekday: "long", year: "numeric", month: "long", day: "numeric",
  });

  return (
    <div className="space-y-6">
      {/* Morning greeting */}
      <div className="rounded-2xl p-6 border"
           style={{ background: "var(--color-bg-surface)", borderColor: "var(--color-border)" }}>
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-xl font-semibold text-[var(--color-text-primary)]">
              Marknadsöversikt
            </h1>
            <p className="text-sm mt-1 text-[var(--color-text-muted)] capitalize">{date}</p>
          </div>
          <div className="flex items-center gap-4 text-xs text-[var(--color-text-secondary)]">
            <span className="font-mono tabular">OMXS30</span>
            <span className="font-mono tabular text-[var(--color-up)]">+0,4%</span>
          </div>
        </div>
      </div>

      {/* Portfolio summary — plan §9: "Portföljvärde + mini-area-graf" */}
      {holdings.length > 0 && (
        <div className="rounded-xl p-5 border"
             style={{ background: "var(--color-bg-surface)", borderColor: "var(--color-border)" }}>
          <div className="flex items-start justify-between gap-6">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <Briefcase size={14} strokeWidth={1.5} style={{ color: "var(--color-text-muted)" }} />
                <span className="text-xs text-[var(--color-text-secondary)]">Portföljvärde</span>
              </div>
              <div className="text-2xl font-bold font-mono tabular text-[var(--color-text-primary)]">
                {formatPrice(totalValue)}
              </div>
              {totalReturn != null && (
                <div className={cn("text-sm font-mono tabular mt-0.5", changeClass(totalReturn))}>
                  {formatPctChange(totalReturn)} total avkastning
                </div>
              )}
              <div className="flex items-center gap-3 mt-2 flex-wrap">
                {holdings.slice(0, 4).map((h) => (
                  <div key={h.ticker} className="text-xs text-[var(--color-text-muted)]">
                    <span className="font-mono">{h.ticker}</span>
                    {h.change_pct != null && (
                      <span className={cn("ml-1 font-mono tabular", changeClass(h.change_pct))}>
                        {formatPctChange(h.change_pct)}
                      </span>
                    )}
                  </div>
                ))}
                {holdings.length > 4 && (
                  <span className="text-xs text-[var(--color-text-muted)]">+{holdings.length - 4} till</span>
                )}
              </div>
            </div>
            <Link href="/portfolj"
                  className="text-xs text-[var(--color-accent)] hover:underline shrink-0">
              Visa portfölj →
            </Link>
          </div>
        </div>
      )}

      {/* Main grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Top picks */}
        <div className="rounded-xl border"
             style={{ background: "var(--color-bg-surface)", borderColor: "var(--color-border)" }}>
          <div className="flex items-center gap-2 px-5 py-4 border-b"
               style={{ borderColor: "var(--color-border)" }}>
            <Trophy size={15} strokeWidth={1.5} style={{ color: "var(--color-accent)" }} />
            <h2 className="text-sm font-medium text-[var(--color-text-primary)]">
              Dagens möjligheter
            </h2>
            <span className="ml-auto text-xs text-[var(--color-text-muted)]">Starkt köpläge</span>
          </div>
          <div>
            {isLoading
              ? Array.from({ length: 5 }).map((_, i) => (
                  <div key={i} className="flex gap-3 px-5 py-3 border-b"
                       style={{ borderColor: "var(--color-border)" }}>
                    <div className="skeleton h-4 w-24" />
                    <div className="skeleton h-4 w-16 ml-auto" />
                  </div>
                ))
              : topPicks.map((stock) => (
                  <Link
                    key={stock.ticker}
                    href={`/aktie/${stock.ticker}`}
                    className="flex items-center gap-3 px-5 py-3 border-b transition-colors
                               hover:bg-[var(--color-bg-elevated)] last:border-b-0"
                    style={{ borderColor: "var(--color-border)" }}
                  >
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs font-semibold text-[var(--color-text-primary)]">
                          {stock.ticker}
                        </span>
                        <span className="text-[11px] text-[var(--color-text-muted)] truncate">
                          {stock.name}
                        </span>
                      </div>
                    </div>
                    <span className={cn("font-mono text-xs font-bold tabular", scoreColorClass(stock.score_total))}>
                      {formatScore(stock.score_total)}
                    </span>
                    <span className={cn("font-mono text-xs tabular", changeClass(stock.change_pct))}>
                      {formatPctChange(stock.change_pct)}
                    </span>
                    <span className="font-mono text-xs tabular text-[var(--color-text-secondary)]">
                      {formatPrice(stock.price)}
                    </span>
                  </Link>
                ))}
          </div>
          <div className="px-5 py-3">
            <Link href="/screener?entry_signal=STARK"
                  className="text-xs text-[var(--color-accent)] hover:underline">
              Visa alla i screener →
            </Link>
          </div>
        </div>

        {/* Quick links */}
        <div className="space-y-4">
          <QuickCard
            icon={FileText}
            title="Rapporter idag"
            content="Se aktier som rapporterar idag i screener"
            href="/screener"
            color="var(--color-accent)"
          />
          <QuickCard
            icon={Bell}
            title="Aktiva larm"
            content="Hantera prisriktkurslarm för dina bevakningar"
            href="/bevakningar"
            color="var(--color-warn)"
          />
          <QuickCard
            icon={TrendingUp}
            title="Upptrend-aktier"
            content="Visa alla aktier i upptrend med högt betyg"
            href="/screener?trend_signal=Upptrend&score_min=60"
            color="var(--color-up)"
          />
        </div>
      </div>

      {/* Keyboard shortcut hint */}
      <p className="text-xs text-center text-[var(--color-text-muted)]">
        Tryck{" "}
        <kbd className="px-1.5 py-0.5 rounded border font-mono text-[10px]"
             style={{ borderColor: "var(--color-border)", background: "var(--color-bg-elevated)" }}>
          ⌘K
        </kbd>
        {" "}för att söka aktier eller hoppa till en vy
      </p>
    </div>
  );
}

function QuickCard({ icon: Icon, title, content, href, color }: {
  icon: React.ComponentType<{ size: number; strokeWidth: number }>;
  title: string;
  content: string;
  href: string;
  color: string;
}) {
  return (
    <Link href={href}
          className="block rounded-xl p-4 border transition-colors hover:bg-[var(--color-bg-elevated)]"
          style={{ background: "var(--color-bg-surface)", borderColor: "var(--color-border)" }}>
      <div className="flex items-start gap-3">
        <Icon size={16} strokeWidth={1.5} style={{ color, flexShrink: 0, marginTop: 1 }} />
        <div>
          <div className="text-sm font-medium text-[var(--color-text-primary)]">{title}</div>
          <div className="text-xs mt-0.5 text-[var(--color-text-muted)]">{content}</div>
        </div>
      </div>
    </Link>
  );
}
