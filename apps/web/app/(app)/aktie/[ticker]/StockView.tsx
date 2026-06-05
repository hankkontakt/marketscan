"use client";

import { useState } from "react";
import { AlertTriangle } from "lucide-react";
import { useStock, usePriceHistory, useScoreHistory } from "@/hooks/useStock";
import { VerdictHeader } from "@/components/stock/VerdictHeader";
import { PriceChart } from "@/components/charts/PriceChart";
import { FactorRadar } from "@/components/charts/FactorRadar";
import { AnalysCommittee } from "@/components/stock/AnalysCommittee";
import { cn } from "@/lib/utils";
import {
  formatPrice, formatNumber, formatPct, formatMarketCap, scoreColorClass, formatScore,
} from "@/lib/format";
import type { ScanRow } from "@/types/scan";

const TABS = ["Översikt", "Faktorer", "Analys", "Rapporter", "AI"] as const;
type Tab = (typeof TABS)[number];

interface Props {
  ticker: string;
}

export function StockView({ ticker }: Props) {
  const { data: stock, isLoading, error } = useStock(ticker);
  const [activeTab, setActiveTab] = useState<Tab>("Översikt");

  if (isLoading) return <StockSkeleton />;
  if (error || !stock) {
    return (
      <div className="flex flex-col items-center justify-center py-24 gap-3">
        <AlertTriangle size={24} style={{ color: "var(--color-warn)" }} />
        <p className="text-sm text-[var(--color-text-secondary)]">
          Aktie {ticker} hittades inte
        </p>
      </div>
    );
  }

  return (
    <div className="-mx-8 -mt-6">
      {/* Sticky verdict header */}
      <VerdictHeader stock={stock} />

      {/* Tab bar */}
      <div className="flex border-b px-6"
           style={{ background: "var(--color-bg-surface)", borderColor: "var(--color-border)" }}>
        {TABS.map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={cn(
              "px-4 py-3 text-sm border-b-2 transition-colors -mb-px",
              activeTab === tab
                ? "border-[var(--color-accent)] text-[var(--color-accent)]"
                : "border-transparent text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]",
            )}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="px-6 py-6">
        {activeTab === "Översikt" && <OverviewTab stock={stock} />}
        {activeTab === "Faktorer" && <FaktorerTab stock={stock} />}
        {activeTab === "Analys" && <AnalysTab ticker={ticker} />}
        {activeTab === "Rapporter" && <RapporterTab stock={stock} />}
        {activeTab === "AI" && <AITab stock={stock} />}
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
      <div className="xl:col-span-2 rounded-xl p-4 border"
           style={{ background: "var(--color-bg-surface)", borderColor: "var(--color-border)" }}>
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
      <div className="rounded-xl p-4 border"
           style={{ background: "var(--color-bg-surface)", borderColor: "var(--color-border)" }}>
        <h3 className="text-sm font-medium mb-4 text-[var(--color-text-secondary)]">
          Nyckeltal
        </h3>
        <dl className="space-y-3">
          {[
            { label: "P/E (TTM)",           value: stock.pe_trailing != null ? formatNumber(stock.pe_trailing, 1) : "—" },
            { label: "P/E (forward)",        value: stock.pe_forward != null ? formatNumber(stock.pe_forward, 1) : "—" },
            { label: "ROE",                  value: stock.roe != null ? formatPct(stock.roe) : "—" },
            { label: "ROA",                  value: stock.roa != null ? formatPct(stock.roa) : "—" },
            { label: "Bruttomarginal",       value: stock.gross_margin != null ? formatPct(stock.gross_margin) : "—" },
            { label: "Rörelsemarginal",      value: stock.operating_margin != null ? formatPct(stock.operating_margin) : "—" },
            { label: "Finansiell styrka",    value: stock.piotroski_f != null ? `${stock.piotroski_f}/9` : "—" },
            { label: "Skuldsättning (D/E)",  value: stock.debt_to_equity != null ? formatNumber(stock.debt_to_equity, 2) : "—" },
            { label: "Direktavkastning",     value: stock.dividend_yield != null ? formatPct(stock.dividend_yield) : "—" },
            { label: "Beta",                 value: stock.beta != null ? formatNumber(stock.beta, 2) : "—" },
            { label: "Börsvärde",            value: formatMarketCap(stock.market_cap) },
          ].map(({ label, value }) => (
            <div key={label} className="flex justify-between items-center">
              <dt className="text-xs text-[var(--color-text-muted)]">{label}</dt>
              <dd className="text-xs font-mono tabular text-[var(--color-text-primary)]">{value}</dd>
            </div>
          ))}
        </dl>
      </div>

      {/* AI summary */}
      {stock.score_total != null && (
        <div className="xl:col-span-3 rounded-xl p-4 border"
             style={{ background: "var(--color-bg-surface)", borderColor: "var(--color-border)" }}>
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
      <div className="rounded-xl p-4 border"
           style={{ background: "var(--color-bg-surface)", borderColor: "var(--color-border)" }}>
        <h3 className="text-sm font-medium mb-2 text-[var(--color-text-secondary)]">Faktoröversikt</h3>
        <FactorRadar stock={stock} />
      </div>

      {/* Factor breakdown */}
      <div className="rounded-xl p-4 border"
           style={{ background: "var(--color-bg-surface)", borderColor: "var(--color-border)" }}>
        <h3 className="text-sm font-medium mb-4 text-[var(--color-text-secondary)]">Faktorbetyg</h3>
        <div className="space-y-4">
          {Object.entries(FACTOR_DESCS).map(([key, desc]) => {
            const score = stock[key as keyof ScanRow] as number | null;
            return (
              <div key={key}>
                <div className="flex justify-between items-center mb-1">
                  <span className="text-xs text-[var(--color-text-primary)]">
                    {key.replace("score_", "").charAt(0).toUpperCase() + key.replace("score_", "").slice(1)}
                  </span>
                  <span className={cn("font-mono text-xs font-semibold tabular", scoreColorClass(score))}>
                    {score != null ? Math.round(score) : "—"}
                  </span>
                </div>
                <div className="h-1.5 rounded-full overflow-hidden"
                     style={{ background: "var(--color-bg-elevated)" }}>
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
      <div className="rounded-xl p-4 border"
           style={{ background: "var(--color-bg-surface)", borderColor: "var(--color-border)" }}>
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
  return (
    <div className="flex items-end gap-1 h-32">
      {history.slice().reverse().map((point, i) => (
        <div
          key={point.date}
          title={`${point.date}: ${Math.round(point.score)}`}
          className="flex-1 rounded-t transition-all"
          style={{
            height: `${point.score}%`,
            background: point.score >= 70
              ? "var(--color-score-high)"
              : point.score >= 50
              ? "var(--color-score-mid)"
              : "var(--color-score-low)",
            opacity: 0.6 + (i / history.length) * 0.4,
          }}
        />
      ))}
    </div>
  );
}

// ─── Rapporter ───────────────────────────────────────────────────────────────

function RapporterTab({ stock }: { stock: ScanRow }) {
  return (
    <div className="rounded-xl p-5 border"
         style={{ background: "var(--color-bg-surface)", borderColor: "var(--color-border)" }}>
      <p className="text-sm text-[var(--color-text-secondary)]">
        Kvartalsrapporter och EPS vs estimat hämtas från yfinance och visas här.
        Klicka på Summera för AI-analys av senaste rapporten.
      </p>
      <p className="text-xs mt-2 text-[var(--color-text-muted)]">
        Implementeras när backend_worker pipeline är kopplad till R2.
      </p>
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

// cn import needed
function cn(...classes: (string | boolean | undefined)[]) {
  return classes.filter(Boolean).join(" ");
}
