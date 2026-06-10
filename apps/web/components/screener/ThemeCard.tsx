"use client";

import Link from "next/link";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import { cn } from "@/lib/utils";
import { useScreener } from "@/hooks/useScreener";
import { FeedbackWidget } from "@/components/ui/FeedbackWidget";
import { formatPrice, formatPctChange } from "@/lib/format";
import type { ThemeDefinition } from "@/lib/themes";
import type { ScanRow } from "@/types/scan";

// ── Risk colour mapping ─────────────────────────────────────────────────────

const RISK_COLORS: Record<
  string,
  { bg: string; text: string; ring: string }
> = {
  "Låg risk": {
    bg: "bg-green-50",
    text: "text-green-700",
    ring: "ring-green-200",
  },
  "Låg–Medel risk": {
    bg: "bg-green-50",
    text: "text-green-700",
    ring: "ring-green-200",
  },
  "Medel risk": {
    bg: "bg-amber-50",
    text: "text-amber-700",
    ring: "ring-amber-200",
  },
  "Varierande risk": {
    bg: "bg-amber-50",
    text: "text-amber-700",
    ring: "ring-amber-200",
  },
  "Högre risk": {
    bg: "bg-red-50",
    text: "text-red-700",
    ring: "ring-red-200",
  },
};

// ── Helpers ─────────────────────────────────────────────────────────────────

function changeIcon(v: number | null) {
  if (v === null || v === undefined) return <Minus size={14} strokeWidth={1.5} />;
  if (v > 0) return <TrendingUp size={14} strokeWidth={1.5} />;
  return <TrendingDown size={14} strokeWidth={1.5} />;
}

// ── ThemeStockRow ────────────────────────────────────────────────────────────

function ThemeStockRow({
  row,
  position,
}: {
  row: ScanRow;
  position: number;
}) {
  const change = row.change_pct;

  return (
    <Link
      href={`/aktie/${row.ticker}`}
      className={cn(
        "group flex items-center gap-3 px-4 py-3 rounded-xl transition-colors",
        "hover:bg-[var(--color-bg-elevated)]",
      )}
    >
      {/* Position number */}
      <span className="w-6 text-center text-xs font-medium text-[var(--color-text-muted)] tabular-nums shrink-0">
        {position}
      </span>

      {/* Name + ticker + sector */}
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-[var(--color-text-primary)] truncate group-hover:text-[var(--color-accent)] transition-colors">
          {row.name}
        </p>
        <p className="text-xs text-[var(--color-text-muted)] truncate mt-0.5">
          {row.ticker}
          {row.sector && (
            <>
              <span className="mx-1 opacity-40">&middot;</span>
              {row.sector}
            </>
          )}
        </p>
      </div>

      {/* Price + change */}
      <div className="text-right shrink-0">
        <p className="text-sm font-medium text-[var(--color-text-primary)] tabular-nums">
          {formatPrice(row.price)}
        </p>
        <span
          className={cn(
            "inline-flex items-center gap-1 text-xs font-medium tabular-nums mt-0.5",
            change === null || change === undefined
              ? "text-[var(--color-text-muted)]"
              : change > 0
                ? "text-[var(--color-up)]"
                : change < 0
                  ? "text-[var(--color-down)]"
                  : "text-[var(--color-text-muted)]",
          )}
        >
          {changeIcon(change)}
          {formatPctChange(change)}
        </span>
      </div>
    </Link>
  );
}

// ── Skeleton row ────────────────────────────────────────────────────────────

function SkeletonRow() {
  return (
    <div className="flex items-center gap-3 px-4 py-3 animate-pulse">
      <span className="w-6 h-3 rounded bg-[var(--color-bg-elevated)] shrink-0" />
      <div className="flex-1 space-y-1.5">
        <div className="h-3.5 w-36 rounded bg-[var(--color-bg-elevated)]" />
        <div className="h-3 w-24 rounded bg-[var(--color-bg-elevated)]" />
      </div>
      <div className="text-right space-y-1.5 shrink-0">
        <div className="h-3.5 w-16 rounded bg-[var(--color-bg-elevated)]" />
        <div className="h-3 w-14 rounded bg-[var(--color-bg-elevated)]" />
      </div>
    </div>
  );
}

// ── ThemeCard ───────────────────────────────────────────────────────────────

export function ThemeCard({ theme }: { theme: ThemeDefinition }) {
  const { data, isLoading } = useScreener(theme.params);
  const rows = (data ?? []).slice(0, theme.limit);

  const riskColor = RISK_COLORS[theme.riskLabel] ?? {
    bg: "bg-gray-50",
    text: "text-gray-700",
    ring: "ring-gray-200",
  };

  // Build query string for "Se alla" link
  const searchParams = new URLSearchParams();
  const p = theme.params as Record<string, unknown>;
  for (const [key, val] of Object.entries(p)) {
    if (val === undefined || val === null) continue;
    if (Array.isArray(val)) {
      val.forEach((v) => searchParams.append(key, String(v)));
    } else {
      searchParams.set(key, String(val));
    }
  }
  searchParams.set("sort_by", theme.sortBy);
  const allLink = `/screener?${searchParams.toString()}`;

  return (
    <section
      className={cn(
        "rounded-2xl border overflow-hidden",
        "bg-[var(--color-bg-surface)] border-[var(--color-border)]",
      )}
    >
      {/* Header */}
      <div className="px-5 pt-5 pb-3">
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className="text-xl leading-none" aria-hidden="true">
                {theme.emoji}
              </span>
              <h2 className="text-lg font-semibold text-[var(--color-text-primary)]">
                {theme.label}
              </h2>
            </div>
            <p className="text-sm text-[var(--color-text-secondary)] mt-1.5 leading-relaxed">
              {theme.description}
            </p>
          </div>

          {/* Risk badge */}
          <span
            className={cn(
              "shrink-0 inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium ring-1 ring-inset",
              riskColor.bg,
              riskColor.text,
              riskColor.ring,
            )}
          >
            {theme.riskLabel}
          </span>
        </div>

        {/* Collapsible risk explanation */}
        <details className="group mt-3">
          <summary className="text-xs text-[var(--color-text-muted)] cursor-pointer hover:text-[var(--color-text-secondary)] transition-colors select-none list-none flex items-center gap-1">
            <span className="inline-block transition-transform duration-200 group-open:rotate-90">
              &rsaquo;
            </span>
            Vad betyder &rdquo;{theme.riskLabel}&rdquo;?
          </summary>
          <p className="text-xs text-[var(--color-text-secondary)] mt-2 leading-relaxed max-w-prose">
            {theme.riskExplanation}
          </p>
        </details>
      </div>

      {/* Stock list */}
      <div className="border-t border-[var(--color-border)]">
        {isLoading ? (
          <div className="divide-y divide-[var(--color-border)]">
            <SkeletonRow />
            <SkeletonRow />
            <SkeletonRow />
          </div>
        ) : rows.length === 0 ? (
          <p className="px-5 py-6 text-sm text-[var(--color-text-muted)] text-center">
            Inga aktier matchar just nu
          </p>
        ) : (
          <div className="divide-y divide-[var(--color-border)]">
            {rows.map((row, i) => (
              <ThemeStockRow key={row.ticker} row={row} position={i + 1} />
            ))}
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between px-5 py-3 border-t border-[var(--color-border)]">
        <FeedbackWidget
          component="theme-card"
          context={theme.id}
          className="scale-[0.85] origin-left"
        />
        <Link
          href={allLink}
          className="text-xs font-medium text-[var(--color-accent)] hover:underline transition-colors"
        >
          Se alla &rarr;
        </Link>
      </div>
    </section>
  );
}
