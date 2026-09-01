"use client";

import React, { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { ChevronDown, Search, X } from "lucide-react";
import { ApiError } from "@/lib/api";
import { v3Compare } from "@/lib/v3";
import type { DecisionProjectionV3 } from "@/lib/types/decision_v3";
import {
  THESIS_BAND_CONFIG,
  SETUP_STATE_CONFIG,
  RISK_STATE_CONFIG,
  DATA_GRADE_CONFIG,
  TRADABILITY_CONFIG,
  badgeFor,
  FALLBACK_THESIS,
  FALLBACK_SETUP,
  FALLBACK_RISK,
  FALLBACK_TRADABILITY,
} from "@/components/screener-v3/badges";
import { InfoTooltip } from "@/components/ui/InfoTooltip";

const MAX_TICKERS = 10;
const MIN_TICKERS = 2;

/** V3 drivers are {factor_name, label_sv} — render the Swedish label, never a synthetic value. */
function driverLabel(driver: Record<string, unknown>): string {
  const label = driver.label_sv ?? driver.factor_name;
  return typeof label === "string" && label.length > 0 ? label : "Driver";
}

/**
 * Jämför v3 (plan section 27.3): published decisions side by side from the
 * SAME canonical snapshot — thesis, setup, risk, data grade, segment
 * percentile, price and decision id. No legacy score_total / entry_signal
 * anywhere: the AICompareCard (score-based) is excluded from this path.
 */
export const JamforViewV3: React.FC = () => {
  const [tickers, setTickers] = useState<string[]>([]);
  const [query, setQuery] = useState("");
  const [rows, setRows] = useState<DecisionProjectionV3[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [asOf, setAsOf] = useState<string | null>(null);
  const [snapshotId, setSnapshotId] = useState<string | null>(null);
  const [expandedTicker, setExpandedTicker] = useState<string | null>(null);

  const addTicker = useCallback((raw: string) => {
    const ticker = raw.trim().toUpperCase();
    if (!ticker) return;
    setTickers((prev) => {
      if (prev.includes(ticker) || prev.length >= MAX_TICKERS) return prev;
      return [...prev, ticker];
    });
    setQuery("");
  }, []);

  const removeTicker = useCallback((ticker: string) => {
    setTickers((prev) => prev.filter((t) => t !== ticker));
    setExpandedTicker((prev) => (prev === ticker ? null : prev));
  }, []);

  const handleSubmit = useCallback(
    (event: React.FormEvent) => {
      event.preventDefault();
      addTicker(query);
    },
    [addTicker, query],
  );

  useEffect(() => {
    let cancelled = false;
    const run = async () => {
      if (tickers.length < MIN_TICKERS) {
        setRows([]);
        setAsOf(null);
        setSnapshotId(null);
        setError(null);
        setIsLoading(false);
        return;
      }
      setIsLoading(true);
      setError(null);
      try {
        const data = await v3Compare(tickers);
        if (cancelled) return;
        setRows(data.rows ?? []);
        setAsOf(data.as_of ?? null);
        setSnapshotId(data.snapshot_id ?? null);
      } catch (err) {
        if (cancelled) return;
        if (err instanceof ApiError && err.status === 404) {
          setError("Inga publicerade beslut matchar");
        } else if (err instanceof ApiError) {
          // 409 (tickers span multiple snapshots) and other API errors show the backend message.
          setError(err.message);
        } else {
          setError("Kunde inte hämta jämförelsen.");
        }
        setRows([]);
        setAsOf(null);
        setSnapshotId(null);
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    };
    void run();
    return () => {
      cancelled = true;
    };
  }, [tickers]);

  const unmatchedCount = tickers.length - rows.length;

  return (
    <div className="w-full space-y-4 max-w-7xl mx-auto px-4 sm:px-6 py-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-zinc-900 dark:text-zinc-50">
            Jämför aktier
          </h1>
          <p className="text-xs text-zinc-500 mt-0.5">
            Thesis · Setup · Risk · Data — samma publicerade snapshot för alla
          </p>
        </div>
        <div className="text-xs font-mono text-zinc-400 text-right">
          {asOf ? (
            <>
              <div>Snapshot {new Date(asOf).toLocaleString("sv-SE")}</div>
              <div className="truncate max-w-[220px]">{snapshotId}</div>
            </>
          ) : (
            <div>{rows.length} instrument</div>
          )}
        </div>
      </div>

      {/* Ticker selector */}
      <div className="rounded-xl border border-zinc-200/80 dark:border-zinc-800/80 bg-white dark:bg-zinc-950 p-4 shadow-sm">
        <div className="flex flex-wrap gap-2 mb-3">
          {tickers.map((t) => (
            <span
              key={t}
              className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-mono font-medium bg-zinc-100 dark:bg-zinc-900 text-zinc-700 dark:text-zinc-300 border border-zinc-200 dark:border-zinc-800"
            >
              {t}
              <button
                type="button"
                onClick={() => removeTicker(t)}
                aria-label={`Ta bort ${t}`}
                className="hover:text-rose-500 transition-colors"
              >
                <X size={12} strokeWidth={2} />
              </button>
            </span>
          ))}
          {tickers.length === 0 && (
            <span className="text-xs text-zinc-400 py-1">
              Lägg till minst 2 aktier för att jämföra
            </span>
          )}
        </div>

        <form onSubmit={handleSubmit} className="flex gap-2">
          <div className="relative flex-1">
            <Search
              size={15}
              strokeWidth={1.5}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-400"
            />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Ticker, t.ex. VOLV-B"
              disabled={tickers.length >= MAX_TICKERS}
              aria-label="Lägg till ticker"
              autoComplete="off"
              spellCheck={false}
              className="w-full h-9 pl-9 pr-3 rounded-md text-sm bg-zinc-50 dark:bg-zinc-900 text-zinc-900 dark:text-zinc-100 placeholder:text-zinc-400 outline-none focus:ring-2 focus:ring-emerald-500/40 disabled:opacity-40 disabled:cursor-not-allowed border border-zinc-200 dark:border-zinc-800"
            />
          </div>
          <button
            type="submit"
            disabled={!query.trim() || tickers.length >= MAX_TICKERS}
            className="h-9 px-3 rounded-md text-xs font-medium bg-zinc-900 dark:bg-zinc-100 text-zinc-50 dark:text-zinc-900 hover:opacity-90 disabled:opacity-40 disabled:cursor-not-allowed transition-opacity"
          >
            Lägg till
          </button>
        </form>
        <p className="text-[11px] text-zinc-400 mt-2">
          {tickers.length >= MAX_TICKERS
            ? "Max 10 aktier"
            : `Max 10 aktier · ${MAX_TICKERS - tickers.length} kvar`}
        </p>
      </div>

      {/* Loading */}
      {isLoading && (
        <div className="w-full py-16 text-center text-zinc-500" role="status">
          <div className="inline-block h-8 w-8 animate-spin rounded-full border-2 border-emerald-500 border-t-transparent" />
          <p className="mt-3 text-sm">Laddar jämförelse...</p>
        </div>
      )}

      {/* Error (404 → explicit no-match message; 409 → backend message) */}
      {error && !isLoading && (
        <div className="w-full py-10 text-center text-sm text-amber-700 dark:text-amber-300 rounded-xl border border-amber-500/30 bg-amber-500/5">
          {error}
        </div>
      )}

      {/* Compare table */}
      {!isLoading && !error && rows.length > 0 && (
        <div className="space-y-3">
          {unmatchedCount > 0 && (
            <p className="text-xs text-zinc-400">
              {unmatchedCount} av {tickers.length} aktier saknar publicerat beslut i snapshoten och
              visas inte.
            </p>
          )}
          <div className="w-full overflow-x-auto rounded-xl border border-zinc-200/80 dark:border-zinc-800/80 bg-white dark:bg-zinc-950 shadow-sm">
            <table className="w-full text-left text-sm border-collapse">
              <caption className="sr-only">
                Jämförelse av publicerade beslut: tes, setup, risk, datakvalitet, segment, kurs och
                besluts-ID
              </caption>
              <thead>
                <tr className="border-b border-zinc-200 dark:border-zinc-800 bg-zinc-50/75 dark:bg-zinc-900/75 text-xs font-semibold text-zinc-500 uppercase tracking-wider">
                  <th scope="col" className="py-3.5 px-2 w-8">
                    <span className="sr-only">Drivare</span>
                  </th>
                  <th scope="col" className="py-3.5 px-4">
                    Aktie
                  </th>
                  <th scope="col" className="py-3.5 px-4">
                    Thesis{" "}
                    <InfoTooltip text="Tesband från den publicerade snapshoten — hur stark den strukturella tesen är." />
                  </th>
                  <th scope="col" className="py-3.5 px-4">
                    Setup{" "}
                    <InfoTooltip text="Setup-tillstånd i snapshoten: bekräftad, bevaka, vänta eller otillräcklig data." />
                  </th>
                  <th scope="col" className="py-3.5 px-4">
                    Risk{" "}
                    <InfoTooltip text="Riskbedömning i snapshoten: låg, medel eller kritisk." />
                  </th>
                  <th scope="col" className="py-3.5 px-4">
                    Data{" "}
                    <InfoTooltip text="Datakvalitetsbetyg (A–D) från täckningsgraden i snapshoten." />
                  </th>
                  <th scope="col" className="py-3.5 px-4">
                    Segment{" "}
                    <InfoTooltip text="Segment-percentil (0–100) — hur starkt rankad aktien är inom sitt segment i snapshoten." />
                  </th>
                  <th scope="col" className="py-3.5 px-4 text-right">
                    Kurs / Idag{" "}
                    <InfoTooltip text="Senaste kurs och dagsförändring från snapshoten." />
                  </th>
                  <th scope="col" className="py-3.5 px-4">
                    Beslut{" "}
                    <InfoTooltip text="Unikt besluts-ID i snapshoten." />
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-100 dark:divide-zinc-900">
                {rows.map((row) => {
                  const tradable = row.tradability_state === "ACTIVE";
                  const thesis = badgeFor(THESIS_BAND_CONFIG, row.thesis_band, FALLBACK_THESIS);
                  const setup = badgeFor(SETUP_STATE_CONFIG, row.setup_state, FALLBACK_SETUP);
                  const risk = badgeFor(RISK_STATE_CONFIG, row.risk_state, FALLBACK_RISK);
                  const tradability = badgeFor(
                    TRADABILITY_CONFIG,
                    row.tradability_state,
                    FALLBACK_TRADABILITY,
                  );
                  const dataGrade =
                    DATA_GRADE_CONFIG[row.data_grade] ?? {
                      label: row.data_grade,
                      bg: "bg-zinc-500/15",
                      text: "text-zinc-500",
                    };
                  const muted = !tradable || !row.is_actionable;
                  const isExpanded = expandedTicker === row.ticker;
                  const driversRowId = `drivers-${row.ticker}`;

                  return (
                    <React.Fragment key={row.decision_id}>
                      <tr
                        className={`transition-colors group ${
                          muted ? "opacity-60" : "hover:bg-zinc-50/80 dark:hover:bg-zinc-900/50"
                        }`}
                      >
                        <td className="py-3.5 px-2 w-8">
                          <button
                            type="button"
                            onClick={() => setExpandedTicker(isExpanded ? null : row.ticker)}
                            aria-expanded={isExpanded}
                            aria-controls={driversRowId}
                            aria-label={`Visa drivare för ${row.ticker}`}
                            className="inline-flex items-center justify-center w-6 h-6 rounded-md text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200 hover:bg-zinc-100 dark:hover:bg-zinc-900 focus:outline-none focus:ring-2 focus:ring-emerald-500/40 transition-colors"
                          >
                            <ChevronDown
                              size={14}
                              className={`transition-transform ${isExpanded ? "rotate-180" : ""}`}
                            />
                          </button>
                        </td>
                        <td className="py-3.5 px-4">
                          <Link
                            href={`/aktie/${encodeURIComponent(row.ticker)}`}
                            tabIndex={muted ? -1 : undefined}
                            className="block"
                          >
                            <div className="flex items-center space-x-2">
                              <span className="font-semibold text-zinc-900 dark:text-zinc-100 group-hover:text-emerald-600 dark:group-hover:text-emerald-400 transition-colors">
                                {row.ticker}
                              </span>
                              {!tradable && (
                                <span
                                  className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium border ${tradability.bg} ${tradability.text} ${tradability.border}`}
                                >
                                  {tradability.label}
                                </span>
                              )}
                            </div>
                            <div className="text-xs text-zinc-500 truncate max-w-[200px] mt-0.5">
                              {row.name ?? row.mic}
                            </div>
                          </Link>
                        </td>
                        <td className="py-3.5 px-4">
                          <span
                            className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${thesis.bg} ${thesis.text} ${thesis.border}`}
                          >
                            {thesis.label}
                          </span>
                        </td>
                        <td className="py-3.5 px-4">
                          <span
                            className={`inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium border ${setup.bg} ${setup.text} ${setup.border}`}
                          >
                            {setup.label}
                          </span>
                        </td>
                        <td className="py-3.5 px-4">
                          <span
                            className={`inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium border ${risk.bg} ${risk.text} ${risk.border}`}
                          >
                            {risk.label}
                          </span>
                        </td>
                        <td className="py-3.5 px-4">
                          <div className="flex items-center space-x-1.5">
                            <span
                              className={`inline-flex items-center justify-center w-5 h-5 rounded text-xs font-bold ${dataGrade.bg} ${dataGrade.text}`}
                            >
                              {dataGrade.label}
                            </span>
                            <span className="text-[10px] text-zinc-400">
                              {Math.round((row.coverage ?? 0) * 100)}%
                            </span>
                          </div>
                        </td>
                        <td className="py-3.5 px-4">
                          {row.segment_percentile != null ? (
                            <span className="font-mono text-zinc-700 dark:text-zinc-300">
                              {Math.round(row.segment_percentile)} %
                            </span>
                          ) : (
                            <span className="text-xs text-zinc-400">—</span>
                          )}
                        </td>
                        <td className="py-3.5 px-4 text-right">
                          {row.price != null ? (
                            <>
                              <div className="font-mono font-medium text-zinc-900 dark:text-zinc-100">
                                {row.price.toLocaleString("sv-SE", {
                                  minimumFractionDigits: 2,
                                  maximumFractionDigits: 2,
                                })}{" "}
                                {row.currency}
                              </div>
                              {row.change_pct != null && (
                                <div
                                  className={`text-xs font-mono font-medium ${
                                    row.change_pct >= 0
                                      ? "text-emerald-600"
                                      : "text-rose-600"
                                  }`}
                                >
                                  {row.change_pct >= 0 ? "+" : ""}
                                  {(row.change_pct * 100).toFixed(2)}%
                                </div>
                              )}
                            </>
                          ) : (
                            <span className="text-xs text-zinc-400">—</span>
                          )}
                        </td>
                        <td className="py-3.5 px-4">
                          <span
                            className="font-mono text-[10px] text-zinc-400"
                            title={row.decision_id}
                          >
                            {row.decision_id.slice(0, 8)}…
                          </span>
                        </td>
                      </tr>
                      {isExpanded && (
                        <tr id={driversRowId} className="bg-zinc-50/50 dark:bg-zinc-900/50">
                          <td colSpan={9} className="py-4 px-4">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                              <div>
                                <h4 className="text-[11px] font-semibold uppercase tracking-wider text-emerald-700 dark:text-emerald-300 mb-2">
                                  Positiva drivare
                                </h4>
                                {row.positive_drivers && row.positive_drivers.length > 0 ? (
                                  <div className="flex flex-wrap gap-1.5">
                                    {row.positive_drivers.map((driver, index) => (
                                      <span
                                        key={`pos-${index}`}
                                        className="text-[11px] px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 font-medium"
                                      >
                                        +{driverLabel(driver)}
                                      </span>
                                    ))}
                                  </div>
                                ) : (
                                  <p className="text-xs text-zinc-400">
                                    Inga positiva avvikelser i snapshoten.
                                  </p>
                                )}
                              </div>
                              <div>
                                <h4 className="text-[11px] font-semibold uppercase tracking-wider text-rose-700 dark:text-rose-300 mb-2">
                                  Negativa drivare
                                </h4>
                                {row.negative_drivers && row.negative_drivers.length > 0 ? (
                                  <div className="flex flex-wrap gap-1.5">
                                    {row.negative_drivers.map((driver, index) => (
                                      <span
                                        key={`neg-${index}`}
                                        className="text-[11px] px-1.5 py-0.5 rounded bg-rose-500/10 text-rose-700 dark:text-rose-300 font-medium"
                                      >
                                        -{driverLabel(driver)}
                                      </span>
                                    ))}
                                  </div>
                                ) : (
                                  <p className="text-xs text-zinc-400">
                                    Inga negativa avvikelser i snapshoten.
                                  </p>
                                )}
                              </div>
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Defensive empty state (backend 404s instead, but never render a blank page) */}
      {!isLoading && !error && tickers.length >= MIN_TICKERS && rows.length === 0 && (
        <div className="w-full py-16 text-center text-zinc-500 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-zinc-50/50 dark:bg-zinc-900/50">
          <p className="text-sm font-medium">Inga publicerade beslut matchade.</p>
          <p className="text-xs text-zinc-400 mt-1">
            Kontrollera tickers, eller vänta tills nästa snapshot är publicerad.
          </p>
        </div>
      )}
    </div>
  );
};