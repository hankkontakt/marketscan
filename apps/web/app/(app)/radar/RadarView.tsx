"use client";

import { useState } from "react";
import { Radar, AlertCircle, ExternalLink } from "lucide-react";
import { useMarketIntelRadar } from "@/hooks/useMarketIntel";
import type { RadarItem, RadarEvent } from "@/lib/api";
import { cn } from "@/lib/utils";

// ─── Konstanter ───────────────────────────────────────────────────────────────

const THEMES = [
  { value: "", label: "Alla teman" },
  { value: "ipo", label: "Noteringar" },
  { value: "order", label: "Order/avtal" },
  { value: "vinstvarning", label: "Vinstvarning" },
  { value: "ledning", label: "Ledningsbyten" },
  { value: "regulatorik", label: "Regulatorik" },
  { value: "sector-ai", label: "AI/tech" },
  { value: "sector-forsvar", label: "Försvar/säkerhet" },
] as const;

const STRATUM_META: Record<string, { label: string; className: string }> = {
  established: { label: "Etablerad", className: "bg-[var(--color-bg-elevated)] text-[var(--color-text-muted)]" },
  growth_early: { label: "Tillväxt", className: "bg-[var(--color-accent-soft)] text-[var(--color-accent)]" },
  new_small: { label: "Nytt & smått", className: "bg-[var(--color-up-soft)] text-[var(--color-up)]" },
  turnaround: { label: "Kris", className: "bg-[var(--color-warn-soft)] text-[var(--color-warn)]" },
};

const BEARING_META: Record<string, { label: string; className: string }> = {
  positive: { label: "Positiv", className: "bg-[var(--color-up-soft)] text-[var(--color-up)]" },
  negative: { label: "Negativ", className: "bg-[var(--color-down-soft)] text-[var(--color-down)]" },
  conditional: { label: "Villkorlig", className: "bg-[var(--color-warn-soft)] text-[var(--color-warn)]" },
  neutral: { label: "Neutral", className: "bg-[var(--color-bg-elevated)] text-[var(--color-text-muted)]" },
};

type SortMode = "activity" | "rank";

// ─── Hjälpfunktioner ──────────────────────────────────────────────────────────

function formatZ(value: number | null): string {
  return value != null ? value.toFixed(1) : "–";
}

function formatShortPct(value: number | null): string {
  return value != null ? `${value.toFixed(1)} %` : "–";
}

// ─── Varningschips ────────────────────────────────────────────────────────────

function WarningChips({ warnings }: { warnings: string[] }) {
  if (warnings.length === 0) return null;
  return (
    <div className="flex flex-wrap gap-1 mt-1">
      {warnings.map((w, i) => (
        <span
          key={i}
          className="px-1.5 py-0.5 rounded text-[9px] font-medium bg-[var(--color-warn-soft)] text-[var(--color-warn)]"
        >
          {w}
        </span>
      ))}
    </div>
  );
}

// ─── Senaste händelser ────────────────────────────────────────────────────────

function EventList({ events }: { events: RadarEvent[] }) {
  if (events.length === 0) return <span className="text-[var(--color-text-muted)]">–</span>;
  return (
    <div className="space-y-1.5 max-w-[280px]">
      {events.slice(0, 3).map((ev, i) => {
        const bearing = ev.bearing ? BEARING_META[ev.bearing] : undefined;
        const headline = (
          <span className="text-xs text-[var(--color-text-primary)] leading-snug line-clamp-2">
            {ev.headline}
          </span>
        );
        return (
          <div key={i} className="flex items-start gap-1.5">
            {ev.message_url ? (
              <a
                href={ev.message_url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-start gap-1 text-[var(--color-text-primary)] hover:text-[var(--color-accent)] transition-colors min-w-0"
              >
                {headline}
                <ExternalLink size={9} className="shrink-0 mt-0.5 opacity-50" />
              </a>
            ) : (
              headline
            )}
            {bearing && (
              <span className={cn("shrink-0 text-[9px] font-medium px-1 py-0.5 rounded mt-0.5", bearing.className)}>
                {bearing.label}
              </span>
            )}
          </div>
        );
      })}
    </div>
  );
}

// ─── Tabellrad ────────────────────────────────────────────────────────────────

function RadarRow({ item }: { item: RadarItem }) {
  const rankBorder =
    item.alpha_rank != null && item.alpha_rank >= 70
      ? "border-l-2 border-l-[var(--color-up)]"
      : item.alpha_rank != null && item.alpha_rank >= 55
        ? "border-l-2 border-l-[var(--color-warn)]"
        : "";
  const dimmed = item.exclusion_reason != null ? "opacity-60" : "";
  const stratum = item.stratum ? STRATUM_META[item.stratum] : undefined;

  return (
    <tr
      title={item.exclusion_reason ?? undefined}
      className={cn(
        "border-b border-[var(--color-border)] transition-colors hover:bg-[var(--color-bg-elevated)]",
        rankBorder,
        dimmed,
      )}
    >
      {/* Bolag */}
      <td className="px-4 py-3">
        <div className="flex items-center gap-2">
          <div>
            <a
              href={`/aktie/${item.ticker}`}
              className="flex items-center gap-1 font-semibold text-sm text-[var(--color-text-primary)] hover:text-[var(--color-accent)] transition-colors"
            >
              {item.ticker}
              <ExternalLink size={10} className="opacity-50" />
            </a>
            {item.name && (
              <div className="text-xs text-[var(--color-text-muted)] truncate max-w-[130px]">
                {item.name}
              </div>
            )}
            <WarningChips warnings={item.warnings} />
          </div>
        </div>
      </td>

      {/* Skikt */}
      <td className="px-4 py-3 hidden md:table-cell">
        {stratum ? (
          <span className={cn("text-[10px] font-medium px-1.5 py-0.5 rounded whitespace-nowrap", stratum.className)}>
            {stratum.label}
          </span>
        ) : (
          <span className="text-xs text-[var(--color-text-muted)]">–</span>
        )}
      </td>

      {/* Kvalitet-z */}
      <td className="px-4 py-3 text-right hidden lg:table-cell">
        <span className="text-sm tabular-nums text-[var(--color-text-secondary)]">
          {formatZ(item.quality_z)}
        </span>
      </td>

      {/* Momentum-z */}
      <td className="px-4 py-3 text-right hidden lg:table-cell">
        <span className="text-sm tabular-nums text-[var(--color-text-secondary)]">
          {formatZ(item.momentum_z)}
        </span>
      </td>

      {/* Insider-z */}
      <td className="px-4 py-3 text-right hidden lg:table-cell">
        <span className="text-sm tabular-nums text-[var(--color-text-secondary)]">
          {formatZ(item.insider_z)}
        </span>
      </td>

      {/* Blankning % */}
      <td className="px-4 py-3 text-right hidden sm:table-cell">
        <div className="flex items-center justify-end gap-1">
          <span
            className={cn(
              "text-sm tabular-nums",
              item.short_pct != null && item.short_pct >= 8
                ? "text-[var(--color-down)] font-medium"
                : "text-[var(--color-text-secondary)]",
            )}
          >
            {formatShortPct(item.short_pct)}
          </span>
          {item.new_disclosure && (
            <span className="text-[9px] font-medium px-1 py-0.5 rounded bg-[var(--color-accent-soft)] text-[var(--color-accent)]">
              ny
            </span>
          )}
        </div>
      </td>

      {/* Nyheter 48h */}
      <td className="px-4 py-3 text-right hidden sm:table-cell">
        <div className="flex items-center justify-end gap-1">
          <span className="text-sm tabular-nums text-[var(--color-text-secondary)]">
            {item.news_48h}
          </span>
          {item.mention_surge != null && item.mention_surge > 1 && (
            <span className="text-[9px] font-medium px-1 py-0.5 rounded bg-[var(--color-accent-soft)] text-[var(--color-accent)]">
              x{item.mention_surge.toFixed(1)}
            </span>
          )}
        </div>
      </td>

      {/* Senaste händelser */}
      <td className="px-4 py-3 hidden xl:table-cell">
        <EventList events={item.top_events} />
      </td>
    </tr>
  );
}

// ─── Huvudvy ──────────────────────────────────────────────────────────────────

export function RadarView() {
  const [sort, setSort] = useState<SortMode>("activity");
  const [theme, setTheme] = useState<string>("");

  const { data, isLoading, error } = useMarketIntelRadar(theme || undefined, sort, 40);
  const items = data?.items ?? [];
  const total = data?.total ?? items.length;

  return (
    <div className="max-w-5xl space-y-6">

      {/* Header */}
      <div>
        <h1 className="text-xl font-semibold text-[var(--color-text-primary)]">Kandidatradar</h1>
        <p className="text-xs text-[var(--color-text-muted)] mt-0.5">
          Bolag med sammanvägda signaler — kvalitet, momentum, insiders, blankning och nyhetsflöde
        </p>
      </div>

      {/* Info box */}
      <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-bg-card)] p-4 text-xs text-[var(--color-text-muted)] space-y-2">
        <p className="font-medium text-[var(--color-text-secondary)]">Hur fungerar det?</p>
        <p>
          Radarn samlar signaler från flera källor: kvalitets- och momentumfaktorer,
          insiderhandel, blankningspositioner och nyhetshändelser. Varje bolag får en
          sammanvägd bild — men signalerna är <strong>underlag för eget beslutsfattande</strong>,
          inte färdiga slutsatser.
        </p>
        <p className="text-[10px]">
          Grön kant = stark sammanvägd signal. Gul kant = medelstark. Nedtonad rad = bolaget
          är exkluderat av ett hårt filter (håll muspekaren över raden för orsak).
        </p>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 items-center">
        {/* Vy: Aktiva / Topprank */}
        <div className="flex gap-1">
          {(["activity", "rank"] as SortMode[]).map((mode) => (
            <button
              key={mode}
              onClick={() => setSort(mode)}
              className={cn(
                "px-3 py-1.5 rounded-lg text-xs font-medium transition-colors",
                sort === mode
                  ? "bg-[var(--color-accent)] text-white"
                  : "bg-[var(--color-bg-elevated)] text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]",
              )}
            >
              {mode === "activity" ? "Aktiva" : "Topprank"}
            </button>
          ))}
        </div>

        {/* Tema-filter */}
        <select
          value={theme}
          onChange={(e) => setTheme(e.target.value)}
          aria-label="Filtrera på tema"
          className="px-3 py-1.5 rounded-lg text-xs font-medium bg-[var(--color-bg-elevated)] text-[var(--color-text-secondary)] border border-[var(--color-border)] hover:border-[var(--color-border-strong)] transition-colors cursor-pointer"
        >
          {THEMES.map((t) => (
            <option key={t.value} value={t.value}>
              {t.label}
            </option>
          ))}
        </select>

        {/* Result count */}
        {!isLoading && (
          <span className="ml-auto text-xs text-[var(--color-text-muted)]">
            {total} bolag med signaler
          </span>
        )}
      </div>

      {/* Table */}
      {isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="h-12 rounded-lg bg-[var(--color-bg-elevated)] animate-pulse" />
          ))}
        </div>
      ) : error ? (
        <div className="flex flex-col items-center py-16 gap-3 text-center">
          <AlertCircle size={32} strokeWidth={1} className="text-[var(--color-warn)]" />
          <p className="text-sm text-[var(--color-text-muted)]">
            Kunde inte hämta radardata
          </p>
        </div>
      ) : items.length === 0 ? (
        <div className="flex flex-col items-center py-16 gap-3 text-center">
          <Radar size={36} strokeWidth={1} className="text-[var(--color-text-muted)]" />
          <p className="text-sm text-[var(--color-text-muted)]">
            Inga signaler just nu
          </p>
          <p className="text-xs text-[var(--color-text-muted)] max-w-xs">
            Prova ett annat tema eller återkom — data uppdateras nattligen.
          </p>
        </div>
      ) : (
        <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-bg-card)] overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--color-border)]">
                <th className="px-4 py-3 text-left text-xs font-medium text-[var(--color-text-muted)]">Bolag</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-[var(--color-text-muted)] hidden md:table-cell">Skikt</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-[var(--color-text-muted)] hidden lg:table-cell">Kvalitet-z</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-[var(--color-text-muted)] hidden lg:table-cell">Momentum-z</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-[var(--color-text-muted)] hidden lg:table-cell">Insider-z</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-[var(--color-text-muted)] hidden sm:table-cell">Blankning %</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-[var(--color-text-muted)] hidden sm:table-cell">Nyheter 48h</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-[var(--color-text-muted)] hidden xl:table-cell">Senaste händelser</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <RadarRow key={item.ticker} item={item} />
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Ärlighetsrad */}
      <p className="text-[11px] text-[var(--color-text-muted)] leading-relaxed">
        Kandidatradarn visar signaler, inte rekommendationer. Historisk avkastning är ingen
        garanti. Småbolagsspread ~1 % per sida — rebalansera högst årligen.
      </p>
    </div>
  );
}