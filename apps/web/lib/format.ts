/**
 * Financial formatting utilities.
 * All numbers displayed with tabular-nums (apply .tabular CSS class).
 */

const pct = new Intl.NumberFormat("sv-SE", {
  style: "percent",
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
});

const pct2 = new Intl.NumberFormat("sv-SE", {
  style: "percent",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

export function formatPct(value: number | null | undefined, decimals: 1 | 2 = 1): string {
  if (value == null) return "—";
  return (decimals === 2 ? pct2 : pct).format(value);
}

export function formatPctChange(value: number | null | undefined): string {
  if (value == null) return "—";
  const sign = value > 0 ? "+" : "";
  return `${sign}${pct.format(value)}`;
}

export function formatPrice(value: number | null | undefined, currency = "SEK"): string {
  if (value == null) return "—";
  return new Intl.NumberFormat("sv-SE", {
    style: "currency",
    currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

export function formatNumber(value: number | null | undefined, decimals = 0): string {
  if (value == null) return "—";
  return new Intl.NumberFormat("sv-SE", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value);
}

export function formatMarketCap(value: number | null | undefined): string {
  if (value == null) return "—";
  if (value >= 1e12) return `${(value / 1e12).toFixed(1)} tn`;
  if (value >= 1e9) return `${(value / 1e9).toFixed(1)} mdr`;
  if (value >= 1e6) return `${(value / 1e6).toFixed(0)} M`;
  return formatNumber(value);
}

export function formatScore(value: number | null | undefined): string {
  if (value == null) return "—";
  return Math.round(value).toString();
}

export function scoreColorClass(score: number | null | undefined): string {
  if (score == null) return "text-[var(--color-text-muted)]";
  if (score >= 70) return "text-[var(--color-score-high)]";
  if (score >= 50) return "text-[var(--color-score-mid)]";
  return "text-[var(--color-score-low)]";
}

export function signalLabel(signal: string | null | undefined): string {
  const map: Record<string, string> = {
    STARK: "Starkt köpläge",
    OK: "Bra läge",
    VÄNTA: "Avvakta",
    EJ_AKTUELL: "Ej aktuellt",
    EJ: "Ej aktuellt",
  };
  return map[signal ?? ""] ?? signal ?? "—";
}

export function signalShortLabel(signal: string | null | undefined): string {
  const map: Record<string, string> = {
    STARK: "Starkt",
    OK: "Bra",
    VÄNTA: "Vänta",
    EJ_AKTUELL: "Ej aktuell",
    EJ: "Ej aktuell",
  };
  return map[signal ?? ""] ?? signal ?? "—";
}

export function signalBadgeClass(signal: string | null | undefined): string {
  const map: Record<string, string> = {
    STARK: "bg-[var(--color-up)]/10 text-[var(--color-up)] border-[var(--color-up)]/20",
    OK: "bg-[var(--color-accent)]/10 text-[var(--color-accent)] border-[var(--color-accent)]/20",
    VÄNTA: "bg-[var(--color-warn)]/10 text-[var(--color-warn)] border-[var(--color-warn)]/20",
    EJ_AKTUELL: "bg-[var(--color-text-muted)]/10 text-[var(--color-text-muted)] border-[var(--color-text-muted)]/20",
  };
  return map[signal ?? ""] ?? "bg-[var(--color-text-muted)]/10 text-[var(--color-text-muted)]";
}

export function signalClass(signal: string | null | undefined): string {
  const map: Record<string, string> = {
    STARK: "signal-stark",
    OK: "signal-ok",
    VÄNTA: "signal-vanta",
    EJ_AKTUELL: "signal-ej",
    EJ: "signal-ej",
  };
  return map[signal ?? ""] ?? "signal-ej";
}

export function trendLabel(trend: string | null | undefined): string {
  const map: Record<string, string> = {
    Upptrend: "Upptrend",
    Sidled: "Sidled",
    Nedtrend: "Nedtrend",
  };
  return map[trend ?? ""] ?? trend ?? "—";
}

export function segmentLabel(segment: string | null | undefined): string {
  const map: Record<string, string> = {
    large_cap: "Stora bolag",
    mid_cap: "Medelstora",
    small_cap: "Småbolag",
    micro_cap: "Mikrobolag",
  };
  return map[segment ?? ""] ?? segment ?? "—";
}

export function changeClass(value: number | null | undefined): string {
  if (value == null) return "text-[var(--color-text-muted)]";
  if (value > 0) return "text-[var(--color-up)]";
  if (value < 0) return "text-[var(--color-down)]";
  return "text-[var(--color-text-secondary)]";
}
