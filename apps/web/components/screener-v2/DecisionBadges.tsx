import { ThesisBand, SetupState, RiskState, DataGrade } from '@/lib/types/decision_v2';

export const THESIS_BAND_CONFIG: Record<
  ThesisBand,
  { label: string; bg: string; text: string; border: string }
> = {
  EXCEPTIONAL: {
    label: 'Exceptionell',
    bg: 'bg-emerald-500/10 dark:bg-emerald-500/20',
    text: 'text-emerald-700 dark:text-emerald-300',
    border: 'border-emerald-500/30',
  },
  STRONG: {
    label: 'Stark tes',
    bg: 'bg-teal-500/10 dark:bg-teal-500/20',
    text: 'text-teal-700 dark:text-teal-300',
    border: 'border-teal-500/30',
  },
  POSITIVE: {
    label: 'Positiv',
    bg: 'bg-blue-500/10 dark:bg-blue-500/20',
    text: 'text-blue-700 dark:text-blue-300',
    border: 'border-blue-500/30',
  },
  MIXED: {
    label: 'Blandad',
    bg: 'bg-zinc-500/10 dark:bg-zinc-500/20',
    text: 'text-zinc-700 dark:text-zinc-300',
    border: 'border-zinc-500/30',
  },
  WEAK: {
    label: 'Svag',
    bg: 'bg-amber-500/10 dark:bg-amber-500/20',
    text: 'text-amber-700 dark:text-amber-300',
    border: 'border-amber-500/30',
  },
  INSUFFICIENT: {
    label: 'Otillräcklig',
    bg: 'bg-rose-500/10 dark:bg-rose-500/20',
    text: 'text-rose-700 dark:text-rose-300',
    border: 'border-rose-500/30',
  },
};

export const SETUP_STATE_CONFIG: Record<
  SetupState,
  { label: string; bg: string; text: string; border: string }
> = {
  CONFIRMED: {
    label: 'Bekräftad trend',
    bg: 'bg-emerald-500/10 dark:bg-emerald-500/20',
    text: 'text-emerald-700 dark:text-emerald-300',
    border: 'border-emerald-500/30',
  },
  PULLBACK: {
    label: 'Kontrollerad rekyl',
    bg: 'bg-indigo-500/10 dark:bg-indigo-500/20',
    text: 'text-indigo-700 dark:text-indigo-300',
    border: 'border-indigo-500/30',
  },
  NEUTRAL: {
    label: 'Neutral setup',
    bg: 'bg-zinc-500/10 dark:bg-zinc-500/20',
    text: 'text-zinc-700 dark:text-zinc-300',
    border: 'border-zinc-500/30',
  },
  EXTENDED: {
    label: 'Utsträckt',
    bg: 'bg-amber-500/10 dark:bg-amber-500/20',
    text: 'text-amber-700 dark:text-amber-300',
    border: 'border-amber-500/30',
  },
  DAMAGED: {
    label: 'Skadad prisbild',
    bg: 'bg-rose-500/10 dark:bg-rose-500/20',
    text: 'text-rose-700 dark:text-rose-300',
    border: 'border-rose-500/30',
  },
  EVENT_RISK: {
    label: 'Rapport nära',
    bg: 'bg-purple-500/10 dark:bg-purple-500/20',
    text: 'text-purple-700 dark:text-purple-300',
    border: 'border-purple-500/30',
  },
  INSUFFICIENT: {
    label: 'Otillräcklig data',
    bg: 'bg-zinc-500/10 dark:bg-zinc-500/20',
    text: 'text-zinc-500 dark:text-zinc-400',
    border: 'border-zinc-500/30',
  },
};

export const RISK_STATE_CONFIG: Record<
  RiskState,
  { label: string; bg: string; text: string; border: string }
> = {
  LOW: {
    label: 'Låg risk',
    bg: 'bg-emerald-500/10 dark:bg-emerald-500/20',
    text: 'text-emerald-700 dark:text-emerald-300',
    border: 'border-emerald-500/30',
  },
  MEDIUM: {
    label: 'Måttlig',
    bg: 'bg-blue-500/10 dark:bg-blue-500/20',
    text: 'text-blue-700 dark:text-blue-300',
    border: 'border-blue-500/30',
  },
  HIGH: {
    label: 'Förhöjd',
    bg: 'bg-amber-500/10 dark:bg-amber-500/20',
    text: 'text-amber-700 dark:text-amber-300',
    border: 'border-amber-500/30',
  },
  VERY_HIGH: {
    label: 'Hög risk',
    bg: 'bg-rose-500/10 dark:bg-rose-500/20',
    text: 'text-rose-700 dark:text-rose-300',
    border: 'border-rose-500/30',
  },
  EVENT: {
    label: 'Eventrisk',
    bg: 'bg-purple-500/10 dark:bg-purple-500/20',
    text: 'text-purple-700 dark:text-purple-300',
    border: 'border-purple-500/30',
  },
  INSUFFICIENT: {
    label: 'Okänd risk',
    bg: 'bg-zinc-500/10 dark:bg-zinc-500/20',
    text: 'text-zinc-500 dark:text-zinc-400',
    border: 'border-zinc-500/30',
  },
};

export const DATA_GRADE_CONFIG: Record<
  DataGrade,
  { label: string; bg: string; text: string }
> = {
  A: { label: 'A', bg: 'bg-emerald-500/15', text: 'text-emerald-600 dark:text-emerald-400' },
  B: { label: 'B', bg: 'bg-teal-500/15', text: 'text-teal-600 dark:text-teal-400' },
  C: { label: 'C', bg: 'bg-blue-500/15', text: 'text-blue-600 dark:text-blue-400' },
  D: { label: 'D', bg: 'bg-amber-500/15', text: 'text-amber-600 dark:text-amber-400' },
  E: { label: 'E', bg: 'bg-rose-500/15', text: 'text-rose-600 dark:text-rose-400' },
  F: { label: 'F', bg: 'bg-rose-500/20', text: 'text-rose-700 dark:text-rose-300' },
};
