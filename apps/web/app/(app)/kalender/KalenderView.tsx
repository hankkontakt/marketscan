"use client";

import { useState, useEffect, useCallback } from "react";
import { api } from "@/lib/api";
import {
  CalendarDays,
  TrendingUp,
  Globe,
  Banknote,
  Building2,
  AlertCircle,
  RotateCw,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { cn } from "@/lib/utils";

// ─── Types ───────────────────────────────────────────────────────────────────

type TabId = "earnings" | "ipo" | "economic" | "dividends";

interface Tab {
  id: TabId;
  label: string;
  icon: React.ElementType;
}

const TABS: Tab[] = [
  { id: "earnings", label: "Rapporter", icon: TrendingUp },
  { id: "ipo", label: "Börsnoteringar", icon: Building2 },
  { id: "economic", label: "Ekonomi", icon: Globe },
  { id: "dividends", label: "Utdelningar", icon: Banknote },
];

interface CalendarEventsResponse {
  events: Record<string, unknown>[];
}

// Strict event types
interface EarningsEvent {
  symbol?: string;
  quarter?: number;
  year?: number;
  date?: string;
  estimate?: number;
  actual?: number;
  lastYear?: number;
}

interface IpoEvent {
  name?: string;
  symbol?: string;
  exchange?: string;
  date?: string;
  price?: number;
  shares?: number;
}

interface EconomicEvent {
  event?: string;
  country?: string;
  currency?: string;
  date?: string;
  previous?: number | string;
  estimate?: number | string;
  actual?: number | string;
}

interface DividendEvent {
  symbol?: string;
  frequency?: string;
  date?: string;
  payDate?: string;
  amount?: number;
  exDate?: string;
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return "—";
  try {
    return new Date(dateStr).toLocaleDateString("sv-SE", {
      year: "numeric", month: "short", day: "numeric",
    });
  } catch { return dateStr; }
}

function formatDay(dateStr: string): string {
  try {
    const d = new Date(dateStr);
    const weekday = d.toLocaleDateString("sv-SE", { weekday: "long" });
    const day = d.toLocaleDateString("sv-SE", { day: "numeric", month: "long" });
    return `${weekday.charAt(0).toUpperCase() + weekday.slice(1)} ${day}`;
  } catch { return dateStr; }
}

function formatCurrency(val: unknown): string {
  if (val === null || val === undefined) return "—";
  const n = Number(val);
  if (isNaN(n)) return String(val);
  return n.toLocaleString("sv-SE", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function formatBigNumber(val: unknown): string {
  if (val === null || val === undefined) return "—";
  const n = Number(val);
  if (isNaN(n)) return String(val);
  if (n >= 1_000_000_000) return `${(n / 1_000_000_000).toFixed(1)}B`;
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  return n.toLocaleString("sv-SE");
}

function getEventDate(event: Record<string, unknown>, tab: TabId): string {
  const d = event.date as string | undefined;
  if (d) return d;
  if (tab === "dividends") return (event.payDate || event.exDate || "") as string;
  return "";
}

function getEventSymbol(event: Record<string, unknown>, tab: TabId): string {
  if (tab === "economic") return (event.country || event.event || "—") as string;
  return (event.symbol || event.name || "—") as string;
}

// ─── Skeleton ────────────────────────────────────────────────────────────────

function SkeletonDay() {
  return (
    <div className="animate-pulse space-y-3 mb-6">
      <div className="skeleton h-4 w-40 rounded" />
      <div className="skeleton h-12 rounded-lg" />
      <div className="skeleton h-12 rounded-lg" />
    </div>
  );
}

// ─── Main view ───────────────────────────────────────────────────────────────

export function KalenderView() {
  const [activeTab, setActiveTab] = useState<TabId>("earnings");
  const [events, setEvents] = useState<Record<string, unknown>[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [currentMonth, setCurrentMonth] = useState(() => {
    const n = new Date();
    return new Date(n.getFullYear(), n.getMonth(), 1);
  });

  const monthStart = currentMonth.toISOString().slice(0, 10);
  const monthEnd = new Date(currentMonth.getFullYear(), currentMonth.getMonth() + 1, 0).toISOString().slice(0, 10);
  const monthLabel = currentMonth.toLocaleDateString("sv-SE", { month: "long", year: "numeric" });

  const fetchEvents = useCallback(() => {
    setLoading(true);
    setError(null);
    api<CalendarEventsResponse>(`/api/calendar/${activeTab}?from_date=${monthStart}&to_date=${monthEnd}`)
      .then((data) => setEvents(data.events ?? []))
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : "Kunde inte ladda kalenderdata");
        setEvents([]);
      })
      .finally(() => setLoading(false));
  }, [activeTab, monthStart, monthEnd]);

  useEffect(() => { fetchEvents(); }, [fetchEvents]);

  function prevMonth() { setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() - 1, 1)); }
  function nextMonth() { setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() + 1, 1)); }
  function isNextDisabled() {
    const now = new Date();
    return currentMonth.getFullYear() >= now.getFullYear() + 1;
  }

  // Group events by date
  const grouped = events.reduce<Record<string, Record<string, unknown>[]>>((acc, ev) => {
    const d = getEventDate(ev, activeTab);
    if (!d) return acc;
    if (!acc[d]) acc[d] = [];
    acc[d].push(ev);
    return acc;
  }, {});
  const sortedDates = Object.keys(grouped).sort();

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center gap-2">
        <CalendarDays size={18} className="text-[var(--color-accent)]" />
        <h1 className="text-lg font-semibold text-[var(--color-text-primary)]">Kalender</h1>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 p-1 rounded-xl bg-[var(--color-bg-elevated)]" role="tablist">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            role="tab"
            aria-selected={activeTab === tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={cn(
              "flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium transition-colors flex-1 justify-center",
              activeTab === tab.id
                ? "bg-[var(--color-bg-surface)] text-[var(--color-accent)] shadow-sm"
                : "text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]",
            )}
          >
            <tab.icon size={14} strokeWidth={1.5} />
            {tab.label}
          </button>
        ))}
      </div>

      {/* Month navigator */}
      <div className="flex items-center justify-between">
        <button onClick={prevMonth} className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-elevated)] transition-colors">
          <ChevronLeft size={14} strokeWidth={1.5} />
          Föregående
        </button>
        <span className="text-sm font-semibold text-[var(--color-text-primary)] capitalize">{monthLabel}</span>
        <button onClick={nextMonth} disabled={isNextDisabled()} className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-elevated)] transition-colors disabled:opacity-30">
          Nästa
          <ChevronRight size={14} strokeWidth={1.5} />
        </button>
      </div>

      {/* Content */}
      <div role="tabpanel" className="space-y-1">
        {loading && (
          <div className="space-y-3" aria-busy="true">
            {Array.from({ length: 3 }).map((_, i) => <SkeletonDay key={i} />)}
          </div>
        )}

        {!loading && error && (
          <div className="rounded-xl border p-6 bg-[var(--color-bg-surface)] border-[var(--color-border)]">
            <div className="flex flex-col items-center gap-3 text-center">
              <AlertCircle size={28} className="text-[var(--color-score-low)]" />
              <p className="text-sm text-[var(--color-text-secondary)]">{error}</p>
              <button onClick={fetchEvents} className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-[var(--color-accent-soft)] text-[var(--color-accent)] hover:opacity-80 transition-opacity">
                <RotateCw size={12} /> Försök igen
              </button>
            </div>
          </div>
        )}

        {!loading && !error && sortedDates.length === 0 && (
          <div className="flex flex-col items-center py-16 text-center">
            <CalendarDays size={36} strokeWidth={1.5} className="text-[var(--color-text-muted)] mb-3" />
            <p className="text-sm font-medium text-[var(--color-text-secondary)]">Inga händelser</p>
            <p className="text-xs text-[var(--color-text-muted)] mt-1">Inga händelser denna månad.</p>
          </div>
        )}

        {!loading && !error && sortedDates.length > 0 && (
          <div>
            {sortedDates.map((dateStr) => {
              const dayEvents = grouped[dateStr];
              return (
                <div key={dateStr} className="mb-4">
                  {/* Date header */}
                  <div className="flex items-center gap-2 mb-2 sticky top-0 bg-[var(--color-bg-base)] py-2 z-10">
                    <span className="text-xs font-semibold text-[var(--color-text-primary)]">{formatDay(dateStr)}</span>
                    <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-[var(--color-bg-elevated)] text-[var(--color-text-muted)]">
                      {dayEvents.length} {dayEvents.length === 1 ? "händelse" : "händelser"}
                    </span>
                  </div>

                  {/* Events for this day */}
                  <div className="space-y-1">
                    {dayEvents.map((ev, i) => (
                      <EventRow key={`${getEventSymbol(ev, activeTab)}-${i}`} event={ev} tab={activeTab} />
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {!loading && !error && events.length > 0 && (
        <p className="text-[10px] text-[var(--color-text-muted)] text-center">Data från Finnhub. {events.length} händelser visas.</p>
      )}
    </div>
  );
}

// ─── Compact event row ───────────────────────────────────────────────────────

function EventRow({ event, tab }: { event: Record<string, unknown>; tab: TabId }) {
  switch (tab) {
    case "earnings": return <EarningsRow event={event as unknown as EarningsEvent} />;
    case "ipo": return <IpoRow event={event as unknown as IpoEvent} />;
    case "economic": return <EconomicRow event={event as unknown as EconomicEvent} />;
    case "dividends": return <DividendsRow event={event as unknown as DividendEvent} />;
  }
}

function EarningsRow({ event }: { event: EarningsEvent }) {
  return (
    <div className="flex items-center gap-3 px-3 py-2.5 rounded-lg bg-[var(--color-bg-surface)] border border-[var(--color-border)] hover:border-[var(--color-accent)]/30 transition-colors">
      <div className="flex-1 min-w-0 flex items-center gap-2">
        <span className="text-xs font-semibold text-[var(--color-text-primary)]">{event.symbol || "—"}</span>
        <span className="text-[10px] text-[var(--color-text-muted)]">{event.quarter ? `Q${event.quarter}` : ""}{event.year ? ` ${event.year}` : ""}</span>
      </div>
      <div className="flex items-center gap-4 text-[11px] font-mono tabular">
        <span className="text-[var(--color-text-muted)]">Est: {formatCurrency(event.estimate)}</span>
        <span className={cn(event.actual != null && event.estimate != null && event.actual > event.estimate ? "text-[var(--color-up)]" : "text-[var(--color-text-secondary)]")}>
          {formatCurrency(event.actual)}
        </span>
      </div>
    </div>
  );
}

function IpoRow({ event }: { event: IpoEvent }) {
  return (
    <div className="flex items-center gap-3 px-3 py-2.5 rounded-lg bg-[var(--color-bg-surface)] border border-[var(--color-border)] hover:border-[var(--color-accent)]/30 transition-colors">
      <div className="flex-1 min-w-0 flex items-center gap-2">
        <span className="text-xs font-semibold text-[var(--color-text-primary)]">{event.name || event.symbol || "—"}</span>
        {event.symbol && <span className="text-[10px] font-mono text-[var(--color-text-muted)]">{event.symbol}</span>}
        {event.exchange && <span className="text-[10px] text-[var(--color-text-muted)]">{event.exchange}</span>}
      </div>
      <div className="flex items-center gap-4 text-[11px] font-mono tabular">
        {event.price != null && <span className="text-[var(--color-text-muted)]">{formatCurrency(event.price)} USD</span>}
        {event.shares != null && <span className="text-[var(--color-text-muted)]">{formatBigNumber(event.shares)} aktier</span>}
      </div>
    </div>
  );
}

function EconomicRow({ event }: { event: EconomicEvent }) {
  return (
    <div className="flex items-center gap-3 px-3 py-2.5 rounded-lg bg-[var(--color-bg-surface)] border border-[var(--color-border)] hover:border-[var(--color-accent)]/30 transition-colors">
      <div className="flex-1 min-w-0 flex items-center gap-2">
        <span className="text-xs font-semibold text-[var(--color-text-primary)] truncate">{event.event || "—"}</span>
        {event.country && <span className="text-[10px] text-[var(--color-text-muted)]">{event.country}</span>}
      </div>
      <div className="flex items-center gap-3 text-[11px] font-mono tabular">
        {event.previous != null && <span className="text-[var(--color-text-muted)]">Fg: {String(event.previous)}</span>}
        {event.estimate != null && <span className="text-[var(--color-text-muted)]">Est: {String(event.estimate)}</span>}
        {event.actual != null && <span className="text-[var(--color-text-secondary)]">{String(event.actual)}</span>}
      </div>
    </div>
  );
}

function DividendsRow({ event }: { event: DividendEvent }) {
  return (
    <div className="flex items-center gap-3 px-3 py-2.5 rounded-lg bg-[var(--color-bg-surface)] border border-[var(--color-border)] hover:border-[var(--color-accent)]/30 transition-colors">
      <div className="flex-1 min-w-0 flex items-center gap-2">
        <span className="text-xs font-semibold text-[var(--color-text-primary)]">{event.symbol || "—"}</span>
        {event.frequency && <span className="text-[10px] text-[var(--color-text-muted)]">{event.frequency}</span>}
      </div>
      <div className="flex items-center gap-4 text-[11px] font-mono tabular">
        {event.amount != null && <span className="text-[var(--color-text-secondary)]">{formatCurrency(event.amount)}</span>}
        {event.exDate && <span className="text-[var(--color-text-muted)]">X-dag: {formatDate(event.exDate)}</span>}
      </div>
    </div>
  );
}
