"use client";

import { useState } from "react";
import * as Tabs from "@radix-ui/react-tabs";
import { AlertTriangle } from "lucide-react";
import { useStock, usePriceHistory, useScoreHistory } from "@/hooks/useStock";
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
          </Tabs.List>

          <div className="px-6 py-6">
            <Tabs.Content value="oversikt"><OverviewTab stock={stock} /></Tabs.Content>
            <Tabs.Content value="faktorer"><FaktorerTab stock={stock} /></Tabs.Content>
            <Tabs.Content value="analys"><AnalysTab ticker={ticker} /></Tabs.Content>
            <Tabs.Content value="rapporter"><RapporterTab stock={stock} /></Tabs.Content>
            <Tabs.Content value="ai"><AITab stock={stock} /></Tabs.Content>
          </div>
        </Tabs.Root>
      </div>
    </div>
  );
}

// ─── Översikt ────────────────────────────────────────────────────────────────

function OverviewTab({ stock }: { stock: ScanRow }) {
  const { data: priceData, isLoading } = usePriceHistory(stock.ticker);

  return (
    <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
      {/* Price chart */}
      <div className="xl:col-span-2 rounded-xl p-4 border bg-[var(--color-bg-surface)] border-[var(--color-border)]">
        <h3 className="text-sm font-medium mb-4 text-[var(--color-text-secondary)]">
          Prisutveckling
        </h3>
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

      {/* AI summary */}
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

// ─── Faktorer ────────────────────────────────────────────────────────────────

const FACTOR_DESCS: Record<string, string> = {
  score_value:     "Hur attraktivt aktien är prissatt relativt fundamentala värden (P/E, P/B m.fl.)",
  score_quality:   "Bolagets lönsamhet, finansiell styrka och resultatstabilitet",
  score_momentum:  "Pristrend och relativ styrka de senaste 3–12 månaderna",
  score_growth:    "Tillväxt i intäkter, vinst och kassaflöde",
  score_risk:      "Volatilitet, skuldsättning och likviditetsrisk",
  score_size:      "Storlekspremium och marknadskapitalisering",
  score_dividend:  "Direktavkastning, utdelningshistorik och hållbarhet",
  score_sentiment: "Nyhetssentiment, analytikerkonsensus och marknadsregim",
};

function FaktorerTab({ stock }: { stock: ScanRow }) {
  return (
    <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
      {/* Radar */}
      <div className="rounded-xl p-4 border bg-[var(--color-bg-surface)] border-[var(--color-border)]">
        <h3 className="text-sm font-medium mb-2 text-[var(--color-text-secondary)]">Faktoröversikt</h3>
        <FactorRadar stock={stock} />
      </div>

      {/* Factor breakdown */}
      <div className="rounded-xl p-4 border bg-[var(--color-bg-surface)] border-[var(--color-border)]">
        <h3 className="text-sm font-medium mb-4 text-[var(--color-text-secondary)]">Faktorbetyg</h3>
        <div className="space-y-4">
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
                <p className="text-[11px] mt-1 text-[var(--color-text-muted)]">{desc}</p>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

// ─── Analys ─────────────────────────────────────────────────────────────────

function AnalysTab({ ticker }: { ticker: string }) {
  const { data, isLoading } = useScoreHistory(ticker);

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

function RapporterTab({ stock }: { stock: ScanRow }) {
  const hasGrowth = stock.revenue_growth != null || stock.earnings_growth != null;

  return (
    <div className="space-y-5">
      {/* Available data */}
      {hasGrowth && (
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

      {/* Key ratios from latest report */}
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

      {/* Coming soon note */}
      <div className="rounded-xl border p-4 flex items-start gap-3 bg-[var(--color-bg-elevated)] border-[var(--color-border)]">
        <div className="text-xs leading-relaxed text-[var(--color-text-muted)]">
          <strong className="text-[var(--color-text-secondary)]">Detaljerade kvartalsrapporter</strong> med
          EPS vs estimat och AI-summering läggs till när pipeline-historiken är ansluten.
          Data ovan hämtas från senaste tillgängliga årsredovisning.
        </div>
      </div>
    </div>
  );
}

// ─── AI ─────────────────────────────────────────────────────────────────────

function AITab({ stock }: { stock: ScanRow }) {
  return <AnalysCommittee stock={stock} />;
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
