"use client";

import { useState, useEffect } from "react";
import * as Tabs from "@radix-ui/react-tabs";
import { AlertTriangle, CheckCircle2, XCircle, Globe, Users, Building2, ChevronDown, ChevronUp } from "lucide-react";
import { useStock, usePriceHistory, useScoreHistory, useStockNews, useStockEarnings, usePiotroski, useSimilarStocks, useCompanyProfile, type SimilarStockItem, type CompanyProfile } from "@/hooks/useStock";
import { useMarketIntelShorts, useMarketIntelQmjRank, useMarketIntelClusters, useMarketIntelMasterTicker } from "@/hooks/useMarketIntel";
import { VerdictHeader } from "@/components/stock/VerdictHeader";
import { VerdictCard } from "@/components/stock/VerdictCard";
import { ExplainSection } from "@/components/stock/ExplainSection";
import { MicroLesson } from "@/components/ui/MicroLesson";
import { BeginnerCTA } from "@/components/stock/BeginnerCTA";
import { LevelSwitcher } from "@/components/stock/LevelSwitcher";
import { PriceChart } from "@/components/charts/PriceChart";
import { FactorRadar } from "@/components/charts/FactorRadar";
import { EarningsMemoCard } from "@/components/stock/EarningsMemoCard";
import { trackEvent, EVENT } from "@/lib/tracking";
import { useExperience, NonExpertOnly, ExpertOnly } from "@/components/providers/ExperienceProvider";
import dynamic from "next/dynamic";

const AnalysCommittee = dynamic(async () => {
  const mod = await import("@/components/stock/AnalysCommittee");
  return mod.AnalysCommittee;
}, {
  loading: () => <div className="skeleton h-48 rounded-xl" />,
});
import { cn } from "@/lib/utils";
import {
  formatPrice, formatNumber, formatPct, formatPctChange, formatMarketCap, scoreColorClass, formatScore, changeClass,
  signalClass, signalLabel, displayValue,
} from "@/lib/format";
import { InfoTooltip } from "@/components/ui/InfoTooltip";
import { AreaChart, Area, XAxis, Tooltip, ResponsiveContainer } from "recharts";
import type { ScanRow } from "@/types/scan";

// ── UI-ärlighet (T12) ────────────────────────────────────────────────────────
// Finansiella sektorer har strukturellt meningslös negativ bruttomarginal
// (premie-/ränteintäkter ≠ försäljning) → dölj negativ gm där, visa annars.
const FINANCIAL_SECTORS = ["Financial Services", "Real Estate", "Insurance"];

function isFinancialSector(sector: string | null | undefined): boolean {
  return sector != null && FINANCIAL_SECTORS.includes(sector);
}

function grossMarginValue(stock: ScanRow): string {
  const min = isFinancialSector(stock.sector) ? 0 : undefined;
  return displayValue(stock.gross_margin != null ? stock.gross_margin * 100 : null, { min, suffix: " %" });
}

interface Props {
  ticker: string;
}

export function StockView({ ticker }: Props) {
  const { data: stock, isLoading, error } = useStock(ticker);
  const { loading: levelLoading } = useExperience();
  const { level } = useExperience();

  useEffect(() => {
    if (stock?.ticker) {
      trackEvent(EVENT.STOCK_PAGE_VIEW, { ticker: stock.ticker });
    }
  }, [stock?.ticker]);

  // If experience level still loading, show skeleton
  if (levelLoading) {
    return <StockSkeleton />;
  }

  if (isLoading) return <StockSkeleton />;
  if (error || !stock) {
    return (
      <div className="flex flex-col items-center justify-center py-24 gap-3">
        <AlertTriangle size={24} className="text-[var(--color-warn)]" />
        <p className="text-sm text-[var(--color-text-secondary)]">
          Aktie {ticker} hittades inte
        </p>
      </div>
    );
  }

  return (
    <>
      {/* ── Non-expert (beginner + intermediate): data-first view ───── */}
      <NonExpertOnly>
        <div className="-mx-8 -mt-6">
          <div className="sticky top-0 z-30">
            {/* Simple headline instead of full VerdictHeader */}
            <div className="border-b px-6 py-4 bg-[var(--color-bg-surface)] border-[var(--color-border)]">
              <div className="flex items-start justify-between gap-4 flex-wrap">
                <div>
                  <div className="flex items-center gap-3">
                    <span className="text-lg font-bold text-[var(--color-text-primary)]">
                      {stock.name}
                    </span>
                    <span className="font-mono text-sm text-[var(--color-text-secondary)]">
                      {stock.ticker}
                    </span>
                  </div>
                </div>
                <div className="shrink-0 text-right">
                  <span className="font-mono tabular text-2xl font-bold text-[var(--color-text-primary)]">
                    {formatPrice(stock.price)}
                  </span>
                  {stock.change_pct != null && (
                    <div className={cn("font-mono tabular text-sm font-medium", changeClass(stock.change_pct))}>
                      {formatPctChange(stock.change_pct)} idag
                    </div>
                  )}
                </div>
              </div>

              {/* Signal badge + level switcher row */}
              <div className="mt-3 flex items-center justify-between gap-4 flex-wrap">
                <SignalBadgeInline signal={stock.entry_signal} />
                <LevelSwitcher />
              </div>

              {/* Market Intel-badges — villkorliga varningar */}
              <MarketIntelBadges ticker={ticker} />
            </div>

            {/* VerdictCard below the header — intermediate only (beginner finds it in the AI tab) */}
            {level === "intermediate" && (
              <div className="px-6 py-4 bg-[var(--color-bg-surface)]">
                <VerdictCard stock={stock} />
              </div>
            )}

            {/* Simplified tabs */}
            <Tabs.Root defaultValue="oversikt" className="bg-[var(--color-bg-surface)]">
              <Tabs.List className="flex border-b px-6 border-[var(--color-border)]" aria-label="Flikar">
                <Tabs.Trigger
                  value="oversikt"
                  className={cn(
                    "px-4 py-3 text-sm border-b-2 transition-colors -mb-px data-[state=inactive]:border-transparent",
                    "data-[state=active]:border-[var(--color-accent)] data-[state=active]:text-[var(--color-accent)]",
                    "data-[state=inactive]:text-[var(--color-text-muted)] data-[state=inactive]:hover:text-[var(--color-text-secondary)]",
                  )}
                >
                  Översikt
                </Tabs.Trigger>
                <Tabs.Trigger
                  value="rapporter"
                  className={cn(
                    "px-4 py-3 text-sm border-b-2 transition-colors -mb-px data-[state=inactive]:border-transparent",
                    "data-[state=active]:border-[var(--color-accent)] data-[state=active]:text-[var(--color-accent)]",
                    "data-[state=inactive]:text-[var(--color-text-muted)] data-[state=inactive]:hover:text-[var(--color-text-secondary)]",
                  )}
                >
                  Rapporter
                </Tabs.Trigger>
                <Tabs.Trigger
                  value="ai"
                  className={cn(
                    "px-4 py-3 text-sm border-b-2 transition-colors -mb-px data-[state=inactive]:border-transparent",
                    "data-[state=active]:border-[var(--color-accent)] data-[state=active]:text-[var(--color-accent)]",
                    "data-[state=inactive]:text-[var(--color-text-muted)] data-[state=inactive]:hover:text-[var(--color-text-secondary)]",
                  )}
                >
                  AI-analys
                </Tabs.Trigger>
              </Tabs.List>

              <div className="px-6 py-6">
                <Tabs.Content value="oversikt"><OverviewTab stock={stock} showBeginnerCTA={level === "beginner"} /></Tabs.Content>
                <Tabs.Content value="rapporter"><RapporterTab ticker={ticker} stock={stock} /></Tabs.Content>
                <Tabs.Content value="ai">
                  {level === "beginner" ? (
                    <div className="space-y-5">
                      <VerdictCard stock={stock} />
                      <ExplainSection ticker={stock.ticker} stock={stock} />
                    </div>
                  ) : (
                    <AITab stock={stock} />
                  )}
                </Tabs.Content>
              </div>
            </Tabs.Root>
          </div>
        </div>
      </NonExpertOnly>

      {/* ── Expert: current StockView EXACTLY as-is ────────────────── */}
      <ExpertOnly>
        <div className="-mx-8 -mt-6">
          {/* Sticky header block: VerdictHeader + tab bar as ONE sticky unit */}
          <div className="sticky top-0 z-30">
            <VerdictHeader stock={stock} />

            {/* Level switcher — slim row between header and tab bar */}
            <div className="px-6 py-2 border-b bg-[var(--color-bg-surface)] border-[var(--color-border)] flex items-center justify-between gap-4 flex-wrap">
              {/* Market Intel-badges — villkorliga varningar */}
              <MarketIntelBadges ticker={ticker} />
              <LevelSwitcher />
            </div>

            {/* Tab bar with Radix Tabs */}
            <Tabs.Root defaultValue="oversikt" className="bg-[var(--color-bg-surface)]">
              <Tabs.List className="flex border-b px-6 border-[var(--color-border)]" aria-label="Flikar">
                <Tabs.Trigger
                  value="oversikt"
                  className={cn(
                    "px-4 py-3 text-sm border-b-2 transition-colors -mb-px data-[state=inactive]:border-transparent",
                    "data-[state=active]:border-[var(--color-accent)] data-[state=active]:text-[var(--color-accent)]",
                    "data-[state=inactive]:text-[var(--color-text-muted)] data-[state=inactive]:hover:text-[var(--color-text-secondary)]",
                  )}
                >
                  Översikt
                </Tabs.Trigger>
                <Tabs.Trigger
                  value="faktorer"
                  className={cn(
                    "px-4 py-3 text-sm border-b-2 transition-colors -mb-px data-[state=inactive]:border-transparent",
                    "data-[state=active]:border-[var(--color-accent)] data-[state=active]:text-[var(--color-accent)]",
                    "data-[state=inactive]:text-[var(--color-text-muted)] data-[state=inactive]:hover:text-[var(--color-text-secondary)]",
                  )}
                >
                  Faktorer
                </Tabs.Trigger>
                <Tabs.Trigger
                  value="analys"
                  className={cn(
                    "px-4 py-3 text-sm border-b-2 transition-colors -mb-px data-[state=inactive]:border-transparent",
                    "data-[state=active]:border-[var(--color-accent)] data-[state=active]:text-[var(--color-accent)]",
                    "data-[state=inactive]:text-[var(--color-text-muted)] data-[state=inactive]:hover:text-[var(--color-text-secondary)]",
                  )}
                >
                  Analys
                </Tabs.Trigger>
                <Tabs.Trigger
                  value="rapporter"
                  className={cn(
                    "px-4 py-3 text-sm border-b-2 transition-colors -mb-px data-[state=inactive]:border-transparent",
                    "data-[state=active]:border-[var(--color-accent)] data-[state=active]:text-[var(--color-accent)]",
                    "data-[state=inactive]:text-[var(--color-text-muted)] data-[state=inactive]:hover:text-[var(--color-text-secondary)]",
                  )}
                >
                  Rapporter
                </Tabs.Trigger>
                <Tabs.Trigger
                  value="ai"
                  className={cn(
                    "px-4 py-3 text-sm border-b-2 transition-colors -mb-px data-[state=inactive]:border-transparent",
                    "data-[state=active]:border-[var(--color-accent)] data-[state=active]:text-[var(--color-accent)]",
                    "data-[state=inactive]:text-[var(--color-text-muted)] data-[state=inactive]:hover:text-[var(--color-text-secondary)]",
                  )}
                >
                  AI
                </Tabs.Trigger>
                <Tabs.Trigger
                  value="liknande"
                  className={cn(
                    "px-4 py-3 text-sm border-b-2 transition-colors -mb-px data-[state=inactive]:border-transparent",
                    "data-[state=active]:border-[var(--color-accent)] data-[state=active]:text-[var(--color-accent)]",
                    "data-[state=inactive]:text-[var(--color-text-muted)] data-[state=inactive]:hover:text-[var(--color-text-secondary)]",
                  )}
                >
                  Liknande
                </Tabs.Trigger>
              </Tabs.List>

              <div className="px-6 py-6">
                <Tabs.Content value="oversikt"><OverviewTab stock={stock} /></Tabs.Content>
                <Tabs.Content value="faktorer"><FaktorerTab stock={stock} ticker={ticker} /></Tabs.Content>
                <Tabs.Content value="analys"><AnalysTab ticker={ticker} /></Tabs.Content>
                <Tabs.Content value="rapporter"><RapporterTab ticker={ticker} stock={stock} /></Tabs.Content>
                <Tabs.Content value="ai"><AITab stock={stock} /></Tabs.Content>
                <Tabs.Content value="liknande"><LiknandeTab ticker={ticker} /></Tabs.Content>
              </div>
            </Tabs.Root>
          </div>
        </div>
      </ExpertOnly>
    </>
  );
}

// ─── Översikt ────────────────────────────────────────────────────────────────

function SignalBadgeInline({ signal }: { signal: string | null | undefined }) {
  if (!signal) return null;
  return (
    <span className={cn("px-2.5 py-1 rounded-md text-xs font-medium", signalClass(signal))}>
      {signalLabel(signal)}
    </span>
  );
}

// ─── Market Intel-badges ──────────────────────────────────────────────────────
// Villkorliga varningar från market-intel-endpoints. Saknas data → inget badge
// (aldrig "no data"-rummel). Endast tre möjliga: blankningsvarning,
// säljkluster-varning och exclusion-reason från kvalitetslistan.

function MarketIntelBadges({ ticker }: { ticker: string }) {
  const { data: shorts } = useMarketIntelShorts(ticker);
  const { data: clusters } = useMarketIntelClusters(ticker);
  const { data: qmjRank } = useMarketIntelQmjRank();

  const badges: { label: string; title?: string }[] = [];

  // Blankningsvarning: senaste total_short_pct ≥ 8 % eller ny FI-disclosure
  // (endpoint returnerar rader sorterade på scan_date DESC → rad 0 = senaste)
  const latestShort = shorts?.[0];
  if (latestShort && ((latestShort.total_short_pct ?? 0) >= 8 || latestShort.is_new_discovery)) {
    badges.push({
      label: "Blankningsvarning",
      title: latestShort.is_new_discovery
        ? "Ny blankningsposition registrerad hos FI"
        : `Kort position: ${latestShort.total_short_pct?.toFixed(1)} %`,
    });
  }

  // Säljkluster-varning: ≥ 3 unika säljare senaste 30 dagarna
  if (clusters && clusters.unique_sellers_30d >= 3) {
    badges.push({
      label: "Säljkluster-varning",
      title: `${clusters.unique_sellers_30d} unika säljare senaste 30 dagarna`,
    });
  }

  // Exclusion-reason från kvalitetslistan (om aktien finns där)
  const qmjEntry = qmjRank?.find((r) => r.ticker === ticker);
  if (qmjEntry?.exclusion_reason) {
    badges.push({
      label: "Exkluderad från kvalitetslista",
      title: qmjEntry.exclusion_reason,
    });
  }

  if (badges.length === 0) return null;

  return (
    <div className="flex flex-wrap items-center gap-1.5">
      {badges.map((b) => (
        <span
          key={b.label}
          title={b.title}
          className="flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-medium bg-[var(--color-warn-soft)] text-[var(--color-warn)]"
        >
          <AlertTriangle size={10} strokeWidth={2} />
          {b.label}
        </span>
      ))}
    </div>
  );
}

function OverviewTab({ stock, showBeginnerCTA = false }: { stock: ScanRow; showBeginnerCTA?: boolean }) {
  const { data: priceData, isLoading } = usePriceHistory(stock.ticker);
  const { data: profile } = useCompanyProfile(stock.ticker);

  return (
    <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
      {/* Price chart */}
      <div className="xl:col-span-2 rounded-xl p-4 border bg-[var(--color-bg-surface)] border-[var(--color-border)]">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-medium text-[var(--color-text-secondary)]">
            Prisutveckling
          </h3>
          {/* U-11: Synthetic data label — shown when real price data is unavailable */}
          {priceData?.is_synthetic && (
            <span className="px-2 py-0.5 rounded text-[10px] font-medium
                             bg-[var(--color-warn-soft)] text-[var(--color-warn)]">
              Exempeldata — verklig historik kopplas när R2 är konfigurerat
            </span>
          )}
        </div>
        {isLoading
          ? <div className="skeleton" style={{ height: 300 }} />
          : priceData?.candles?.length
          ? <PriceChart candles={priceData.candles as Parameters<typeof PriceChart>[0]["candles"]} />
          : <div className="h-[300px] flex items-center justify-center text-sm text-[var(--color-text-muted)]">
              Prishistorik ej tillgänglig
            </div>
        }
      </div>

      {/* Quick facts */}
      <div className="rounded-xl p-4 border bg-[var(--color-bg-surface)] border-[var(--color-border)]">
        <h3 className="text-sm font-medium mb-4 text-[var(--color-text-secondary)]">
          Nyckeltal
        </h3>
        <dl className="space-y-3">
          {[
            {
              label: "P/E (TTM)",
              value: displayValue(stock.pe_trailing, { min: 0 }),
              tip: "Pris/vinst-kvot (senaste 12 mån). Visar hur många kronor du betalar per krona vinst. Lågt P/E kan tyda på att aktien är billig, men beror också på bransch.",
              microTopic: "pe_trailing",
            },
            {
              label: "P/E (forward)",
              value: displayValue(stock.pe_forward, { min: 0 }),
              tip: "Pris/vinst-kvot baserad på analytikernas vinstprognos för kommande 12 månader. Ger en bild av vad marknaden förväntar sig.",
              microTopic: "pe_forward",
            },
            {
              label: "ROE",
              value: (() => { const v = stock.roe_raw ?? stock.roe; return v != null && v > 0.0005 ? formatPct(v) : "—" })(),
              tip: "Avkastning på eget kapital. Hur effektivt bolaget genererar vinst med ägarnas kapital. Över 15 % anses generellt bra.",
              microTopic: "roe",
            },
            {
              label: "ROA",
              value: stock.roa != null ? formatPct(stock.roa) : "—",
              tip: "Avkastning på totala tillgångar. Mäter hur effektivt bolaget använder sina tillgångar för att skapa vinst.",
            },
            {
              label: "Bruttomarginal",
              value: grossMarginValue(stock),
              tip: "Hur stor andel av intäkterna som blir kvar efter direkta produktionskostnader. Hög marginal = starkt prissättningsutrymme.",
            },
            {
              label: "Rörelsemarginal",
              value: stock.operating_margin != null ? formatPct(stock.operating_margin) : "—",
              tip: "Vinst efter alla driftkostnader, men före räntor och skatt. Visar hur lönsam kärnverksamheten är.",
            },
            {
              label: "Finansiell styrka",
              value: stock.piotroski_f != null ? `${stock.piotroski_f}/9` : "—",
              tip: "Piotroski F-score (0–9). Mäter bolagets finansiella hälsa utifrån lönsamhet, skuldsättning och operativ effektivitet. 7–9 = starkt, 0–2 = svagt.",
              microTopic: "piotroski",
            },
            {
              label: "Skuldsättning (D/E)",
              value: displayValue(stock.debt_to_equity, { min: 0 }),
              tip: "Räntebärande skulder delat med eget kapital. Visar hur mycket bolaget är finansierat med lån kontra eget kapital. Under 1,0 anses ofta konservativt.",
            },
            {
              label: "Direktavkastning",
              value: stock.dividend_yield != null ? formatPct(stock.dividend_yield) : "—",
              tip: "Årsutdelning delat med aktiekurs. Visar hur stor andel av din investering du får tillbaka i utdelning per år.",
            },
            {
              label: "Beta",
              value: stock.beta != null ? formatNumber(stock.beta, 2) : "—",
              tip: "Mäter aktiens rörlighet jämfört med marknadsindex. Beta > 1 = rör sig mer än index. Beta < 1 = stabilare. Beta = 1 = följer marknaden.",
            },
            {
              label: "Börsvärde",
              value: formatMarketCap(stock.market_cap),
              tip: "Aktiekursen multiplicerat med antalet aktier. Visar hur mycket hela bolaget värderas till på börsen.",
              microTopic: "market_cap",
            },
          ].map(({ label, value, tip, microTopic }) => (
            <div key={label} className="flex justify-between items-center">
              <dt className="flex items-center text-xs text-[var(--color-text-muted)]">
                {label}
                <InfoTooltip text={tip} side="left" />
                {microTopic && <MicroLesson topic={microTopic} />}
              </dt>
              <dd className="text-xs font-mono tabular text-[var(--color-text-primary)]">{value}</dd>
            </div>
          ))}
        </dl>
      </div>

      {/* Company profile card — shown when yfinance data is available */}
      {profile && (
        <div className="xl:col-span-3">
          <CompanyProfileCard profile={profile} currentPrice={stock.price} />
        </div>
      )}

      {/* Beginner CTA — soft close of the overview, only in beginner mode */}
      {showBeginnerCTA && (
        <div className="xl:col-span-3">
          <BeginnerCTA ticker={stock.ticker} />
        </div>
      )}

    </div>
  );
}

// ─── Company Profile Card ────────────────────────────────────────────────────

const DESCRIPTION_PREVIEW_LENGTH = 320;

function CompanyProfileCard({
  profile,
  currentPrice,
}: {
  profile: CompanyProfile;
  currentPrice: number | null | undefined;
}) {
  const [expanded, setExpanded] = useState(false);
  const desc = profile.description ?? "";
  const isTruncated = desc.length > DESCRIPTION_PREVIEW_LENGTH;
  const shownDesc = expanded || !isTruncated
    ? desc
    : desc.slice(0, DESCRIPTION_PREVIEW_LENGTH).trimEnd() + "…";

  // 52-week range bar
  const hi = profile.week_52_high;
  const lo = profile.week_52_low;
  const pct =
    hi && lo && hi > lo && currentPrice != null
      ? Math.max(0, Math.min(100, ((currentPrice - lo) / (hi - lo)) * 100))
      : null;

  return (
    <div className="rounded-xl p-5 border bg-[var(--color-bg-surface)] border-[var(--color-border)] space-y-4">
      {/* Header row */}
      <div className="flex items-center justify-between gap-3">
        <h3 className="text-sm font-medium text-[var(--color-text-secondary)]">
          Om bolaget
        </h3>
        <div className="flex items-center gap-3 text-xs text-[var(--color-text-muted)]">
          {profile.industry && (
            <span className="flex items-center gap-1">
              <Building2 size={11} />
              {profile.industry}
            </span>
          )}
          {profile.country && (
            <span className="flex items-center gap-1">
              <Globe size={11} />
              {profile.country}
            </span>
          )}
          {profile.employees != null && (
            <span className="flex items-center gap-1">
              <Users size={11} />
              {profile.employees.toLocaleString("sv-SE")} anst.
            </span>
          )}
          {profile.website && (
            <a
              href={profile.website.startsWith("http") ? profile.website : `https://${profile.website}`}
              target="_blank"
              rel="noopener noreferrer"
              className="text-[var(--color-accent)] hover:underline truncate max-w-[140px]"
              onClick={(e) => e.stopPropagation()}
            >
              {profile.website.replace(/^https?:\/\/(www\.)?/, "")}
            </a>
          )}
        </div>
      </div>

      {/* Description */}
      {desc && (
        <div>
          <p className="text-sm text-[var(--color-text-primary)] leading-relaxed">
            {shownDesc}
          </p>
          {isTruncated && (
            <button
              onClick={() => setExpanded((v) => !v)}
              className="mt-2 flex items-center gap-1 text-xs text-[var(--color-accent)] hover:underline"
            >
              {expanded ? (
                <>Visa mindre <ChevronUp size={12} /></>
              ) : (
                <>Visa mer <ChevronDown size={12} /></>
              )}
            </button>
          )}
        </div>
      )}

      {/* 52-week range + meta grid */}
      {(hi != null || lo != null || profile.beta != null) && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2 border-t border-[var(--color-border)]">
          {/* 52-week range bar */}
          {hi != null && lo != null && (
            <div>
              <div className="flex justify-between text-[10px] text-[var(--color-text-muted)] mb-1">
                <span>52v låg: {lo.toFixed(2)}</span>
                <span>52v hög: {hi.toFixed(2)}</span>
              </div>
              <div className="relative h-2 rounded-full bg-[var(--color-bg-elevated)] overflow-visible">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-[var(--color-down)] via-[var(--color-warn)] to-[var(--color-up)]"
                  style={{ width: "100%" }}
                />
                {pct != null && (
                  <div
                    className="absolute top-1/2 -translate-y-1/2 w-3 h-3 rounded-full border-2 bg-white border-[var(--color-accent)] shadow"
                    style={{ left: `calc(${pct}% - 6px)` }}
                  />
                )}
              </div>
              {currentPrice != null && (
                <div className="text-center text-[10px] text-[var(--color-text-muted)] mt-1">
                  Nuvarande: {currentPrice.toFixed(2)}
                </div>
              )}
            </div>
          )}

          {/* Beta + updated_at */}
          <div className="flex items-start gap-6 text-xs">
            {profile.beta != null && (
              <div>
                <div className="text-[var(--color-text-muted)] mb-0.5 flex items-center gap-1">
                  Beta
                  <InfoTooltip text="Mäter aktiens rörlighet mot S&P 500. Beta > 1 rör sig mer än marknaden." side="top" />
                </div>
                <div className="font-mono font-semibold text-[var(--color-text-primary)]">
                  {profile.beta.toFixed(2)}
                </div>
              </div>
            )}
            {profile.updated_at && (
              <div className="text-[var(--color-text-muted)] text-[10px] self-end ml-auto">
                Uppdaterad: {profile.updated_at.slice(0, 10)}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Faktorer ────────────────────────────────────────────────────────────────

const FACTOR_DESCS: Record<string, string> = {
  score_value:     "Värderingsbetyg baserat på P/E, P/B, EV/EBITDA.",
  score_quality:   "Kvalitetsbetyg baserat på ROE, marginaler, Piotroski.",
  score_momentum:  "Momentumbetyg baserat på kursutveckling 6-12 mån.",
  score_growth:    "Tillväxtbetyg baserat på intäkts- och vinsttillväxt.",
  score_risk:      "Riskbetyg baserat på beta, volatilitet, skuldsättning.",
  score_size:      "Storlekspremium och marknadskapitalisering",
  score_dividend:  "Direktavkastning, utdelningshistorik och hållbarhet",
  score_sentiment: "Nyhetssentiment, analytikerkonsensus och marknadsregim",
};

function FaktorerTab({ stock, ticker }: { stock: ScanRow; ticker: string }) {
  const [showDetails, setShowDetails] = useState(false);
  const { data: master } = useMarketIntelMasterTicker(ticker);

  return (
    <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
      {/* Radar */}
      <div className="rounded-xl p-4 border bg-[var(--color-bg-surface)] border-[var(--color-border)]">
        <h3 className="text-sm font-medium mb-2 text-[var(--color-text-secondary)]">FaktorÃ¶versikt</h3>
        <FactorRadar stock={stock} />
        <div className="mt-3 text-center">
          <button
            onClick={() => setShowDetails(!showDetails)}
            className="text-xs text-[var(--color-accent)] hover:underline"
          >
            {showDetails ? "DÃ¶lj detaljer" : "Detaljer"}
          </button>
        </div>
        {showDetails && (
          <div className="mt-4 space-y-3 pt-3 border-t border-[var(--color-border)]">
            {Object.entries(FACTOR_DESCS).map(([key, desc]) => {
              const score = stock[key as keyof ScanRow] as number | null;
              const niceName = key.replace("score_", "");
              const displayName = niceName.charAt(0).toUpperCase() + niceName.slice(1);
              return (
                <div key={key}>
                  <div className="flex justify-between items-center mb-1">
                    <span className="flex items-center text-xs text-[var(--color-text-primary)]">
                      {displayName}
                      <InfoTooltip text={desc} side="right" />
                    </span>
                    <span className={cn("font-mono text-xs font-semibold tabular", scoreColorClass(score))}>
                      {score != null ? Math.round(score) : "â€”"}
                    </span>
                  </div>
                  <div className="h-1.5 rounded-full overflow-hidden bg-[var(--color-bg-elevated)]">
                    <div
                      className="h-full rounded-full transition-all"
                      style={{
                        width: `${score ?? 0}%`,
                        background: (score ?? 0) >= 70
                          ? "var(--color-score-high)"
                          : (score ?? 0) >= 50
                          ? "var(--color-score-mid)"
                          : "var(--color-score-low)",
                      }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* MasterRank (ROND 8) — kort: varför rankas denna aktie så? */}
      <div className="rounded-xl p-4 border bg-[var(--color-bg-surface)] border-[var(--color-border)]">
        <h3 className="text-sm font-medium mb-2 text-[var(--color-text-secondary)]">MasterRank</h3>
        {master ? (
          <div className="space-y-2">
            <div className="flex items-baseline gap-2">
              <span className={cn("text-2xl font-bold tabular", scoreColorClass(master.master_rank))}>
                {master.master_rank != null ? Math.round(master.master_rank) : "—"}
              </span>
              <span className="text-xs text-[var(--color-text-muted)]">
                {master.tier ?? ""} · PIT: {master.pit_status ?? "—"}
              </span>
            </div>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div className="rounded-lg p-2 bg-[var(--color-bg-elevated)]">
                <div className="text-[var(--color-text-muted)]">Värdering vs historik</div>
                <div className="font-semibold tabular">{master.val_hist_z != null ? Math.round(master.val_hist_z) : "—"}</div>
              </div>
              <div className="rounded-lg p-2 bg-[var(--color-bg-elevated)]">
                <div className="text-[var(--color-text-muted)]">Analytikeruppsida</div>
                <div className="font-semibold">
                  {master.analyst_upside != null
                    ? `${master.analyst_upside > 0 ? "+" : ""}${master.analyst_upside.toFixed(1)}%`
                    : "—"}
                </div>
              </div>
              <div className="rounded-lg p-2 bg-[var(--color-bg-elevated)]">
                <div className="text-[var(--color-text-muted)]">RSI 14</div>
                <div className="font-semibold tabular">{master.rsi_14 != null ? Math.round(master.rsi_14) : "—"}</div>
              </div>
              <div className="rounded-lg p-2 bg-[var(--color-bg-elevated)]">
                <div className="text-[var(--color-text-muted)]">Nästa katalysator</div>
                <div className="font-semibold">{master.catalyst_days != null ? `om ${master.catalyst_days} d` : "—"}</div>
              </div>
            </div>
            {master.val_flags?.includes("EXTREME_OVERVAL") && master.tech_flags?.includes("OVERBOUGHT") && (
              <div className="flex items-center gap-1 text-[10px] font-medium px-2 py-1 rounded bg-[var(--color-warn-soft)] text-[var(--color-warn)]">
                <AlertTriangle size={10} /> Bubbla-triage: starkt bolag, priset har sprungit ikapp nyheterna
              </div>
            )}
          </div>
        ) : (
          <p className="text-xs text-[var(--color-text-muted)]">MasterRank ej tillgänglig ännu (uppdateras fredags)</p>
        )}
      </div>
    </div>
  );
}

// ─── Analys ─────────────────────────────────────────────────────────────────

function AnalysTab({ ticker }: { ticker: string }) {
  const { data, isLoading } = useScoreHistory(ticker);
  const { data: piotroskiData, isLoading: piotroskiLoading } = usePiotroski(ticker);

  return (
    <div className="space-y-6">
      <div className="rounded-xl p-4 border bg-[var(--color-bg-surface)] border-[var(--color-border)]">
        <h3 className="text-sm font-medium mb-4 text-[var(--color-text-secondary)]">Betygstrend (veckovis)</h3>
        {isLoading
          ? <div className="skeleton h-40 rounded-lg" />
          : data?.history?.length
          ? <ScoreHistoryChart history={data.history} />
          : <p className="text-sm text-[var(--color-text-muted)] text-center py-8">
              Betygstrend ej tillgänglig (kräver historikdata i R2)
            </p>
        }
      </div>

      <div className="rounded-xl p-4 border bg-[var(--color-bg-surface)] border-[var(--color-border)]">
        <h3 className="text-sm font-medium mb-4 text-[var(--color-text-secondary)]">
          Piotroski F-Score: {piotroskiData ? `${piotroskiData.total_score}/9` : "—"}
        </h3>
        {piotroskiLoading ? (
          <div className="skeleton h-48 rounded-lg" />
        ) : piotroskiData?.criteria?.length ? (
          <div className="space-y-2">
            {piotroskiData.criteria.map((c, i) => (
              <div
                key={i}
                className="flex items-start gap-3 rounded-lg p-3 border border-[var(--color-border)] bg-[var(--color-bg-elevated)] group relative"
              >
                {c.passed ? (
                  <CheckCircle2 size={18} className="shrink-0 mt-0.5 text-[var(--color-up)]" />
                ) : (
                  <XCircle size={18} className="shrink-0 mt-0.5 text-[var(--color-down)]" />
                )}
                <div className="flex-1 min-w-0">
                  <span className={cn(
                    "text-sm font-medium",
                    c.passed ? "text-[var(--color-text-primary)]" : "text-[var(--color-text-muted)]",
                  )}>
                    {c.name}
                  </span>
                  <div className="text-xs text-[var(--color-text-muted)] mt-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
                    {c.explanation}
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-[var(--color-text-muted)] text-center py-8">
            Piotroski-data ej tillgänglig
          </p>
        )}
      </div>
    </div>
  );
}

function ScoreHistoryChart({ history }: { history: { date: string; score: number; signal: string }[] }) {
  const data = history.map((h) => ({
    date: h.date.slice(0, 7), // YYYY-MM
    score: Math.round(h.score),
    signal: h.signal,
  }));

  return (
    <div style={{ height: 160 }}>
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 4, right: 4, bottom: 0, left: -20 }}>
          <defs>
            <linearGradient id="scoreGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="var(--color-accent)" stopOpacity={0.15} />
              <stop offset="95%" stopColor="var(--color-accent)" stopOpacity={0} />
            </linearGradient>
          </defs>
          <XAxis
            dataKey="date"
            tick={{ fontSize: 10, fill: "var(--color-text-muted)" }}
            tickLine={false}
            axisLine={false}
            interval="preserveStartEnd"
          />
          <Tooltip
            content={({ active, payload }: { active?: boolean; payload?: Array<{ value?: number; payload?: { date: string } }> }) => {
              if (!active || !payload?.length) return null;
              return (
                <div className="px-2 py-1.5 rounded-lg text-xs shadow-md bg-[var(--color-bg-surface)] text-[var(--color-text-primary)]"
                     style={{ border: "1px solid var(--color-border-strong)" }}>
                  <span className="font-semibold">{payload[0].value}</span>
                  <span className="ml-1 text-[var(--color-text-muted)]">{payload[0].payload?.date}</span>
                </div>
              );
            }}
          />
          <Area
            type="monotone"
            dataKey="score"
            stroke="var(--color-accent)"
            strokeWidth={2}
            fill="url(#scoreGrad)"
            dot={false}
            activeDot={{ r: 3, strokeWidth: 0, fill: "var(--color-accent)" }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

// ─── Rapporter ───────────────────────────────────────────────────────────────

function RapporterTab({ ticker, stock }: { ticker: string; stock: ScanRow }) {
  const { data: earningsData, isLoading: earningsLoading } = useStockEarnings(ticker);
  const { data: newsData, isLoading: newsLoading } = useStockNews(ticker);
  const earnings = earningsData?.earnings ?? [];
  const news = newsData?.news ?? [];
  const [showAllNews, setShowAllNews] = useState(false);
  const newsLimit = 3;
  const visibleNews = showAllNews ? news : news.slice(0, newsLimit);

  return (
    <div className="space-y-5">
      {/* Earnings history */}
      <div className="rounded-xl border p-5 bg-[var(--color-bg-surface)] border-[var(--color-border)]">
        <h3 className="text-sm font-semibold mb-4 text-[var(--color-text-primary)]">
          Kvartalsrapporter
        </h3>
        {earningsLoading ? (
          <div className="skeleton h-32 rounded-lg" />
        ) : earnings.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-[var(--color-text-muted)] border-b border-[var(--color-border)]">
                  <th className="text-left py-2 pr-4 font-medium">Period</th>
                  <th className="text-right py-2 pr-4 font-medium">EPS (rapport)</th>
                  <th className="text-right py-2 pr-4 font-medium">EPS (estimat)</th>
                  <th className="text-right py-2 pr-4 font-medium">Överraskning</th>
                  <th className="text-right py-2 font-medium">Intäkt (M$)</th>
                </tr>
              </thead>
              <tbody>
                {earnings.slice(0, 8).map((e, i: number) => {
                  const surprise = e.actual != null && e.estimate ? ((e.actual - e.estimate) / Math.abs(e.estimate) * 100).toFixed(1) : null;
                  return (
                    <tr key={i} className="border-b border-[var(--color-border)] hover:bg-[var(--color-bg-elevated)]">
                      <td className="py-2 pr-4 text-[var(--color-text-primary)]">{e.quarter} {e.year}</td>
                      <td className={cn("text-right py-2 pr-4 font-mono tabular", (e.actual ?? 0) >= 0 ? "text-[var(--color-up)]" : "text-[var(--color-down)]")}>
                        {e.actual?.toFixed(2) ?? "—"}
                      </td>
                      <td className="text-right py-2 pr-4 font-mono tabular text-[var(--color-text-muted)]">
                        {e.estimate?.toFixed(2) ?? "—"}
                      </td>
                      <td className={cn("text-right py-2 pr-4 font-mono tabular", surprise && parseFloat(surprise) > 0 ? "text-[var(--color-up)]" : "text-[var(--color-down)]")}>
                        {surprise ? `${surprise}%` : "—"}
                      </td>
                      <td className="text-right py-2 font-mono tabular text-[var(--color-text-muted)]">
                        {e.revenue ? (e.revenue / 1_000_000).toFixed(0) : "—"}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-sm text-[var(--color-text-muted)] text-center py-6">
            Inga rapportdata tillgängliga från Finnhub
          </p>
        )}
      </div>

      {/* Growth data from latest report */}
      {(stock.revenue_growth != null || stock.earnings_growth != null) && (
        <div className="rounded-xl border p-5 bg-[var(--color-bg-surface)] border-[var(--color-border)]">
          <h3 className="text-sm font-semibold mb-4 text-[var(--color-text-primary)]">
            Tillväxt (senaste rapporten)
          </h3>
          <div className="grid grid-cols-2 gap-4">
            {stock.revenue_growth != null && (
              <div>
                <div className="flex items-center text-xs mb-1 text-[var(--color-text-muted)]">
                  Intäktstillväxt (YoY)
                  <InfoTooltip text="Hur mycket bolagets intäkter vuxit jämfört med samma period förra året." />
                </div>
                <div className={cn("text-lg font-bold tabular",
                                   stock.revenue_growth >= 0 ? "text-[var(--color-up)]" : "text-[var(--color-down)]")}>
                  {stock.revenue_growth >= 0 ? "+" : ""}{(stock.revenue_growth * 100).toFixed(1)} %
                </div>
              </div>
            )}
            {stock.earnings_growth != null && (
              <div>
                <div className="flex items-center text-xs mb-1 text-[var(--color-text-muted)]">
                  Vinsttillväxt (YoY)
                  <InfoTooltip text="Hur mycket bolagets vinst per aktie (EPS) vuxit jämfört med samma period förra året." />
                </div>
                <div className={cn("text-lg font-bold tabular",
                                   stock.earnings_growth >= 0 ? "text-[var(--color-up)]" : "text-[var(--color-down)]")}>
                  {stock.earnings_growth >= 0 ? "+" : ""}{(stock.earnings_growth * 100).toFixed(1)} %
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* News */}
      <div className="rounded-xl border p-5 bg-[var(--color-bg-surface)] border-[var(--color-border)]">
        <div className="flex items-center justify-between gap-3 mb-4">
          <h3 className="text-sm font-semibold text-[var(--color-text-primary)]">
            Nyheter
          </h3>
          {/* Nyhetsbäring (T12) — framåtriktad: fältet kan saknas i äldre API-svar */}
          {stock.news_bias != null && (stock.news_bias < -0.15 || stock.news_bias > 0.15) && (
            <span className={cn(
              "shrink-0 text-[10px] font-medium px-2 py-0.5 rounded",
              stock.news_bias < -0.15
                ? "bg-[var(--color-down-soft)] text-[var(--color-down)]"
                : "bg-[var(--color-up-soft)] text-[var(--color-up)]",
            )}>
              Nyhetsvinkel: {stock.news_bias < -0.15 ? "negativ" : "positiv"}
              {stock.news_bias_n != null ? ` (${stock.news_bias_n} artiklar)` : ""}
            </span>
          )}
        </div>
        {newsLoading ? (
          <div className="skeleton h-40 rounded-lg" />
        ) : news.length > 0 ? (
          <div className="space-y-3 max-h-[400px] overflow-y-auto">
            {visibleNews.map((item, i) => (
              <a
                key={i}
                href={item.url ?? "#"}
                target="_blank"
                rel="noopener noreferrer"
                className="block rounded-lg p-3 border border-[var(--color-border)] hover:bg-[var(--color-bg-elevated)] transition-colors"
              >
                <div className="flex justify-between items-start gap-3">
                  <p className="text-sm font-medium text-[var(--color-text-primary)] leading-snug">
                    {item.headline}
                  </p>
                  {item.sentiment && (
                    <span className={cn(
                      "shrink-0 text-[10px] font-medium px-1.5 py-0.5 rounded",
                      item.sentiment === "positive" ? "bg-[var(--color-up-soft)] text-[var(--color-up)]" :
                      item.sentiment === "negative" ? "bg-[var(--color-down-soft)] text-[var(--color-down)]" :
                      "bg-[var(--color-bg-elevated)] text-[var(--color-text-muted)]",
                    )}>
                      {item.sentiment === "positive" ? "Positiv" : item.sentiment === "negative" ? "Negativ" : "Neutral"}
                    </span>
                  )}
                </div>
                <p className="text-xs text-[var(--color-text-muted)] mt-1 line-clamp-2">{item.summary}</p>
                <div className="flex items-center gap-2 mt-1.5">
                  <span className="text-[10px] text-[var(--color-text-muted)]">{item.source}</span>
                  {item.date && <span className="text-[10px] text-[var(--color-text-muted)]">{item.date}</span>}
                </div>
              </a>
            ))}
            {!showAllNews && news.length > newsLimit && (
              <button
                onClick={() => setShowAllNews(true)}
                className="w-full py-2 text-xs font-medium text-[var(--color-accent)] hover:underline transition-colors"
              >
                Visa alla {news.length} nyheter
              </button>
            )}
          </div>
        ) : (
          <p className="text-sm text-[var(--color-text-muted)] text-center py-6">
            Inga nyheter tillgängliga
          </p>
        )}
      </div>

      {/* Key ratios */}
      <div className="rounded-xl border p-5 bg-[var(--color-bg-surface)] border-[var(--color-border)]">
        <h3 className="text-sm font-semibold mb-4 text-[var(--color-text-primary)]">
          Nyckeltal från senaste rapporten
        </h3>
        <dl className="grid grid-cols-2 gap-x-8 gap-y-3">
          {[
            { label: "Bruttomarginal", value: grossMarginValue(stock), tip: "Hur stor andel av intäkterna som kvarstår efter direkta produktionskostnader." },
            { label: "Rörelsemarginal", value: stock.operating_margin != null ? `${(stock.operating_margin * 100).toFixed(1)} %` : "—", tip: "Vinst som andel av intäkterna, efter driftkostnader men före räntor och skatt." },
            { label: "ROE", value: (() => { const v = stock.roe_raw ?? stock.roe; return v != null && v > 0.0005 ? `${(v * 100).toFixed(1)} %` : "—" })(), tip: "Avkastning på eget kapital — hur effektivt bolaget skapar värde för aktieägarna." },
            { label: "Skuldsättning (D/E)", value: displayValue(stock.debt_to_equity, { min: 0 }), tip: "Skulder relativt eget kapital. Under 1,0 är konservativt." },
            { label: "Finansiell styrka", value: stock.piotroski_f != null ? `${stock.piotroski_f}/9` : "—", tip: "Piotroski F-score: summerar 9 finansiella hälsokontroller. 7–9 är starkt." },
            { label: "Direktavkastning", value: stock.dividend_yield != null ? `${(stock.dividend_yield * 100).toFixed(2)} %` : "—", tip: "Årsutdelning delat med aktiekurs." },
          ].map(({ label, value, tip }) => (
            <div key={label}>
              <dt className="flex items-center text-xs text-[var(--color-text-muted)]">
                {label} <InfoTooltip text={tip} />
              </dt>
              <dd className="text-sm font-semibold mt-0.5 tabular text-[var(--color-text-primary)]">
                {value}
              </dd>
            </div>
          ))}
        </dl>
      </div>
    </div>
  );
}

// ─── AI ─────────────────────────────────────────────────────────────────────

function AITab({ stock }: { stock: ScanRow }) {
  return (
    <div className="space-y-4">
      <ExplainSection ticker={stock.ticker} stock={stock} />
      <EarningsMemoCard ticker={stock.ticker} />
      <div>
        <AnalysCommittee stock={stock} />
      </div>
    </div>
  );
}

// ─── Liknande ────────────────────────────────────────────────────────────────

function LiknandeTab({ ticker }: { ticker: string }) {
  const { data, isLoading, error } = useSimilarStocks(ticker);

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        {Array.from({ length: 8 }).map((_, i) => (
          <div key={i} className="skeleton h-44 rounded-xl" />
        ))}
      </div>
    );
  }

  if (error || !data?.similar?.length) {
    return (
      <div className="flex flex-col items-center justify-center py-16 gap-3">
        <p className="text-sm text-[var(--color-text-muted)]">
          Inga liknande aktier hittades för {ticker}
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <p className="text-xs text-[var(--color-text-muted)]">
        {data.similar.length} aktier med liknande faktorsignatur — baserat på 8 faktorpoäng via cosinus-likhet
      </p>
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        {data.similar.map((item) => (
          <SimilarStockCard key={item.ticker} item={item} />
        ))}
      </div>
    </div>
  );
}

const SIGNAL_COLORS: Record<string, string> = {
  STARK:      "bg-[var(--color-up-soft)] text-[var(--color-up)]",
  OK:         "bg-[var(--color-accent-soft)] text-[var(--color-accent)]",
  VÄNTA:      "bg-[var(--color-warn-soft)] text-[var(--color-warn)]",
  EJ_AKTUELL: "bg-[var(--color-bg-elevated)] text-[var(--color-text-muted)]",
};
const SIGNAL_LABELS: Record<string, string> = {
  STARK:      "Stark",
  OK:         "OK",
  VÄNTA:      "Avvakta",
  EJ_AKTUELL: "Ej aktuell",
};

function SimilarStockCard({ item }: { item: SimilarStockItem }) {
  const signal = item.entry_signal ?? "EJ_AKTUELL";
  const colorClass = SIGNAL_COLORS[signal] ?? SIGNAL_COLORS["EJ_AKTUELL"];
  const label = SIGNAL_LABELS[signal] ?? signal;

  return (
    <a
      href={`/aktie/${item.ticker}`}
      className="group block rounded-xl border p-4 bg-[var(--color-bg-surface)] border-[var(--color-border)] hover:border-[var(--color-accent)] hover:bg-[var(--color-bg-elevated)] transition-colors"
    >
      {/* Header: ticker + similarity score */}
      <div className="flex items-start justify-between gap-2 mb-3">
        <div className="min-w-0">
          <div className="font-semibold text-sm text-[var(--color-text-primary)] truncate group-hover:text-[var(--color-accent)] transition-colors">
            {item.ticker}
          </div>
          {item.name && (
            <div className="text-xs text-[var(--color-text-muted)] truncate mt-0.5">
              {item.name}
            </div>
          )}
        </div>
        <div className="shrink-0 text-right">
          <div className="text-sm font-bold tabular text-[var(--color-accent)]">
            {item.similarity_pct.toFixed(0)}%
          </div>
          <div className="text-[10px] text-[var(--color-text-muted)]">likhet</div>
        </div>
      </div>

      {/* Score + sector */}
      <div className="flex items-center gap-2 mb-3 min-w-0">
        {item.score_total != null && (
          <span className={cn("text-xs font-bold tabular shrink-0", scoreColorClass(item.score_total))}>
            {formatScore(item.score_total)}/100
          </span>
        )}
        {item.sector && (
          <span className="text-[10px] px-1.5 py-0.5 rounded bg-[var(--color-bg-elevated)] text-[var(--color-text-muted)] truncate">
            {item.sector}
          </span>
        )}
      </div>

      {/* Price + daily change */}
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-mono tabular text-[var(--color-text-primary)]">
          {item.price != null ? formatPrice(item.price) : "—"}
        </span>
        {item.change_pct != null && (
          <span className={cn(
            "text-xs font-mono tabular",
            item.change_pct >= 0 ? "text-[var(--color-up)]" : "text-[var(--color-down)]",
          )}>
            {item.change_pct >= 0 ? "+" : ""}{item.change_pct.toFixed(2)}%
          </span>
        )}
      </div>

      {/* Signal badge + AI-top badge */}
      <div className="flex items-center gap-1.5 flex-wrap">
        <span className={cn("text-[10px] font-medium px-1.5 py-0.5 rounded", colorClass)}>
          {label}
        </span>
        {item.ml_rank != null && item.ml_rank >= 90 && (
          <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-[var(--color-accent-soft)] text-[var(--color-accent)]">
            AI top
          </span>
        )}
      </div>
    </a>
  );
}

// ─── Skeleton ────────────────────────────────────────────────────────────────

function StockSkeleton() {
  return (
    <div className="-mx-8 -mt-6 space-y-0">
      <div className="h-24 skeleton" style={{ borderRadius: 0 }} />
      <div className="h-12 skeleton" style={{ borderRadius: 0 }} />
      <div className="p-6 space-y-4">
        <div className="skeleton h-64 rounded-xl" />
        <div className="grid grid-cols-3 gap-4">
          {[1,2,3].map(i => <div key={i} className="skeleton h-24 rounded-xl" />)}
        </div>
      </div>
    </div>
  );
}
