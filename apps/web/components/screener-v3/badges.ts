/**
 * V3 semantic state badges (plan section 26.1): text + color, never color
 * alone. Tradability is explicit: an inactive listing is a state, not a weak
 * rating.
 */

export interface BadgeStyle {
  label: string;
  bg: string;
  text: string;
  border: string;
}

export const THESIS_BAND_CONFIG: Record<string, BadgeStyle> = {
  BULLISH: {
    label: "Stark tes",
    bg: "bg-emerald-500/10 dark:bg-emerald-500/20",
    text: "text-emerald-700 dark:text-emerald-300",
    border: "border-emerald-500/30",
  },
  CONSTRUCTIVE: {
    label: "Konstruktiv",
    bg: "bg-teal-500/10 dark:bg-teal-500/20",
    text: "text-teal-700 dark:text-teal-300",
    border: "border-teal-500/30",
  },
  NEUTRAL: {
    label: "Neutral",
    bg: "bg-zinc-500/10 dark:bg-zinc-500/20",
    text: "text-zinc-700 dark:text-zinc-300",
    border: "border-zinc-500/30",
  },
  AVOID: {
    label: "Undvik",
    bg: "bg-amber-500/10 dark:bg-amber-500/20",
    text: "text-amber-700 dark:text-amber-300",
    border: "border-amber-500/30",
  },
};

export const SETUP_STATE_CONFIG: Record<string, BadgeStyle> = {
  READY: {
    label: "Bekräftad",
    bg: "bg-emerald-500/10 dark:bg-emerald-500/20",
    text: "text-emerald-700 dark:text-emerald-300",
    border: "border-emerald-500/30",
  },
  WATCH: {
    label: "Bevaka",
    bg: "bg-blue-500/10 dark:bg-blue-500/20",
    text: "text-blue-700 dark:text-blue-300",
    border: "border-blue-500/30",
  },
  WAIT: {
    label: "Vänta",
    bg: "bg-zinc-500/10 dark:bg-zinc-500/20",
    text: "text-zinc-700 dark:text-zinc-300",
    border: "border-zinc-500/30",
  },
  INSUFFICIENT: {
    label: "Otillräcklig data",
    bg: "bg-zinc-500/10 dark:bg-zinc-500/20",
    text: "text-zinc-500 dark:text-zinc-400",
    border: "border-zinc-500/30",
  },
};

export const RISK_STATE_CONFIG: Record<string, BadgeStyle> = {
  NORMAL: {
    label: "Låg",
    bg: "bg-emerald-500/10 dark:bg-emerald-500/20",
    text: "text-emerald-700 dark:text-emerald-300",
    border: "border-emerald-500/30",
  },
  ELEVATED: {
    label: "Medel",
    bg: "bg-amber-500/10 dark:bg-amber-500/20",
    text: "text-amber-700 dark:text-amber-300",
    border: "border-amber-500/30",
  },
  CRITICAL: {
    label: "Kritisk",
    bg: "bg-rose-500/10 dark:bg-rose-500/20",
    text: "text-rose-700 dark:text-rose-300",
    border: "border-rose-500/30",
  },
};

export const DATA_GRADE_CONFIG: Record<string, { label: string; bg: string; text: string }> = {
  A: { label: "A", bg: "bg-emerald-500/15", text: "text-emerald-600 dark:text-emerald-400" },
  B: { label: "B", bg: "bg-teal-500/15", text: "text-teal-600 dark:text-teal-400" },
  C: { label: "C", bg: "bg-blue-500/15", text: "text-blue-600 dark:text-blue-400" },
  D: { label: "D", bg: "bg-amber-500/15", text: "text-amber-600 dark:text-amber-400" },
};

export const TRADABILITY_CONFIG: Record<string, BadgeStyle> = {
  ACTIVE: {
    label: "Aktiv",
    bg: "bg-emerald-500/10 dark:bg-emerald-500/20",
    text: "text-emerald-700 dark:text-emerald-300",
    border: "border-emerald-500/30",
  },
  MERGED: {
    label: "Avnoterad (M&A)",
    bg: "bg-zinc-500/10 dark:bg-zinc-500/20",
    text: "text-zinc-600 dark:text-zinc-400",
    border: "border-zinc-500/30",
  },
  DELISTED: {
    label: "Avnoterad",
    bg: "bg-zinc-500/10 dark:bg-zinc-500/20",
    text: "text-zinc-600 dark:text-zinc-400",
    border: "border-zinc-500/30",
  },
  HALTED: {
    label: "Handelsstoppad",
    bg: "bg-amber-500/10 dark:bg-amber-500/20",
    text: "text-amber-700 dark:text-amber-300",
    border: "border-amber-500/30",
  },
  UNKNOWN: {
    label: "Verifiering krävs",
    bg: "bg-zinc-500/10 dark:bg-zinc-500/20",
    text: "text-zinc-500 dark:text-zinc-400",
    border: "border-zinc-500/30",
  },
};

export function badgeFor(config: Record<string, BadgeStyle>, key: string | undefined | null, fallback: BadgeStyle): BadgeStyle {
  if (!key) return fallback;
  return config[key] ?? fallback;
}

export const FALLBACK_THESIS = THESIS_BAND_CONFIG.NEUTRAL;
export const FALLBACK_SETUP = SETUP_STATE_CONFIG.INSUFFICIENT;
export const FALLBACK_RISK = RISK_STATE_CONFIG.CRITICAL;
export const FALLBACK_TRADABILITY = TRADABILITY_CONFIG.UNKNOWN;