"use client";
import { InfoTooltip } from "@/components/ui/InfoTooltip";
import { cn } from "@/lib/utils";

interface MetricCardProps {
  label: string;
  value: string | number;
  subtitle?: string;
  change?: { value: number; positive: boolean };
  tooltip?: string;
  variant?: "default" | "positive" | "negative" | "neutral";
}

export function MetricCard({ label, value, subtitle, change, tooltip, variant = "default" }: MetricCardProps) {
  const valueColor = {
    default: "text-[var(--color-text-primary)]",
    positive: "text-[var(--color-up)]",
    negative: "text-[var(--color-down)]",
    neutral: "text-[var(--color-text-muted)]",
  }[variant];

  return (
    <div className="rounded-xl border p-4 bg-[var(--color-bg-surface)] border-[var(--color-border)] space-y-1">
      <div className="flex items-center gap-1.5">
        <span className="text-xs text-[var(--color-text-muted)]">{label}</span>
        {tooltip && <InfoTooltip text={tooltip} />}
      </div>
      <div className={cn("text-lg font-semibold font-mono tabular", valueColor)}>{value}</div>
      {subtitle && <div className="text-xs text-[var(--color-text-muted)]">{subtitle}</div>}
      {change && (
        <div className={cn("text-xs font-mono tabular", change.positive ? "text-[var(--color-up)]" : "text-[var(--color-down)]")}>
          {change.positive ? "+" : ""}{change.value.toFixed(1)}%
        </div>
      )}
    </div>
  );
}
