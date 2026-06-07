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

// ─── Helpers ─────────────────────────────────────────────────────────────────

function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return "—";
  try {
    return new Date(dateStr).toLocaleDateString("sv-SE", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  } catch {
    return dateStr;
  }
}

function formatCurrency(val: unknown): string {
  if (val === null || val === undefined) return "—";
  const n = Number(val);
  if (isNaN(n)) return String(val);
  return n.toLocaleString("sv-SE", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function formatNumber(val: unknown): string {
  if (val === null || val === undefined) return "—";
  const n = Number(val);
  if (isNaN(n)) return String(val);
  return n.toLocaleString("sv-SE");
}

// ─── Event card sub-components ───────────────────────────────────────────────

function EarningsCard({ event }: { event: Record<string, unknown> }) {
  return (
    <div className="rounded-xl border p-4 bg-[var(--color-bg-surface)] border-[var(--color-border)]">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-[var(--color-text-primary)]">
            {String(event.symbol ?? "—")}
          </p>
          <p className="text-xs text-[var(--color-text-muted)] mt-0.5">
            {event.quarter ? `Q${event.quarter} ` : ""}
            {event.year ? String(event.year) : ""}
          </p>
        </div>
        <span className="text-[11px] text-[var(--color-text-muted)] whitespace-nowrap">
          {formatDate(event.date as string | null | undefined)}
        </span>
      </div>
      <div className="grid grid-cols-3 gap-3 mt-3 text-xs">
        <div>
          <span className="text-[var(--color-text-muted)]">Estimat</span>
          <p className="font-mono text-[var(--color-text-secondary)] mt-0.5">
            {formatCurrency(event.estimate)}
          </p>
        </div>
        <div>
          <span className="text-[var(--color-text-muted)]">Utfall</span>
          <p className="font-mono text-[var(--color-text-secondary)] mt-0.5">
            {formatCurrency(event.actual)}
          </p>
        </div>
        <div>
          <span className="text-[var(--color-text-muted)]">Fjol</span>
          <p className="font-mono text-[var(--color-text-secondary)] mt-0.5">
            {formatCurrency(event.lastYear)}
          </p>
        </div>
      </div>
    </div>
  );
}

function IpoCard({ event }: { event: Record<string, unknown> }) {
  return (
    <div className="rounded-xl border p-4 bg-[var(--color-bg-surface)] border-[var(--color-border)]">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-[var(--color-text-primary)]">
            {String(event.name ?? event.symbol ?? "—")}
          </p>
          <p className="text-xs text-[var(--color-text-muted)] mt-0.5">
            {String(event.symbol ?? "")}
            {event.exchange ? ` · ${event.exchange}` : ""}
          </p>
        </div>
        <span className="text-[11px] text-[var(--color-text-muted)] whitespace-nowrap">
          {formatDate(event.date as string | null | undefined)}
        </span>
      </div>
      <div className="grid grid-cols-2 gap-3 mt-3 text-xs">
        <div>
          <span className="text-[var(--color-text-muted)]">Pris</span>
          <p className="font-mono text-[var(--color-text-secondary)] mt-0.5">
            {event.price ? `${formatCurrency(event.price)} USD` : "—"}
          </p>
        </div>
        <div>
          <span className="text-[var(--color-text-muted)]">Aktier</span>
          <p className="font-mono text-[var(--color-text-secondary)] mt-0.5">
            {event.shares ? formatNumber(event.shares) : "—"}
          </p>
        </div>
      </div>
    </div>
  );
}

function EconomicCard({ event }: { event: Record<string, unknown> }) {
  return (
    <div className="rounded-xl border p-4 bg-[var(--color-bg-surface)] border-[var(--color-border)]">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <p className="text-sm font-semibold text-[var(--color-text-primary)] truncate">
            {String(event.event ?? "—")}
          </p>
          <p className="text-xs text-[var(--color-text-muted)] mt-0.5">
            {String(event.country ?? "")}
            {event.currency ? ` · ${event.currency}` : ""}
          </p>
        </div>
        <span className="text-[11px] text-[var(--color-text-muted)] whitespace-nowrap shrink-0">
          {formatDate(event.date as string | null | undefined)}
        </span>
      </div>
      <div className="grid grid-cols-3 gap-3 mt-3 text-xs">
        <div>
          <span className="text-[var(--color-text-muted)]">Föregående</span>
          <p className="font-mono text-[var(--color-text-secondary)] mt-0.5">
            {event.previous != null ? String(event.previous) : "—"}
          </p>
        </div>
        <div>
          <span className="text-[var(--color-text-muted)]">Estimat</span>
          <p className="font-mono text-[var(--color-text-secondary)] mt-0.5">
            {event.estimate != null ? String(event.estimate) : "—"}
          </p>
        </div>
        <div>
          <span className="text-[var(--color-text-muted)]">Utfall</span>
          <p className="font-mono text-[var(--color-text-secondary)] mt-0.5">
            {event.actual != null ? String(event.actual) : "—"}
          </p>
        </div>
      </div>
    </div>
  );
}

function DividendsCard({ event }: { event: Record<string, unknown> }) {
  return (
    <div className="rounded-xl border p-4 bg-[var(--color-bg-surface)] border-[var(--color-border)]">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-[var(--color-text-primary)]">
            {String(event.symbol ?? "—")}
          </p>
          {event.frequency != null && (
            <p className="text-xs text-[var(--color-text-muted)] mt-0.5">
              {String(event.frequency)}
            </p>
          )}
        </div>
        <span className="text-[11px] text-[var(--color-text-muted)] whitespace-nowrap">
          {formatDate((event.payDate ?? event.date) as string | null | undefined)}
        </span>
      </div>
      <div className="grid grid-cols-2 gap-3 mt-3 text-xs">
        <div>
          <span className="text-[var(--color-text-muted)]">Belopp</span>
          <p className="font-mono text-[var(--color-text-secondary)] mt-0.5">
            {event.amount ? formatCurrency(event.amount) : "—"}
          </p>
        </div>
        <div>
          <span className="text-[var(--color-text-muted)]">Avstämningsdag</span>
          <p className="font-mono text-[var(--color-text-secondary)] mt-0.5">
            {formatDate(event.exDate as string | null | undefined)}
          </p>
        </div>
      </div>
    </div>
  );
}

// ─── Skeleton ────────────────────────────────────────────────────────────────

function SkeletonCard() {
  return (
    <div className="rounded-xl border p-4 bg-[var(--color-bg-surface)] border-[var(--color-border)] animate-pulse">
      <div className="flex items-start justify-between">
        <div className="space-y-2">
          <div className="skeleton h-4 w-24 rounded" />
          <div className="skeleton h-3 w-16 rounded" />
        </div>
        <div className="skeleton h-3 w-20 rounded" />
      </div>
      <div className="grid grid-cols-3 gap-3 mt-3">
        <div className="skeleton h-8 rounded" />
        <div className="skeleton h-8 rounded" />
        <div className="skeleton h-8 rounded" />
      </div>
    </div>
  );
}

// ─── Empty state ─────────────────────────────────────────────────────────────

function EmptyState({ tab }: { tab: Tab }) {
  const messages: Record<TabId, { title: string; desc: string }> = {
    earnings: {
      title: "Inga rapporter",
      desc: "Inga kommande rapporter funna för den valda perioden.",
    },
    ipo: {
      title: "Inga börsnoteringar",
      desc: "Inga kommande IPO:er funna för den valda perioden.",
    },
    economic: {
      title: "Inga ekonomiska händelser",
      desc: "Inga ekonomiska kalenderhändelser funna för den valda perioden.",
    },
    dividends: {
      title: "Utdelningskalender kommer snart",
      desc: "Stöd för utdelningskalender är under utveckling och kommer inom kort.",
    },
  };

  const msg = messages[tab.id];
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <tab.icon
        size={36}
        strokeWidth={1.5}
        className="text-[var(--color-text-muted)] mb-3"
      />
      <p className="text-sm font-medium text-[var(--color-text-secondary)]">
        {msg.title}
      </p>
      <p className="text-xs text-[var(--color-text-muted)] mt-1 max-w-xs">
        {msg.desc}
      </p>
    </div>
  );
}

// ─── Main view ───────────────────────────────────────────────────────────────

export function KalenderView() {
  const [activeTab, setActiveTab] = useState<TabId>("earnings");
  const [events, setEvents] = useState<Record<string, unknown>[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchEvents = useCallback(() => {
    if (activeTab === "dividends") {
      setLoading(false);
      setEvents([]);
      setError(null);
      return;
    }

    setLoading(true);
    setError(null);

    api<CalendarEventsResponse>(`/api/calendar/${activeTab}`)
      .then((data) => {
        setEvents(data.events ?? []);
      })
      .catch((err: unknown) => {
        const message =
          err instanceof Error ? err.message : "Kunde inte ladda kalenderdata";
        setError(message);
        setEvents([]);
      })
      .finally(() => setLoading(false));
  }, [activeTab]);

  useEffect(() => {
    fetchEvents();
  }, [fetchEvents]);

  // Determine which card renderer to use
  const currentTab = TABS.find((t) => t.id === activeTab)!;

  function renderEvent(event: Record<string, unknown>, index: number) {
    switch (activeTab) {
      case "earnings":
        return <EarningsCard key={`${event.symbol}-${event.date}-${index}`} event={event} />;
      case "ipo":
        return <IpoCard key={`${event.symbol}-${event.date}-${index}`} event={event} />;
      case "economic":
        return <EconomicCard key={`${event.event}-${event.date}-${index}`} event={event} />;
      case "dividends":
        return <DividendsCard key={`${event.symbol}-${index}`} event={event} />;
    }
  }

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-center gap-2">
        <CalendarDays size={18} className="text-[var(--color-accent)]" />
        <h1 className="text-lg font-semibold text-[var(--color-text-primary)]">
          Kalender
        </h1>
      </div>

      {/* Tab bar */}
      <div
        className="flex gap-1 p-1 rounded-xl bg-[var(--color-bg-elevated)]"
        role="tablist"
        aria-label="Kalendertyper"
      >
        {TABS.map((tab) => {
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              role="tab"
              aria-selected={isActive}
              aria-controls={`panel-${tab.id}`}
              onClick={() => setActiveTab(tab.id)}
              className={cn(
                "flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium transition-colors flex-1 justify-center",
                isActive
                  ? "bg-[var(--color-bg-surface)] text-[var(--color-accent)] shadow-sm"
                  : "text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]",
              )}
            >
              <tab.icon size={14} strokeWidth={1.5} />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Content area */}
      <div
        role="tabpanel"
        id={`panel-${activeTab}`}
        aria-labelledby={`tab-${activeTab}`}
        className="space-y-3"
      >
        {/* Loading state */}
        {loading && (
          <div className="space-y-3" aria-busy="true">
            {Array.from({ length: 4 }).map((_, i) => (
              <SkeletonCard key={i} />
            ))}
          </div>
        )}

        {/* Error state */}
        {!loading && error && (
          <div className="rounded-xl border p-6 bg-[var(--color-bg-surface)] border-[var(--color-border)]">
            <div className="flex flex-col items-center gap-3 text-center">
              <AlertCircle size={28} className="text-[var(--color-score-low)]" />
              <p className="text-sm text-[var(--color-text-secondary)]">{error}</p>
              <button
                onClick={fetchEvents}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium
                         bg-[var(--color-accent-soft)] text-[var(--color-accent)]
                         hover:opacity-80 transition-opacity"
              >
                <RotateCw size={12} />
                Försök igen
              </button>
            </div>
          </div>
        )}

        {/* Empty state */}
        {!loading && !error && events.length === 0 && <EmptyState tab={currentTab} />}

        {/* Events list */}
        {!loading && !error && events.length > 0 && (
          <div className="space-y-2">
            {events.map((event, i) => renderEvent(event, i))}
          </div>
        )}
      </div>

      {/* Footer note */}
      {!loading && !error && events.length > 0 && (
        <p className="text-[10px] text-[var(--color-text-muted)] text-center">
          Data från Finnhub. {events.length} händelser visas.
        </p>
      )}
    </div>
  );
}
