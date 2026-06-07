"use client";

import { useState, useEffect, useCallback, useMemo } from "react";
import { api } from "@/lib/api";
import {
  CalendarDays,
  TrendingUp,
  Globe,
  Banknote,
  Building2,
  ChevronLeft,
  ChevronRight,
  RotateCw,
  AlertCircle,
} from "lucide-react";
import { cn } from "@/lib/utils";
import {
  startOfMonth, endOfMonth, eachDayOfInterval,
  startOfWeek, endOfWeek, format, isSameMonth, isSameDay,
} from "date-fns";
import { sv } from "date-fns/locale";

// ─── Types ───────────────────────────────────────────────────────────────────

type EventType = "earnings" | "dividends" | "ipo" | "economic";

interface DayEvent {
  type: EventType;
  symbol?: string;
  name?: string;
  title?: string;
  date?: string;
  price?: number;
  estimate?: number;
  actual?: number;
  exDate?: string;
  amount?: number;
  exchange?: string;
  [key: string]: unknown;
}

interface CalendarResponse {
  events: Record<string, unknown>[];
}

const EVENT_TYPES: { key: EventType; label: string; color: string }[] = [
  { key: "earnings", label: "Rapporter", color: "var(--color-accent)" },
  { key: "dividends", label: "Utdelningar", color: "var(--color-chart-3)" },
  { key: "ipo", label: "Börsnoteringar", color: "var(--color-up)" },
  { key: "economic", label: "Ekonomi", color: "var(--color-chart-7)" },
];

const TYPE_COLORS: Record<EventType, string> = {
  earnings: "var(--color-accent)",
  dividends: "var(--color-chart-3)",
  ipo: "var(--color-up)",
  economic: "var(--color-chart-7)",
};

// ─── Helpers ─────────────────────────────────────────────────────────────────

function formatCurrency(val: unknown): string {
  if (val == null) return "—";
  const n = Number(val);
  if (isNaN(n)) return String(val);
  return n.toLocaleString("sv-SE", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function getEventTitle(event: DayEvent): string {
  if (event.symbol) return event.symbol;
  if (event.name) return event.name;
  if (event.title) return event.title;
  return "—";
}

// ─── Skeleton ────────────────────────────────────────────────────────────────

function SkeletonGrid() {
  return (
    <div className="animate-pulse space-y-2">
      <div className="flex gap-1 mb-1">
        {["Mån", "Tis", "Ons", "Tor", "Fre", "Lör", "Sön"].map((d) => (
          <div key={d} className="flex-1 skeleton h-3 rounded" />
        ))}
      </div>
      {Array.from({ length: 5 }).map((_, w) => (
        <div key={w} className="flex gap-1">
          {Array.from({ length: 7 }).map((_, d) => (
            <div key={d} className="flex-1 skeleton h-20 rounded-lg" />
          ))}
        </div>
      ))}
    </div>
  );
}

// ─── Main View ───────────────────────────────────────────────────────────────

export function KalenderView() {
  const [scope, setScope] = useState<"mine" | "all">("mine");
  const [eventsByDate, setEventsByDate] = useState<Record<string, DayEvent[]>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [currentMonth, setCurrentMonth] = useState(() => {
    const n = new Date();
    return new Date(n.getFullYear(), n.getMonth(), 1);
  });
  const [selectedDay, setSelectedDay] = useState<string | null>(null);

  const monthStart = currentMonth.toISOString().slice(0, 10);
  const monthEnd = new Date(currentMonth.getFullYear(), currentMonth.getMonth() + 1, 0).toISOString().slice(0, 10);
  const monthLabel = format(currentMonth, "MMMM yyyy", { locale: sv });

  const prevMonth = () => setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() - 1, 1));
  const nextMonth = () => setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() + 1, 1));
  const isNextDisabled = () => {
    const now = new Date();
    return currentMonth.getFullYear() >= now.getFullYear() + 1;
  };

  // Build month grid
  const gridDays = useMemo(() => {
    const gridStart = startOfWeek(startOfMonth(currentMonth), { weekStartsOn: 1 });
    const gridEnd = endOfWeek(endOfMonth(currentMonth), { weekStartsOn: 1 });
    return eachDayOfInterval({ start: gridStart, end: gridEnd });
  }, [currentMonth]);

  const fetchAllEvents = useCallback(async () => {
    setLoading(true);
    setError(null);

    const scopeParam = `&scope=${scope}`;

    try {
      const [earningsData, dividendsData, ipoData, economicData] = await Promise.all([
        api<CalendarResponse>(`/api/calendar/earnings?from_date=${monthStart}&to_date=${monthEnd}${scopeParam}`),
        api<CalendarResponse>(`/api/calendar/dividends?from_date=${monthStart}&to_date=${monthEnd}${scopeParam}`),
        api<CalendarResponse>(`/api/calendar/ipo?from_date=${monthStart}&to_date=${monthEnd}`),
        api<CalendarResponse>(`/api/calendar/economic?from_date=${monthStart}&to_date=${monthEnd}`),
      ]);

      // Index all events by date
      const byDate: Record<string, DayEvent[]> = {};

      const addEvents = (list: Record<string, unknown>[], type: EventType, dateField: string) => {
        for (const ev of list) {
          const d = (ev[dateField] as string) || (ev.date as string);
          if (!d) continue;
          const key = d.slice(0, 10);
          if (!byDate[key]) byDate[key] = [];
          byDate[key].push({ ...ev, type } as DayEvent);
        }
      };

      addEvents(earningsData.events, "earnings", "date");
      addEvents(dividendsData.events, "dividends", "payDate");
      addEvents(ipoData.events, "ipo", "date");
      addEvents(economicData.events, "economic", "date");

      setEventsByDate(byDate);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Kunde inte ladda kalenderdata");
      setEventsByDate({});
    } finally {
      setLoading(false);
    }
  }, [scope, monthStart, monthEnd]);

  useEffect(() => { fetchAllEvents(); }, [fetchAllEvents]);

  const selectedEvents = selectedDay ? (eventsByDate[selectedDay] || []) : [];

  // Count event types on a given day for dot display
  const dayEventTypes = (dayStr: string): EventType[] => {
    const dayEvents = eventsByDate[dayStr];
    if (!dayEvents) return [];
    const seen = new Set<EventType>();
    for (const ev of dayEvents) {
      seen.add(ev.type);
    }
    return Array.from(seen);
  };

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center gap-2">
        <CalendarDays size={18} className="text-[var(--color-accent)]" />
        <h1 className="text-lg font-semibold text-[var(--color-text-primary)]">Kalender</h1>
      </div>

      {/* Scope toggle */}
      <div className="flex p-0.5 rounded-xl bg-[var(--color-bg-elevated)] w-fit">
        <button
          onClick={() => setScope("mine")}
          className={cn(
            "px-4 py-1.5 rounded-lg text-xs font-medium transition-colors",
            scope === "mine"
              ? "bg-[var(--color-bg-surface)] text-[var(--color-accent)] shadow-sm"
              : "text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]",
          )}
        >
          Mina aktier
        </button>
        <button
          onClick={() => setScope("all")}
          className={cn(
            "px-4 py-1.5 rounded-lg text-xs font-medium transition-colors",
            scope === "all"
              ? "bg-[var(--color-bg-surface)] text-[var(--color-accent)] shadow-sm"
              : "text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]",
          )}
        >
          Alla
        </button>
      </div>

      {/* Legend */}
      <div className="flex gap-4 text-[11px] text-[var(--color-text-secondary)]">
        {EVENT_TYPES.map((et) => (
          <div key={et.key} className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full" style={{ background: et.color }} />
            {et.label}
          </div>
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

      {/* Error */}
      {error && !loading && (
        <div className="rounded-xl border p-4 bg-[var(--color-bg-surface)] border-[var(--color-border)]">
          <div className="flex flex-col items-center gap-2 text-center">
            <AlertCircle size={22} className="text-[var(--color-score-low)]" />
            <p className="text-xs text-[var(--color-text-secondary)]">{error}</p>
            <button onClick={fetchAllEvents} className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-[var(--color-accent-soft)] text-[var(--color-accent)] hover:opacity-80 transition-opacity">
              <RotateCw size={12} /> Försök igen
            </button>
          </div>
        </div>
      )}

      {/* Loading */}
      {loading && <SkeletonGrid />}

      {/* Month grid */}
      {!loading && !error && (
        <>
          {/* Day headers */}
          <div className="grid grid-cols-7 gap-px mb-px">
            {["Mån", "Tis", "Ons", "Tor", "Fre", "Lör", "Sön"].map((d) => (
              <div key={d} className="text-center text-[10px] text-[var(--color-text-muted)] py-1">
                {d}
              </div>
            ))}
          </div>

          <div className="grid grid-cols-7 gap-px">
            {gridDays.map((day) => {
              const dayStr = format(day, "yyyy-MM-dd");
              const inMonth = isSameMonth(day, currentMonth);
              const today = isSameDay(day, new Date());
              const types = dayEventTypes(dayStr);
              const totalEvents = eventsByDate[dayStr]?.length || 0;

              return (
                <button
                  key={dayStr}
                  onClick={() => setSelectedDay(dayStr)}
                  className={cn(
                    "relative flex flex-col items-center py-1.5 rounded-lg text-xs transition-colors min-h-[56px]",
                    "hover:bg-[var(--color-bg-elevated)]",
                    inMonth ? "text-[var(--color-text-primary)]" : "text-[var(--color-text-muted)]",
                    today && "ring-1 ring-[var(--color-accent)]",
                    selectedDay === dayStr && "bg-[var(--color-accent-soft)]",
                  )}
                >
                  <span className={cn(
                    "text-xs",
                    today && "font-bold text-[var(--color-accent)]",
                  )}>
                    {format(day, "d")}
                  </span>
                  {types.length > 0 && (
                    <div className="flex gap-0.5 mt-0.5 flex-wrap justify-center">
                      {types.slice(0, 3).map((t) => (
                        <span
                          key={t}
                          className="w-1.5 h-1.5 rounded-full"
                          style={{ background: TYPE_COLORS[t] }}
                        />
                      ))}
                      {totalEvents > 3 && (
                        <span className="text-[8px] text-[var(--color-text-muted)] leading-none">
                          +{totalEvents - 3}
                        </span>
                      )}
                    </div>
                  )}
                </button>
              );
            })}
          </div>
        </>
      )}

      {/* Day detail dialog */}
      {selectedDay && (
        <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/30" onClick={() => setSelectedDay(null)}>
          <div
            className="w-full sm:max-w-lg max-h-[60vh] sm:rounded-2xl rounded-t-2xl bg-[var(--color-bg-base)] border border-[var(--color-border)] overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between px-5 py-4 border-b border-[var(--color-border)]">
              <span className="text-sm font-semibold text-[var(--color-text-primary)]">
                {format(new Date(selectedDay + "T12:00:00"), "EEEE d MMMM", { locale: sv })}
              </span>
              <button onClick={() => setSelectedDay(null)} className="text-xs text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]">
                Stäng
              </button>
            </div>
            <div className="overflow-y-auto p-4 space-y-2 max-h-[50vh]">
              {selectedEvents.length === 0 ? (
                <p className="text-xs text-[var(--color-text-muted)] text-center py-8">Inga händelser denna dag</p>
              ) : (
                selectedEvents.map((ev, i) => (
                  <DayEventRow key={`${getEventTitle(ev)}-${i}`} event={ev} />
                ))
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Day Event Row ───────────────────────────────────────────────────────────

function DayEventRow({ event }: { event: DayEvent }) {
  const color = TYPE_COLORS[event.type] || "var(--color-text-muted)";
  const typeLabel = EVENT_TYPES.find((et) => et.key === event.type)?.label || event.type;

  return (
    <div
      className="flex items-start gap-3 px-3 py-2.5 rounded-lg bg-[var(--color-bg-surface)] border border-[var(--color-border)]"
    >
      <span className="w-2 h-2 rounded-full mt-1.5 shrink-0" style={{ background: color }} />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-[var(--color-text-primary)]">
            {getEventTitle(event)}
          </span>
          <span className="text-[10px] text-[var(--color-text-muted)]">{typeLabel}</span>
        </div>
        <EventDetail event={event} />
      </div>
    </div>
  );
}

function EventDetail({ event }: { event: DayEvent }) {
  switch (event.type) {
    case "earnings":
      return (
        <div className="flex gap-3 mt-1 text-[11px] font-mono tabular">
          {event.estimate != null && (
            <span className="text-[var(--color-text-muted)]">Est: {formatCurrency(event.estimate)}</span>
          )}
          {event.actual != null && (
            <span className={cn(
              Number(event.actual) >= Number(event.estimate || 0) ? "text-[var(--color-up)]" : "text-[var(--color-text-secondary)]"
            )}>
              {formatCurrency(event.actual)}
            </span>
          )}
        </div>
      );
    case "dividends":
      return (
        <div className="flex gap-3 mt-1 text-[11px] font-mono tabular text-[var(--color-text-muted)]">
          {event.amount != null && <span>{formatCurrency(event.amount)}</span>}
          {event.exDate && <span>X-dag: {event.exDate as string}</span>}
        </div>
      );
    case "ipo":
      return (
        <div className="flex gap-3 mt-1 text-[11px] font-mono tabular text-[var(--color-text-muted)]">
          {event.price != null && <span>{formatCurrency(event.price)} USD</span>}
          {event.exchange && <span>{event.exchange as string}</span>}
        </div>
      );
    default:
      return null;
  }
}
