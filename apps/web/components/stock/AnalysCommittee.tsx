"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Users, Brain, TrendingUp, BarChart2, AlertCircle, RefreshCw } from "lucide-react";
import { api } from "@/lib/api";
import type { ScanRow } from "@/types/scan";

interface CommitteeResult {
  ticker: string;
  analysts: {
    teknisk: { name: string; analysis: string };
    fundamental: { name: string; analysis: string };
    sentiment: { name: string; analysis: string };
  };
  synthesis: {
    verdict: "STARK" | "BRA" | "AVVAKTA" | "EJ_AKTUELLT";
    confidence: number;
    summary: string;
    disagreement: boolean;
    disagreement_note: string | null;
  };
  cached_date: string;
}

interface Props {
  stock: ScanRow;
}

const VERDICT_COLORS: Record<string, string> = {
  STARK:     "var(--color-up)",
  BRA:       "var(--color-accent)",
  AVVAKTA:   "var(--color-warn)",
  EJ_AKTUELLT: "var(--color-text-muted)",
};

export function AnalysCommittee({ stock }: Props) {
  const [launched, setLaunched] = useState(false);

  const { data, isLoading, error, refetch } = useQuery<CommitteeResult>({
    queryKey: ["committee", stock.ticker],
    queryFn: () =>
      api<CommitteeResult>(`/api/ai/committee/${stock.ticker}`, {
        method: "POST",
        body: JSON.stringify({ ticker: stock.ticker, stock_data: stock }),
      }),
    enabled: launched,
    staleTime: 8 * 60 * 60_000, // cached for 8h (also cached server-side per day)
  });

  if (!launched) {
    return (
      <div className="flex flex-col items-center justify-center py-16 gap-4">
        <div className="flex items-center gap-2 text-[var(--color-text-secondary)]">
          <Users size={20} strokeWidth={1.5} />
          <span className="text-sm font-medium">Analyskommittén</span>
        </div>
        <p className="text-xs text-center max-w-72 text-[var(--color-text-muted)]">
          Tre AI-analytiker analyserar aktien parallellt — teknisk, fundamental och sentiment.
          En ordförande syntetiserar till ett slutgiltigt omdöme.
        </p>
        <button
          onClick={() => setLaunched(true)}
          className="px-5 py-2.5 rounded-xl text-sm font-medium transition-colors
                     bg-[var(--color-accent)] text-white hover:bg-[var(--color-accent-hover)]"
        >
          Starta analys
        </button>
      </div>
    );
  }

  if (isLoading) return <CommitteeSkeleton />;

  if (error || !data) {
    return (
      <div className="flex flex-col items-center py-12 gap-3">
        <AlertCircle size={20} className="text-[var(--color-down)]" />
        <p className="text-xs text-[var(--color-text-muted)]">Analys misslyckades</p>
        <button onClick={() => refetch()}
                className="text-xs text-[var(--color-accent)] hover:underline">
          Försök igen
        </button>
      </div>
    );
  }

  const { synthesis, analysts } = data;
  const verdictColor = VERDICT_COLORS[synthesis.verdict] ?? "var(--color-text-muted)";

  return (
    <div className="space-y-5">
      {/* Synthesis card */}
      <div className="rounded-xl p-5 border bg-[var(--color-bg-elevated)] border-[var(--color-border)]">
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <Brain size={16} strokeWidth={1.5} style={{ color: verdictColor }} />
              <span className="text-xs font-medium text-[var(--color-text-secondary)]">
                Ordförandens syntes
              </span>
            </div>
            <p className="text-sm text-[var(--color-text-primary)] leading-relaxed">
              {synthesis.summary}
            </p>
          </div>
          <div className="flex flex-col items-center shrink-0">
            <span className="text-lg font-bold font-mono" style={{ color: verdictColor }}>
              {synthesis.verdict}
            </span>
            <span className="text-xs text-[var(--color-text-muted)] mt-0.5">
              Konfidens {synthesis.confidence}%
            </span>
            <ConfidenceMeter value={synthesis.confidence} color={verdictColor} />
          </div>
        </div>

        {synthesis.disagreement && synthesis.disagreement_note && (
          <div className="mt-3 px-3 py-2 rounded-lg flex items-start gap-2 bg-[var(--color-warn-soft)] text-[var(--color-warn)]">
            <AlertCircle size={13} strokeWidth={1.5} className="shrink-0 mt-0.5" />
            <span className="text-xs">{synthesis.disagreement_note}</span>
          </div>
        )}
      </div>

      {/* Three analyst cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <AnalystCard
          icon={TrendingUp}
          name="Teknisk analytiker"
          analysis={analysts.teknisk.analysis}
        />
        <AnalystCard
          icon={BarChart2}
          name="Fundamental analytiker"
          analysis={analysts.fundamental.analysis}
        />
        <AnalystCard
          icon={Users}
          name="Sentimentanalytiker"
          analysis={analysts.sentiment.analysis}
        />
      </div>

      <div className="flex items-center justify-between">
        <span className="text-[11px] text-[var(--color-text-muted)]">
          Analys från {data.cached_date}
        </span>
        <button
          onClick={() => refetch()}
          className="flex items-center gap-1 text-[11px] text-[var(--color-text-muted)] hover:text-[var(--color-accent)]"
        >
          <RefreshCw size={11} strokeWidth={1.5} />
          Uppdatera
        </button>
      </div>
    </div>
  );
}

function AnalystCard({ icon: Icon, name, analysis }: {
  icon: React.ElementType;
  name: string;
  analysis: string;
}) {
  const [expanded, setExpanded] = useState(false);

  // Extract short verdict (first line or **text**) and detailed analysis
  const shortMatch = analysis.match(/^\*\*(.+?)\*\*/);
  const shortVerdict = shortMatch ? shortMatch[1] : "";
  const detailStart = shortMatch ? analysis.indexOf(shortMatch[0]) + shortMatch[0].length : 0;
  const detailText = detailStart > 0 ? analysis.slice(detailStart).trim() : analysis;

  return (
    <div className="rounded-xl p-4 border space-y-3 bg-[var(--color-bg-surface)] border-[var(--color-border)]">
      <div className="flex items-center gap-2">
        <Icon size={14} strokeWidth={1.5} />
        <span className="text-xs font-medium text-[var(--color-text-secondary)]">{name}</span>
      </div>

      {/* Short verdict — always visible */}
      {shortVerdict && (
        <p className="text-sm font-semibold text-[var(--color-text-primary)]">
          {shortVerdict}
        </p>
      )}

      {/* Detailed analysis — collapsed by default */}
      {detailText && (
        <div className={expanded ? "" : "line-clamp-3"}>
          <p className="text-xs text-[var(--color-text-primary)] leading-relaxed whitespace-pre-line">
            {detailText}
          </p>
        </div>
      )}

      {detailText && detailText.length > 150 && (
        <button
          onClick={() => setExpanded(!expanded)}
          className="text-xs text-[var(--color-accent)] hover:underline"
        >
          {expanded ? "Dölj detaljer" : "Visa detaljerad analys"}
        </button>
      )}
    </div>
  );
}

function ConfidenceMeter({ value, color }: { value: number; color: string }) {
  return (
    <div className="w-16 h-1.5 rounded-full mt-1.5 overflow-hidden bg-[var(--color-bg-base)]">
      <div
        className="h-full rounded-full transition-all"
        style={{ width: `${value}%`, background: color }}
      />
    </div>
  );
}

function CommitteeSkeleton() {
  return (
    <div className="space-y-5">
      <div className="skeleton h-28 rounded-xl" />
      <div className="grid grid-cols-3 gap-4">
        {[1,2,3].map(i => <div key={i} className="skeleton h-32 rounded-xl" />)}
      </div>
    </div>
  );
}
