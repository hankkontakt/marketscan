"use client";

import { useState } from "react";
import { TrendingUp, Shield, AlertTriangle, ChevronDown, ChevronUp, Eye, Star } from "lucide-react";
import { buildVerdict, type StockVerdict, type VerdictReason } from "@/lib/plainLanguage";
import type { ScanRow } from "@/types/scan";
import { InfoTooltip } from "@/components/ui/InfoTooltip";
import { FeedbackWidget } from "@/components/ui/FeedbackWidget";
import { cn } from "@/lib/utils";
import { formatPrice, formatPctChange, changeClass } from "@/lib/format";
import { trackEvent, EVENT } from "@/lib/tracking";

// ── Quality color map ───────────────────────────────────────────────────────

const QUALITY_COLORS: Record<StockVerdict["qualityLabel"], { bg: string; border: string; text: string; emoji: string }> = {
  exceptionell: { bg: "#f0fdf4", border: "#86efac", text: "#166534", emoji: "🌟" },
  stark:        { bg: "#f0fdf4", border: "#bbf7d0", text: "#166534", emoji: "✅" },
  bra:          { bg: "#f8fafc", border: "#e2e8f0", text: "#334155", emoji: "👍" },
  okej:         { bg: "#fffbeb", border: "#fde68a", text: "#92400e", emoji: "🤔" },
  svag:         { bg: "#fef2f2", border: "#fecaca", text: "#991b1b", emoji: "⚠️" },
};

// ── SignalBadge helper ──────────────────────────────────────────────────────

const SIGNAL_LABELS: Record<string, string> = {
  STARK:      "Starkt köpläge",
  OK:         "Bra läge",
  VÄNTA:      "Avvakta",
  EJ_AKTUELL: "Ej aktuellt",
};

const SIGNAL_COLORS: Record<string, string> = {
  STARK:      "bg-green-100 text-green-800",
  OK:         "bg-blue-100 text-blue-800",
  VÄNTA:      "bg-amber-100 text-amber-800",
  EJ_AKTUELL: "bg-gray-100 text-gray-600",
};

function SignalBadge({ signal }: { signal: string | null | undefined }) {
  const label = SIGNAL_LABELS[signal ?? ""] ?? signal ?? "—";
  const color = SIGNAL_COLORS[signal ?? ""] ?? SIGNAL_COLORS["EJ_AKTUELL"];
  return (
    <span className={cn("inline-block px-2.5 py-1 rounded-md text-xs font-medium", color)}>
      {label}
    </span>
  );
}

// ── Reason icon helper ──────────────────────────────────────────────────────

function ReasonIcon({ icon }: { icon: VerdictReason["icon"] }) {
  switch (icon) {
    case "check":
      return <TrendingUp size={16} className="shrink-0 text-green-600" />;
    case "warning":
      return <AlertTriangle size={16} className="shrink-0 text-amber-600" />;
    case "info":
      return <Shield size={16} className="shrink-0 text-blue-600" />;
  }
}

// ── NumberCard helper ───────────────────────────────────────────────────────

interface NumberCardDef {
  label: string;
  value: string;
  unit: string;
  tooltip: string;
}

const NUMBER_CARDS = (stock: ScanRow): NumberCardDef[] => [
  {
    label: "Totalbetyg",
    value: stock.score_total != null ? Math.round(stock.score_total).toString() : "—",
    unit: "/100",
    tooltip: "Sammanvägt betyg 0-100 baserat på 8 faktorer.",
  },
  {
    label: "P/E",
    value: stock.pe_trailing != null ? stock.pe_trailing.toFixed(1) : "—",
    unit: "x",
    tooltip: "Pris per krona vinst. Lägre = billigare.",
  },
  {
    label: "ROE",
    value: stock.roe != null ? (stock.roe * 100).toFixed(1) : "—",
    unit: "%",
    tooltip: "Avkastning på eget kapital. Högre = mer lönsamt.",
  },
  {
    label: "Beta",
    value: stock.beta != null ? stock.beta.toFixed(2) : "—",
    unit: "",
    tooltip: "Kursens känslighet mot börsen. 1 = följer index.",
  },
  {
    label: "Skuldsättning",
    value: stock.debt_to_equity != null ? stock.debt_to_equity.toFixed(2) : "—",
    unit: "x",
    tooltip: "Skulder / eget kapital. Lägre = mindre risk.",
  },
  {
    label: "Direktavkastning",
    value: stock.dividend_yield != null ? (stock.dividend_yield * 100).toFixed(2) : "—",
    unit: "%",
    tooltip: "Årlig utdelning i procent av kursen.",
  },
];

function NumberCard({ label, value, unit, tooltip }: NumberCardDef) {
  return (
    <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-bg-surface)] p-3">
      <div className="flex items-center gap-1 mb-1">
        <span className="text-[11px] text-[var(--color-text-muted)]">{label}</span>
        <InfoTooltip text={tooltip} side="top" />
      </div>
      <span className="font-mono text-lg font-bold tabular text-[var(--color-text-primary)]">
        {value}
        {unit && <span className="text-sm font-normal text-[var(--color-text-muted)] ml-0.5">{unit}</span>}
      </span>
    </div>
  );
}

// ── WatchlistButton (placeholder) ───────────────────────────────────────────

function WatchlistButton() {
  return (
    <button
      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors border
                 border-[var(--color-border)] hover:border-[var(--color-border-strong)]
                 text-[var(--color-text-secondary)]"
    >
      <Star size={13} strokeWidth={1.5} />
      Bevaka
    </button>
  );
}

// ── Main component ──────────────────────────────────────────────────────────

interface Props {
  stock: ScanRow;
}

export function VerdictCard({ stock }: Props) {
  const [showNumbers, setShowNumbers] = useState(false);
  const verdict = buildVerdict(stock);
  const colors = QUALITY_COLORS[verdict.qualityLabel];

  return (
    <div
      className="rounded-xl border p-5 space-y-5"
      style={{ borderColor: colors.border, backgroundColor: colors.bg }}
    >
      {/* Header: name + ticker / price + change */}
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <h2 className="text-lg font-bold text-[var(--color-text-primary)]">
              {stock.name}
            </h2>
            <span className="font-mono text-sm text-[var(--color-text-secondary)]">
              {stock.ticker}
            </span>
          </div>
        </div>
        <div className="shrink-0 text-right">
          <div className="font-mono text-lg font-bold tabular text-[var(--color-text-primary)]">
            {formatPrice(stock.price)}
          </div>
          {stock.change_pct != null && (
            <div className={cn("font-mono text-xs tabular", changeClass(stock.change_pct))}>
              {formatPctChange(stock.change_pct)}
            </div>
          )}
        </div>
      </div>

      {/* Signal badge */}
      <SignalBadge signal={stock.entry_signal} />

      {/* Emoji + quality sentence */}
      <div className="flex items-start gap-3">
        <span className="text-2xl shrink-0 block" style={{ lineHeight: 1 }}>
          {colors.emoji}
        </span>
        <p className="text-sm leading-relaxed" style={{ color: colors.text }}>
          {verdict.qualitySentence}
        </p>
      </div>

      {/* 3 reasons */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {verdict.reasons.map((reason, i) => (
          <div
            key={i}
            className="rounded-lg border p-3 bg-white border-[var(--color-border)]"
          >
            <div className="flex items-center gap-1.5 mb-1">
              <ReasonIcon icon={reason.icon} />
              <span className="text-xs font-semibold text-[var(--color-text-primary)]">
                {reason.title}
              </span>
            </div>
            <p className="text-[11px] text-[var(--color-text-secondary)] leading-relaxed">
              {reason.detail}
            </p>
          </div>
        ))}
      </div>

      {/* Risk */}
      <div className="rounded-lg border p-3 bg-amber-50 border-amber-200">
        <div className="flex items-center gap-1.5 mb-1">
          <AlertTriangle size={15} className="shrink-0 text-amber-700" />
          <span className="text-xs font-semibold text-[var(--color-text-primary)]">
            {verdict.risk.title}
          </span>
        </div>
        <p className="text-[11px] text-amber-800 leading-relaxed">
          {verdict.risk.detail}
        </p>
      </div>

      {/* Visa siffrorna expand */}
      <div>
        <button
          onClick={() => {
            setShowNumbers((v) => !v);
            if (!showNumbers) trackEvent(EVENT.VERDICT_EXPAND, { ticker: stock.ticker });
          }}
          className="flex items-center gap-1 text-xs font-medium text-[var(--color-accent)] hover:underline mb-3"
        >
          {showNumbers ? (
            <>Dölj siffrorna <ChevronUp size={13} /></>
          ) : (
            <>Visa siffrorna <ChevronDown size={13} /></>
          )}
        </button>

        {showNumbers && (
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
            {NUMBER_CARDS(stock).map((card) => (
              <NumberCard key={card.label} {...card} />
            ))}
          </div>
        )}
      </div>

      {/* Bottom row */}
      <div className="flex items-center justify-between pt-1">
        <WatchlistButton />
        <FeedbackWidget component="verdict_card" context={stock.ticker} />
      </div>
    </div>
  );
}
