"use client";

import { useState } from "react";
import { TrendingUp, Shield, AlertTriangle, ChevronDown, ChevronUp, Star, Loader2, HelpCircle, CheckCircle2 } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { buildVerdict, type VerdictReason } from "@/lib/plainLanguage";
import type { ScanRow } from "@/types/scan";
import { InfoTooltip } from "@/components/ui/InfoTooltip";
import { FeedbackWidget } from "@/components/ui/FeedbackWidget";
import { cn } from "@/lib/utils";
import { formatPrice, formatPctChange, changeClass, signalClass, signalLabel } from "@/lib/format";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { trackEvent, EVENT } from "@/lib/tracking";

// ── Quality styling (design tokens — matches rest of app, dark-mode safe) ────

function QualityIcon({ label }: { label: string }) {
  switch (label) {
    case "exceptionell":
      return <Star size={20} className="text-[var(--color-up)]" strokeWidth={1.5} />;
    case "stark":
      return <TrendingUp size={20} className="text-[var(--color-up)]" strokeWidth={1.5} />;
    case "bra":
      return <CheckCircle2 size={20} className="text-[var(--color-text-secondary)]" strokeWidth={1.5} />;
    case "okej":
      return <HelpCircle size={20} className="text-[var(--color-warn)]" strokeWidth={1.5} />;
    default:
      return <AlertTriangle size={20} className="text-[var(--color-down)]" strokeWidth={1.5} />;
  }
}

// ── SignalBadge helper ──────────────────────────────────────────────────────

function SignalBadge({ signal }: { signal: string | null | undefined }) {
  return (
    <span className={cn("inline-block px-2.5 py-1 rounded-md text-xs font-medium", signalClass(signal))}>
      {signalLabel(signal)}
    </span>
  );
}

// ── Reason icon helper ──────────────────────────────────────────────────────

function ReasonIcon({ icon }: { icon: VerdictReason["icon"] }) {
  switch (icon) {
    case "check":
      return <TrendingUp size={16} className="shrink-0 text-[var(--color-up)]" />;
    case "warning":
      return <AlertTriangle size={16} className="shrink-0 text-[var(--color-warn)]" />;
    case "info":
      return <Shield size={16} className="shrink-0 text-[var(--color-accent)]" />;
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
    <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-bg-elevated)] p-3">
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

// ── WatchlistButton ──────────────────────────────────────────────────────────

function WatchlistButton({ ticker }: { ticker: string }) {
  const qc = useQueryClient();

  const { data: watchlist = [] } = useQuery<{ ticker: string }[]>({
    queryKey: ["watchlist"],
    queryFn: () => api("/api/watchlist"),
    staleTime: 60_000,
  });
  const isWatching = watchlist.some((w) => w.ticker === ticker);

  const addWatch = useMutation({
    mutationFn: () => api(`/api/watchlist/${ticker}`, { method: "POST" }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["watchlist"] }); toast.success("Bevakning tillagd"); },
    onError: () => toast.error("Logga in för att bevaka aktier"),
  });

  const removeWatch = useMutation({
    mutationFn: () => api(`/api/watchlist/${ticker}`, { method: "DELETE" }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["watchlist"] }); toast.success("Bevakning borttagen"); },
  });

  const pending = addWatch.isPending || removeWatch.isPending;

  return (
    <button
      onClick={() => isWatching ? removeWatch.mutate() : addWatch.mutate()}
      disabled={pending}
      className={cn(
        "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors border",
        isWatching
          ? "border-[var(--color-warn)] text-[var(--color-warn)] bg-[var(--color-warn-soft)]"
          : "border-[var(--color-border)] hover:border-[var(--color-border-strong)] text-[var(--color-text-secondary)]",
      )}
    >
      {pending ? (
        <Loader2 size={13} className="animate-spin" />
      ) : (
        <Star size={13} strokeWidth={1.5} fill={isWatching ? "currentColor" : "none"} />
      )}
      {isWatching ? "Bevakad" : "Bevaka"}
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

  return (
    <div className="rounded-xl border p-5 space-y-5 bg-[var(--color-bg-surface)] border-[var(--color-border)]">
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

      {/* Icon + quality sentence */}
      <div className="flex items-start gap-3">
        <span className="shrink-0 mt-0.5">
          <QualityIcon label={verdict.qualityLabel} />
        </span>
        <p className="text-sm leading-relaxed text-[var(--color-text-secondary)]">
          {verdict.qualitySentence}
        </p>
      </div>

      {/* 3 reasons */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {verdict.reasons.map((reason, i) => (
          <div
            key={i}
            className="rounded-lg border p-3 bg-[var(--color-bg-elevated)] border-[var(--color-border)]"
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
      <div className="rounded-lg border p-3 bg-[var(--color-warn-soft)] border-[var(--color-warn-soft)]">
        <div className="flex items-center gap-1.5 mb-1">
          <AlertTriangle size={15} className="shrink-0 text-[var(--color-warn)]" />
          <span className="text-xs font-semibold text-[var(--color-text-primary)]">
            {verdict.risk.title}
          </span>
        </div>
        <p className="text-[11px] text-[var(--color-text-secondary)] leading-relaxed">
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
        <WatchlistButton ticker={stock.ticker} />
        <FeedbackWidget component="verdict_card" context={stock.ticker} />
      </div>
    </div>
  );
}
