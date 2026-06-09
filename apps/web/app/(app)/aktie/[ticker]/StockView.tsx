"use client";

import { useState } from "react";
import * as Tabs from "@radix-ui/react-tabs";
import { AlertTriangle, CheckCircle2, XCircle, Globe, Users, Building2, ChevronDown, ChevronUp } from "lucide-react";
import { useStock, usePriceHistory, useScoreHistory, useStockNews, useStockEarnings, usePiotroski, useSimilarStocks, useCompanyProfile, type SimilarStockItem, type CompanyProfile } from "@/hooks/useStock";
import { VerdictHeader } from "@/components/stock/VerdictHeader";
import { PriceChart } from "@/components/charts/PriceChart";
import { FactorRadar } from "@/components/charts/FactorRadar";
import dynamic from "next/dynamic";

const AnalysCommittee = dynamic(async () => {
  const mod = await import("@/components/stock/AnalysCommittee");
  return mod.AnalysCommittee;
}, {
  loading: () => <div className="skeleton h-48 rounded-xl" />,
});
import { cn } from "@/lib/utils";
import {
  formatPrice, formatNumber, formatPct, formatMarketCap, scoreColorClass, formatScore,
} from "@/lib/format";
import { InfoTooltip } from "@/components/ui/InfoTooltip";
import { AreaChart, Area, XAxis, Tooltip, ResponsiveContainer } from "recharts";
import type { ScanRow } from "@/types/scan";

interface Props {
  ticker: string;
}

export function StockView({ ticker }: Props) {
  const { data: stock, isLoading, error } = useStock(ticker);

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
    <div className="-mx-8 -mt-6">
      {/* Sticky header block: VerdictHeader + tab bar as ONE sticky unit */}
      <div className="sticky top-0 z-30">
        <VerdictHeader stock={stock} />

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
            <Tabs.Content value="faktorer"><FaktorerTab stock={stock} /></Tabs.Content>
            <Tabs.Content value="analys"><AnalysTab ticker={ticker} /></Tabs.Content>
            <Tabs.Content value="rapporter"><RapporterTab ticker={ticker} stock={stock} /></Tabs.Content>
            <Tabs.Content value="ai"><AITab stock={stock} /></Tabs.Content>
            <Tabs.Content value="liknande"><LiknandeTab ticker={ticker} /></Tabs.Content>
          </div>
        </Tabs.Root>
      </div>
    </div>
  );
}

// ─── Översikt ────────────────────────────────────────────────────────────────

function OverviewTab({ stock }: { stock: ScanRow }) {
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
              value: stock.pe_trailing != null ? formatNumber(stock.pe_trailing, 1) : "—",
              tip: "Pris/vinst-kvot (senaste 12 mån). Visar hur många kronor du betalar per krona vinst. Lågt P/E kan tyda på att aktien är billig, men beror också på bransch.",
            },
            {
              label: "P/E (forward)",
              value: stock.pe_forward != null ? formatNumber(stock.pe_forward, 1) : "—",
              tip: "Pris/vinst-kvot baserad på analytikernas vinstprognos för kommande 12 månader. Ger en bild av vad marknaden förväntar sig.",
            },
            {
              label: "ROE",
              value: stock.roe != null ? formatPct(stock.roe) : "—",
              tip: "Avkastning på eget kapital. Hur effektivt bolaget genererar vinst med ägarnas kapital. Över 15 % anses generellt bra.",
            },
            {
              label: "ROA",
              value: stock.roa != null ? formatPct(stock.roa) : "—",
              tip: "Avkastning på totala tillgångar. Mäter hur effektivt bolaget använder sina tillgångar för att skapa vinst.",
            },
            {
              label: "Bruttomarginal",
              value: stock.gross_margin != null ? formatPct(stock.gross_margin) : "—",
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
            },
            {
              label: "Skuldsättning (D/E)",
              value: stock.debt_to_equity != null ? formatNumber(stock.debt_to_equity, 2) : "—",
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
            },
          ].map(({ label, value, tip }) => (
            <div key={label} className="flex justify-between items-center">
              <dt className="flex items-center text-xs text-[var(--color-text-muted)]">
                {label}
                <InfoTooltip text={tip} side="left" />
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

      {/* Sammanfattning (U-10: döpte om från "AI-sammanfattning" — detta är en mall, inte AI) */}
      {stock.score_total != null && (
        <div className="xl:col-span-3 rounded-xl p-4 border bg-[var(--color-bg-surface)] border-[var(--color-border)]">
          <p className="text-sm text-[var(--color-text-secondary)] leading-relaxed">
            <strong className={scoreColorClass(stock.score_total)}>
              {stock.name}
            </strong>{" "}
            har ett Totalbetyg på{" "}
            <strong className={scoreColorClass(stock.score_total)}>
              {formatScore(stock.score_total)}/100
            </strong>
            {stock.entry_signal === "STARK" && " och befinner sig i ett starkt köpläge"}
            {stock.entry_signal === "OK" && " och befinner sig i ett bra läge"}
            {stock.entry_signal === "VÄNTA" && " — systemet rekommenderar att avvakta"}
            {". "}
            {stock.trend_signal === "Upptrend" && "Aktien är i upptrend. "}
            {stock.trend_signal === "Nedtrend" && "Aktien är i nedtrend. "}
            {stock.piotroski_f != null && `Finansiell styrka (Piotroski F): ${stock.piotroski_f}/9. `}
            {stock.predicted_return != null &&
              `AI-prognos 30 dagar: ${stock.predicted_return > 0 ? "+" : ""}${(stock.predicted_return*100).toFixed(1)}%.`}
          </p>
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

function FaktorerTab({ stock }: { stock: ScanRow }) {
  const [showDetails, setShowDetails] = useState(false);

  return (
    <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
      {/* Radar */}
      <div className="rounded-xl p-4 border bg-[var(--color-bg-surface)] border-[var(--color-border)]">
        <h3 className="text-sm font-medium mb-2 text-[var(--color-text-secondary)]">Faktoröversikt</h3>
        <FactorRadar stock={stock} />
        <div className="mt-3 text-center">
          <button
            onClick={() => setShowDetails(!showDetails)}
            className="text-xs text-[var(--color-accent)] hover:underline"
          >
            {showDetails ? "Dölj detaljer" : "Detaljer"}
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
                      {score != null ? Math.round(score) : "—"}
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
            content={({ active, payload }: any) => {
              if (!active || !payload?.length) return null;
              return (
                <div className="px-2 py-1.5 rounded-lg text-xs shadow-md bg-[var(--color-bg-surface)] text-[var(--color-text-primary)]"
                     style={{ border: "1px solid var(--color-border-strong)" }}>
                  <span className="font-semibold">{payload[0].value}</span>
                  <span className="ml-1 text-[var(--color-text-muted)]">{payload[0].payload.date}</span>
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
                {earnings.slice(0, 8).map((e: any, i: number) => {
                  const surprise = e.estimate ? ((e.actual - e.estimate) / Math.abs(e.estimate) * 100).toFixed(1) : null;
                  return (
                    <tr key={i} className="border-b border-[var(--color-border)] hover:bg-[var(--color-bg-elevated)]">
                      <td className="py-2 pr-4 text-[var(--color-text-primary)]">{e.quarter} {e.year}</td>
                      <td className={cn("text-right py-2 pr-4 font-mono tabular", e.actual >= 0 ? "text-[var(--color-up)]" : "text-[var(--color-down)]")}>
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
        <h3 className="text-sm font-semibold mb-4 text-[var(--color-text-primary)]">
          Nyheter
        </h3>
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
            { label: "Bruttomarginal", value: stock.gross_margin != null ? `${(stock.gross_margin * 100).toFixed(1)} %` : "—", tip: "Hur stor andel av intäkterna som kvarstår efter direkta produktionskostnader." },
            { label: "Rörelsemarginal", value: stock.operating_margin != null ? `${(stock.operating_margin * 100).toFixed(1)} %` : "—", tip: "Vinst som andel av intäkterna, efter driftkostnader men före räntor och skatt." },
            { label: "ROE", value: stock.roe != null ? `${(stock.roe * 100).toFixed(1)} %` : "—", tip: "Avkastning på eget kapital — hur effektivt bolaget skapar värde för aktieägarna." },
            { label: "Skuldsättning (D/E)", value: stock.debt_to_equity != null ? stock.debt_to_equity.toFixed(2) : "—", tip: "Skulder relativt eget kapital. Under 1,0 är konservativt." },
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
