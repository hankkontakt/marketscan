import React, { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import {
  RefreshCw, Play, Database, ExternalLink, CheckCircle2,
  XCircle, AlertTriangle, Copy, Key, Cloud, GitBranch, Table2,
  Users, TrendingUp, Loader2,
} from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { KpiCard, StatusPill, RunsTable, DistTable, type PipelineRun } from "./StatusHelpers";

// ─── Shared error/empty state ─────────────────────────────────────────────────

function ErrorBlock({ message, onRetry }: { message?: string; onRetry?: () => void }) {
  return (
    <div className="flex flex-col items-center gap-3 py-10 text-center">
      <AlertTriangle size={24} strokeWidth={1.5} className="text-[var(--color-warn)]" />
      <p className="text-sm text-[var(--color-text-muted)]">
        {message ?? "Kunde inte hämta data"}
      </p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="flex items-center gap-1 text-xs text-[var(--color-accent)] hover:underline"
        >
          <RefreshCw size={11} strokeWidth={1.5} />
          Försök igen
        </button>
      )}
    </div>
  );
}

// ─── Status ──────────────────────────────────────────────────────────────────

export function StatusSection() {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["admin-status"],
    queryFn: () => api<{ scan_rows: number; last_runs: PipelineRun[] }>("/api/admin/status"),
    staleTime: 30_000,
    retry: 1,
  });

  return (
    <div className="space-y-4 mt-4">
      <div className="flex justify-between items-center">
        <h2 className="text-sm font-medium text-[var(--color-text-secondary)]">Systemstatus</h2>
        <button onClick={() => refetch()}
                className="text-xs text-[var(--color-accent)] flex items-center gap-1 hover:underline">
          <RefreshCw size={11} strokeWidth={1.5} />
          Uppdatera
        </button>
      </div>

      {isLoading ? (
        <div className="skeleton h-24 rounded-xl" />
      ) : error ? (
        <ErrorBlock message="Kunde inte hämta systemstatus" onRetry={refetch} />
      ) : (
        <>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            <KpiCard label="Aktier i scan" value={String(data?.scan_rows ?? "—")} />
            <KpiCard label="Senaste status" value={data?.last_runs[0]?.status ?? "—"} status={data?.last_runs[0]?.status} />
            <KpiCard label="Körtid (senaste)" value={data?.last_runs[0]?.duration_s ? `${data.last_runs[0].duration_s}s` : "—"} />
          </div>

          {data?.last_runs && data.last_runs.length > 0 && (
            <div className="rounded-xl overflow-hidden border border-[var(--color-border)]">
              <table className="w-full text-xs border-collapse">
                <thead>
                  <tr className="bg-[var(--color-bg-surface)] border-b border-[var(--color-border)]">
                    {["Typ", "Status", "Ok", "Fel", "Tid", "Startat"].map((h) => (
                      <th key={h} className="px-4 py-2 text-left font-medium text-[var(--color-text-muted)]">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {data.last_runs.map((run) => (
                    <tr key={run.id} className="bg-[var(--color-bg-surface)] border-b border-[var(--color-border)]">
                      <td className="px-4 py-2.5 font-mono">{run.run_type}</td>
                      <td className="px-4 py-2.5"><StatusPill status={run.status} /></td>
                      <td className="px-4 py-2.5 tabular font-mono text-[var(--color-up)]">{run.tickers_ok ?? "—"}</td>
                      <td className="px-4 py-2.5 tabular font-mono text-[var(--color-down)]">{run.tickers_err ?? "—"}</td>
                      <td className="px-4 py-2.5 tabular font-mono text-[var(--color-text-muted)]">
                        {run.duration_s != null ? `${run.duration_s}s` : "—"}
                      </td>
                      <td className="px-4 py-2.5 text-[var(--color-text-muted)]">
                        {run.started_at ? new Date(run.started_at).toLocaleString("sv-SE") : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </div>
  );
}

// ─── Pipeline / GitHub Actions ────────────────────────────────────────────────

interface WorkflowInputDef {
  key: string;
  label: string;
  type: "text" | "select" | "toggle";
  placeholder?: string;
  options?: string[];
  defaultVal?: string;
}

interface WorkflowDef {
  file: string;
  label: string;
  desc: string;
  inputs?: WorkflowInputDef[];
  setupEndpoint?: string;  // optional one-click DB setup before triggering
  setupLabel?: string;     // button label (default: "Konfigurera DB")
}

const WORKFLOW_CATEGORIES: { title: string; workflows: WorkflowDef[] }[] = [
  {
    title: "Pipeline",
    workflows: [
      {
        file: "pipeline.yml",
        label: "Daglig pipeline",
        desc: "Hämtar marknadsdata och kör scoring för alla aktier",
        inputs: [
          {
            key: "mode",
            label: "Läge",
            type: "select",
            options: ["morning", "evening", "weekly", "smallcap", "targeted", "refresh_missing", "retry_rate_limited"],
            defaultVal: "morning",
          },
          {
            key: "tickers",
            label: "Tickers (targeted)",
            type: "text",
            placeholder: "VOLV-B.ST, TSLA (valfritt)",
          },
        ],
      },
      { file: "score_tracker.yml",    label: "Score-spårning",   desc: "Spårar dagliga förändringar i totalbetyg" },
      { file: "risk_analysis.yml",    label: "Riskanalys",       desc: "Beräknar portföljriskmått (VaR, Sharpe, etc.)" },
      { file: "smart_alerts.yml",     label: "Smarta varningar", desc: "Utvärderar regler och skickar signalvarningar" },
      { file: "signal_analytics.yml", label: "Signalanalys",     desc: "Beräknar framåtavkastning och win-rate per signal" },
    ],
  },
  {
    title: "ML & Backtest",
    workflows: [
      { file: "ml_train.yml", label: "ML-träning", desc: "Tränar om LightGBM LambdaRank-rankeraren (walk-forward)" },
      {
        file: "ml_retrain.yml",
        label: "ML-omträning (veckovis)",
        desc: "Omträning från realiserade utfall med deploy-gate",
        inputs: [{ key: "force_retrain", label: "Tvinga omträning", type: "toggle", defaultVal: "false" }],
      },
      {
        file: "strategy_backtester.yml",
        label: "Strategitest",
        desc: "Backtesting av en specifik strategi mot historisk data",
        inputs: [{ key: "strategy_id", label: "Strategi-ID", type: "text", placeholder: "uuid (valfritt, kör alla om tomt)" }],
      },
      {
        file: "backtest_runner.yml",
        label: "Backtester",
        desc: "Kör den generella backtesting-pipeline",
        inputs: [{ key: "strategy", label: "Strategi", type: "text", placeholder: "t.ex. momentum (valfritt)" }],
      },
    ],
  },
  {
    title: "Universum",
    workflows: [
      { file: "universe_discovery.yml", label: "Universum-discovery", desc: "Söker nya aktier via Finviz och lägger till i universumet" },
      { file: "smallcap_scan.yml",      label: "Småbolagsscan",       desc: "Djupscan av småbolag med utökade kriterier" },
      { file: "sector_rotation.yml",    label: "Sektorsrotation",     desc: "Analyserar och loggar sektorsrotationsmönster" },
    ],
  },
  {
    title: "Verktyg",
    workflows: [
      {
        file: "options_scan.yml",
        label: "Optionsscan",
        desc: "Söker ovanliga optionsflöden",
        inputs: [{ key: "tickers", label: "Tickers", type: "text", placeholder: "VOLV-B.ST, TSLA (valfritt)" }],
      },
      {
        file: "fi_insider.yml",
        label: "FI Insider (ny)",
        desc: "Bulk-ingestion av FI:s insynsregister + klusterscoring",
        inputs: [{ key: "days", label: "Dagar bakåt", type: "text", placeholder: "7" }],
      },
      {
        file: "doc_intelligence.yml",
        label: "Dokumentintelligens",
        desc: "Hämtar rapporter + extraherar kvalitativa signaler",
        inputs: [
          { key: "days", label: "Dagar bakåt", type: "text", placeholder: "3" },
          { key: "tickers", label: "Tickers (kommasep, valfritt)", type: "text", placeholder: "" },
        ],
      },
      {
        file: "digest.yml",
        label: "Digest-mail",
        desc: "Skickar daglig marknadssammanfattning via Resend",
        inputs: [{ key: "dry_run", label: "Testläge (skicka ej)", type: "toggle", defaultVal: "false" }],
      },
      {
        file: "company_profiles.yml",
        label: "Bolagsprofiler",
        desc: "Skapar tabell + hämtar beskrivning, anställda, webb, 52v-intervall (yfinance/Finnhub/FMP)",
        inputs: [{ key: "ticker", label: "Enstaka ticker (tomt = alla)", type: "text", placeholder: "VOLV-B.ST (valfritt)" }],
      },
      {
        file: "insider_trades.yml",
        label: "Insiderhandel",
        desc: "Hämtar insiderköp/-sälj via Finnhub för alla aktier i scan_results",
        inputs: [
          { key: "ticker", label: "Enstaka ticker (tomt = alla)", type: "text", placeholder: "ERIC-B.ST (valfritt)" },
          { key: "days", label: "Dagar bakåt", type: "text", placeholder: "90" },
        ],
      },
    ],
  },
];

export function PipelineSection() {
  const { data: runs = [], isLoading: runsLoading, refetch } = useQuery({
    queryKey: ["pipeline-runs"],
    queryFn: () => api<PipelineRun[]>("/api/admin/pipeline-runs"),
    staleTime: 30_000,
  });

  // Per-workflow trigger state: pending / ok / error
  const [wfState, setWfState] = useState<
    Record<string, { pending?: boolean; ok?: boolean; link?: string; error?: string }>
  >({});

  // Per-workflow setup state (DB migration buttons)
  const [setupState, setSetupState] = useState<
    Record<string, { pending?: boolean; ok?: boolean; msg?: string; error?: string; sql?: string }>
  >({});

  const runSetup = async (wf: WorkflowDef) => {
    if (!wf.setupEndpoint) return;
    setSetupState((s) => ({ ...s, [wf.file]: { pending: true } }));
    try {
      const res = await api<{ ok: boolean; message: string; needs_manual?: boolean; sql?: string }>(
        wf.setupEndpoint, { method: "POST" }
      );
      if (res.needs_manual) {
        setSetupState((s) => ({ ...s, [wf.file]: { ok: false, msg: res.message, sql: res.sql } }));
      } else {
        setSetupState((s) => ({ ...s, [wf.file]: { ok: true, msg: res.message } }));
      }
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : "Setup misslyckades";
      setSetupState((s) => ({ ...s, [wf.file]: { error: msg } }));
    }
  };

  // Per-workflow input values (initialised with defaults)
  const [inputVals, setInputVals] = useState<Record<string, Record<string, string>>>(() => {
    const init: Record<string, Record<string, string>> = {};
    for (const cat of WORKFLOW_CATEGORIES) {
      for (const wf of cat.workflows) {
        init[wf.file] = {};
        for (const inp of wf.inputs ?? []) {
          if (inp.defaultVal !== undefined) init[wf.file][inp.key] = inp.defaultVal;
        }
      }
    }
    return init;
  });

  const setInputVal = (file: string, key: string, val: string) =>
    setInputVals((s) => ({ ...s, [file]: { ...(s[file] ?? {}), [key]: val } }));

  const triggerWorkflow = async (wf: WorkflowDef) => {
    setWfState((s) => ({ ...s, [wf.file]: { pending: true } }));
    try {
      const inputs: Record<string, string> = {};
      for (const inp of wf.inputs ?? []) {
        const val = inputVals[wf.file]?.[inp.key] ?? inp.defaultVal ?? "";
        if (val !== "") inputs[inp.key] = val;
      }
      const result = await api<{ status: string; link: string }>("/api/admin/workflow/trigger", {
        method: "POST",
        body: JSON.stringify({ workflow: wf.file, inputs }),
      });
      setWfState((s) => ({ ...s, [wf.file]: { ok: true, link: result.link } }));
      setTimeout(refetch, 3000);
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : "Kunde inte starta workflow";
      setWfState((s) => ({ ...s, [wf.file]: { error: msg } }));
    }
  };

  return (
    <div className="space-y-5 mt-4">
      <div className="flex justify-between items-center">
        <h2 className="text-sm font-medium text-[var(--color-text-secondary)]">GitHub Actions</h2>
        <a
          href="https://github.com/hankkontakt/marketscan/actions"
          target="_blank"
          rel="noopener noreferrer"
          className="text-xs text-[var(--color-accent)] flex items-center gap-1 hover:underline"
        >
          <ExternalLink size={11} strokeWidth={1.5} />
          Öppna GitHub
        </a>
      </div>

      {WORKFLOW_CATEGORIES.map((cat) => (
        <div
          key={cat.title}
          className="rounded-xl border border-[var(--color-border)] bg-[var(--color-bg-surface)] overflow-hidden"
        >
          {/* Category header */}
          <div className="px-4 py-2 border-b border-[var(--color-border)] bg-[var(--color-bg-elevated)]">
            <h3 className="text-[10px] font-semibold text-[var(--color-text-muted)] uppercase tracking-wider">
              {cat.title}
            </h3>
          </div>

          {/* Workflow rows */}
          <div className="divide-y divide-[var(--color-border)]">
            {cat.workflows.map((wf) => {
              const st = wfState[wf.file] ?? {};
              return (
                <div key={wf.file} className="px-4 py-3 space-y-2">
                  {/* Label row */}
                  <div className="flex items-center gap-3">
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-medium text-[var(--color-text-primary)]">{wf.label}</p>
                      <p className="text-[10px] text-[var(--color-text-muted)] mt-0.5 leading-relaxed">{wf.desc}</p>
                    </div>

                    {/* Status badge */}
                    {st.pending && (
                      <span className="flex items-center gap-1 text-[10px] text-[var(--color-text-muted)] shrink-0">
                        <Loader2 size={11} className="animate-spin" />
                        Startar…
                      </span>
                    )}
                    {!st.pending && st.ok && (
                      <a
                        href={st.link}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-1 text-[10px] text-[var(--color-up)] hover:underline shrink-0"
                      >
                        <CheckCircle2 size={11} />
                        Startad
                        <ExternalLink size={9} />
                      </a>
                    )}
                    {!st.pending && st.error && (
                      <span
                        className="text-[10px] text-[var(--color-down)] max-w-[180px] truncate shrink-0"
                        title={st.error}
                      >
                        <XCircle size={11} className="inline mr-0.5" />
                        {st.error}
                      </span>
                    )}

                    {/* Setup button (only for workflows with setupEndpoint) */}
                    {wf.setupEndpoint && (() => {
                      const ss = setupState[wf.file] ?? {};
                      return (
                        <div className="flex items-center gap-1.5 shrink-0">
                          {ss.pending && (
                            <span className="flex items-center gap-1 text-[10px] text-[var(--color-text-muted)]">
                              <Loader2 size={10} className="animate-spin" />
                            </span>
                          )}
                          {!ss.pending && ss.ok && (
                            <span className="flex items-center gap-1 text-[10px] text-[var(--color-up)]" title={ss.msg}>
                              <CheckCircle2 size={10} />
                              {ss.msg ?? "OK"}
                            </span>
                          )}
                          {!ss.pending && ss.error && (
                            <span className="text-[10px] text-[var(--color-down)] max-w-[140px] truncate" title={ss.error}>
                              <XCircle size={10} className="inline mr-0.5" />
                              {ss.error}
                            </span>
                          )}
                          {!ss.ok && !ss.sql && (
                            <button
                              onClick={() => runSetup(wf)}
                              disabled={!!ss.pending}
                              className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium
                                         bg-[var(--color-bg-elevated)] text-[var(--color-text-secondary)]
                                         border border-[var(--color-border)]
                                         hover:bg-[var(--color-bg-elevated)]/80 transition-colors disabled:opacity-40"
                            >
                              <Database size={10} strokeWidth={1.5} />
                              {wf.setupLabel ?? "Konfigurera DB"}
                            </button>
                          )}
                        </div>
                      );
                    })()}

                    <button
                      onClick={() => triggerWorkflow(wf)}
                      disabled={!!st.pending}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium shrink-0
                                 bg-[var(--color-accent-soft)] text-[var(--color-accent)]
                                 border border-[var(--color-accent)]/20
                                 hover:bg-[var(--color-accent)]/20 transition-colors disabled:opacity-40"
                    >
                      <Play size={11} strokeWidth={1.5} />
                      Starta
                    </button>
                  </div>

                  {/* SQL panel — shown when server can't auto-create table */}
                  {wf.setupEndpoint && setupState[wf.file]?.sql && (
                    <div className="rounded-lg border border-[var(--color-warn)]/40 bg-[var(--color-warn-soft)] p-3 space-y-2">
                      <p className="text-[11px] text-[var(--color-text-secondary)] leading-relaxed">
                        {setupState[wf.file]?.msg}
                      </p>
                      <pre className="text-[10px] font-mono bg-[var(--color-bg-elevated)] rounded p-2 overflow-x-auto whitespace-pre text-[var(--color-text-primary)] leading-relaxed">
                        {setupState[wf.file]?.sql}
                      </pre>
                      <button
                        onClick={() => navigator.clipboard.writeText(setupState[wf.file]?.sql ?? "")}
                        className="flex items-center gap-1 text-[10px] text-[var(--color-accent)] hover:underline"
                      >
                        <Copy size={10} />
                        Kopiera SQL
                      </button>
                    </div>
                  )}

                  {/* Inline inputs */}
                  {wf.inputs && wf.inputs.length > 0 && (
                    <div className="flex flex-wrap gap-2.5 pt-0.5">
                      {wf.inputs.map((inp) => {
                        const val = inputVals[wf.file]?.[inp.key] ?? inp.defaultVal ?? "";

                        if (inp.type === "select" && inp.options) {
                          return (
                            <div key={inp.key} className="flex items-center gap-1.5">
                              <label className="text-[10px] text-[var(--color-text-muted)] whitespace-nowrap">
                                {inp.label}:
                              </label>
                              <select
                                value={val}
                                onChange={(e) => setInputVal(wf.file, inp.key, e.target.value)}
                                className="h-7 px-2 rounded-md text-[10px] bg-[var(--color-bg-elevated)]
                                           text-[var(--color-text-primary)] border border-[var(--color-border)]
                                           outline-none focus:ring-1 focus:ring-[var(--color-accent)]"
                              >
                                {inp.options.map((o) => <option key={o} value={o}>{o}</option>)}
                              </select>
                            </div>
                          );
                        }

                        if (inp.type === "toggle") {
                          return (
                            <label key={inp.key} className="flex items-center gap-1.5 cursor-pointer">
                              <input
                                type="checkbox"
                                checked={val === "true"}
                                onChange={(e) => setInputVal(wf.file, inp.key, String(e.target.checked))}
                                className="w-3.5 h-3.5 accent-[var(--color-accent)]"
                              />
                              <span className="text-[10px] text-[var(--color-text-muted)]">{inp.label}</span>
                            </label>
                          );
                        }

                        // text
                        return (
                          <div key={inp.key} className="flex items-center gap-1.5">
                            <label className="text-[10px] text-[var(--color-text-muted)] whitespace-nowrap">
                              {inp.label}:
                            </label>
                            <input
                              type="text"
                              value={val}
                              onChange={(e) => setInputVal(wf.file, inp.key, e.target.value)}
                              placeholder={inp.placeholder}
                              className="h-7 px-2 rounded-md text-[10px] bg-[var(--color-bg-elevated)]
                                         text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)]
                                         border border-[var(--color-border)] outline-none focus:ring-1
                                         focus:ring-[var(--color-accent)] min-w-[160px]"
                            />
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      ))}

      <p className="text-[11px] text-[var(--color-text-muted)]">
        Pipeline körs automatiskt (morgon 06:15, kväll 18:30, veckovis söndag 08:00).
        Knapparna ovan triggar manuella körningar via GitHub Actions API.
      </p>

      {runsLoading
        ? <div className="skeleton h-48 rounded-xl" />
        : <RunsTable runs={runs} />
      }
    </div>
  );
}

// ─── Health Check ────────────────────────────────────────────────────────────

export function HealthSection() {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["admin-health"],
    queryFn: () => api<{
      env: Record<string, boolean>;
      db: Record<string, number | string | null>;
      checks: { name: string; ok: boolean; detail?: string }[];
    }>(`/api/admin/health`),
    staleTime: 10_000,
    retry: 1,
  });

  return (
    <div className="space-y-4 mt-4">
      <div className="flex justify-between items-center">
        <h2 className="text-sm font-medium text-[var(--color-text-secondary)]">Hälsokoll</h2>
        <button onClick={() => refetch()}
                className="text-xs text-[var(--color-accent)] flex items-center gap-1 hover:underline">
          <RefreshCw size={11} strokeWidth={1.5} />
          Kör nu
        </button>
      </div>

      {isLoading ? (
        <div className="skeleton h-32 rounded-xl" />
      ) : error ? (
        <ErrorBlock message="Kunde inte hämta hälsodata" onRetry={refetch} />
      ) : data && (
        <>
          {/* Env badges */}
          <div className="flex flex-wrap gap-2">
            {Object.entries(data.env).map(([key, ok]) => (
              <span
                key={key}
                className={`inline-flex items-center gap-1 px-2 py-1 rounded-lg text-[10px] font-medium
                  ${ok ? "bg-[var(--color-up)]/10 text-[var(--color-up)]" : "bg-[var(--color-down)]/10 text-[var(--color-down)]"}`}
              >
                {ok ? <CheckCircle2 size={10} /> : <XCircle size={10} />}
                {key}
              </span>
            ))}
          </div>

          {/* DB stats */}
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            {Object.entries(data.db).filter(([, v]) => v != null).map(([key, val]) => (
              <KpiCard key={key} label={key.replace(/_/g, " ")} value={String(val ?? "—")} />
            ))}
          </div>

          {/* Service checks */}
          <div className="space-y-1.5">
            {data.checks.map((check) => (
              <div
                key={check.name}
                className="flex items-center gap-2 px-3 py-2 rounded-lg bg-[var(--color-bg-surface)] border border-[var(--color-border)]"
              >
                {check.ok
                  ? <CheckCircle2 size={14} className="text-[var(--color-up)] shrink-0" />
                  : <XCircle size={14} className="text-[var(--color-down)] shrink-0" />
                }
                <span className="text-xs text-[var(--color-text-primary)]">{check.name}</span>
                <span className="text-[10px] text-[var(--color-text-muted)] ml-auto">{check.detail}</span>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

// ─── Universum ───────────────────────────────────────────────────────────────

export function UniversumSection() {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["admin-universe"],
    queryFn: () => api<{
      by_sector: Record<string, number>;
      by_segment: Record<string, number>;
      by_country: Record<string, number>;
      low_liquidity: number;
      total: number;
    }>("/api/admin/universe"),
    staleTime: 60_000,
    retry: 1,
  });

  if (isLoading) return <div className="skeleton h-48 rounded-xl mt-4" />;
  if (error) return <ErrorBlock message="Kunde inte hämta universumdata" onRetry={refetch} />;
  if (!data) return null;

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-4">
      <DistTable title="Per segment" data={data.by_segment} total={data.total} />
      <DistTable title="Per sektor" data={data.by_sector} total={data.total} />
      <DistTable title="Per land" data={data.by_country} total={data.total} />
    </div>
  );
}

// ─── Mått ────────────────────────────────────────────────────────────────────

export function MattSection() {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["score-distribution"],
    queryFn: () => api<{
      buckets: { range: string; count: number }[];
      total: number;
      by_signal: Record<string, number>;
    }>("/api/admin/score-distribution"),
    staleTime: 60_000,
    retry: 1,
  });

  if (isLoading) return <div className="skeleton h-48 rounded-xl mt-4" />;
  if (error) return <ErrorBlock message="Kunde inte hämta poängfördelning" onRetry={refetch} />;
  if (!data) return null;

  const max = Math.max(...data.buckets.map((b) => b.count), 1);

  // Color each bucket: 0-39 = red-ish, 40-59 = amber, 60-79 = blue-accent, 80-100 = green
  function bucketColor(range: string): string {
    const lo = parseInt(range.split("-")[0], 10);
    if (lo < 40) return "#ef4444"; // red
    if (lo < 60) return "#f59e0b"; // amber
    if (lo < 80) return "var(--color-accent)"; // blue
    return "#22c55e"; // green
  }

  // Signal bar widths
  const signalMax = Math.max(...Object.values(data.by_signal), 1);

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-4">
      {/* Score distribution histogram */}
      <div className="rounded-xl p-4 border bg-[var(--color-bg-surface)] border-[var(--color-border)]">
        <h3 className="text-sm font-medium mb-4 text-[var(--color-text-secondary)]">
          Totalbetyg-fördelning ({data.total} aktier)
        </h3>
        <div className="flex items-end gap-1.5 h-36">
          {data.buckets.map((b) => {
            const heightPct = b.count > 0 ? Math.max((b.count / max) * 100, 8) : 0;
            return (
              <div key={b.range} className="flex-1 flex flex-col items-center gap-0.5 min-w-0">
                {/* Count label above bar */}
                <span className="text-[9px] text-[var(--color-text-muted)] tabular-nums leading-none">
                  {b.count > 0 ? b.count : ""}
                </span>
                <div
                  className="w-full rounded-sm transition-all duration-300"
                  style={{
                    height: heightPct > 0 ? `${heightPct}%` : "0",
                    background: bucketColor(b.range),
                    opacity: b.count > 0 ? 0.85 : 0,
                  }}
                  title={`${b.range}: ${b.count} aktier`}
                />
              </div>
            );
          })}
        </div>
        {/* Range labels */}
        <div className="flex mt-1 gap-1.5">
          {data.buckets.map((b) => (
            <div key={b.range} className="flex-1 text-center">
              <span className="text-[8px] text-[var(--color-text-muted)]">
                {b.range.split("-")[0]}
              </span>
            </div>
          ))}
        </div>
        {/* Color legend */}
        <div className="flex items-center gap-3 mt-2 flex-wrap">
          {[
            { color: "#ef4444", label: "Svagt (<40)" },
            { color: "#f59e0b", label: "Neutral (40-59)" },
            { color: "var(--color-accent)", label: "Bra (60-79)" },
            { color: "#22c55e", label: "Starkt (80+)" },
          ].map(({ color, label }) => (
            <div key={label} className="flex items-center gap-1">
              <span className="w-2.5 h-2.5 rounded-sm inline-block" style={{ background: color, opacity: 0.85 }} />
              <span className="text-[9px] text-[var(--color-text-muted)]">{label}</span>
            </div>
          ))}
        </div>
      </div>

      {/* By signal — horizontal bar chart */}
      <div className="rounded-xl p-4 border bg-[var(--color-bg-surface)] border-[var(--color-border)]">
        <h3 className="text-sm font-medium mb-4 text-[var(--color-text-secondary)]">Per köpläge</h3>
        <dl className="space-y-3">
          {Object.entries(data.by_signal).map(([sig, count]) => {
            const pct = data.total > 0 ? (count / data.total) * 100 : 0;
            const barPct = (count / signalMax) * 100;
            const sigColor: Record<string, string> = {
              STARK: "#22c55e",
              OK: "var(--color-accent)",
              "VÄNTA": "#f59e0b",
              EJ_AKTUELL: "#6b7280",
            };
            return (
              <div key={sig} className="space-y-1">
                <div className="flex justify-between text-xs">
                  <dt className="font-medium text-[var(--color-text-primary)]">{sig}</dt>
                  <dd className="font-mono tabular text-[var(--color-text-muted)]">
                    {count} <span className="text-[10px]">({pct.toFixed(0)}%)</span>
                  </dd>
                </div>
                <div className="h-1.5 rounded-full bg-[var(--color-border)] overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all duration-500"
                    style={{
                      width: `${barPct}%`,
                      background: sigColor[sig] ?? "var(--color-accent)",
                    }}
                  />
                </div>
              </div>
            );
          })}
        </dl>
      </div>
    </div>
  );
}

// ─── Inställningar ───────────────────────────────────────────────────────────

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      onClick={() => { navigator.clipboard.writeText(text); setCopied(true); setTimeout(() => setCopied(false), 2000); }}
      className="ml-1.5 p-0.5 rounded text-[var(--color-text-muted)] hover:text-[var(--color-accent)] transition-colors"
      title="Kopiera"
    >
      {copied ? <CheckCircle2 size={12} className="text-[var(--color-up)]" /> : <Copy size={12} />}
    </button>
  );
}

function SetupBlock({ icon: Icon, title, ok, children }: {
  icon: React.ElementType; title: string; ok?: boolean; children: React.ReactNode;
}) {
  return (
    <div className={`rounded-xl p-4 border space-y-3 ${ok === false ? "border-[var(--color-down)]/30 bg-[var(--color-down)]/5" : "border-[var(--color-border)] bg-[var(--color-bg-surface)]"}`}>
      <div className="flex items-center gap-2">
        <Icon size={14} strokeWidth={1.5} className={ok === false ? "text-[var(--color-down)]" : "text-[var(--color-accent)]"} />
        <h3 className="text-sm font-medium text-[var(--color-text-primary)]">{title}</h3>
        {ok === true && <span className="ml-auto text-[10px] text-[var(--color-up)] font-medium">✓ konfigurerad</span>}
        {ok === false && <span className="ml-auto text-[10px] text-[var(--color-down)] font-medium">⚠ saknas</span>}
      </div>
      {children}
    </div>
  );
}

function CodeSnip({ code }: { code: string }) {
  return (
    <div className="flex items-start gap-1 bg-[var(--color-bg-elevated)] rounded-lg p-2 font-mono text-[10px] text-[var(--color-text-secondary)] break-all">
      <span className="flex-1">{code}</span>
      <CopyButton text={code} />
    </div>
  );
}

export function SettingsSection() {
  // Reuse health data to know which env vars are set
  const { data: health } = useQuery({
    queryKey: ["admin-health"],
    queryFn: () => api<{
      env: Record<string, boolean>;
      db: Record<string, number | string | null>;
      checks: { name: string; ok: boolean; detail?: string }[];
    }>(`/api/admin/health`),
    staleTime: 30_000,
  });

  const env = health?.env ?? {};

  return (
    <div className="space-y-4 mt-4">

      {/* ── GH_DISPATCH_TOKEN ─────────────────────────────────── */}
      <SetupBlock icon={GitBranch} title="GH_DISPATCH_TOKEN — Pipeline-trigger" ok={env.gh_token}>
        <p className="text-xs text-[var(--color-text-muted)]">
          Krävs för att starta pipelines från admin-panelen. Skapa ett GitHub Personal Access Token (classic) med scope <code className="bg-[var(--color-bg-elevated)] px-1 rounded">workflow</code>.
        </p>
        <ol className="text-xs text-[var(--color-text-muted)] space-y-1 list-decimal list-inside">
          <li>Gå till <a href="https://github.com/settings/tokens/new" target="_blank" rel="noopener noreferrer" className="text-[var(--color-accent)] hover:underline">github.com/settings/tokens/new</a></li>
          <li>Välj scope: <strong>workflow</strong> (ger rättighet till Actions)</li>
          <li>Kopiera token och lägg till som env var i Vercel API-projektet:</li>
        </ol>
        <CodeSnip code="GH_DISPATCH_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxx" />
        <p className="text-[10px] text-[var(--color-text-muted)]">
          Vercel: <em>marketscan-api → Settings → Environment Variables → Add</em>. Redeploya efter sparad variabel.
        </p>
      </SetupBlock>

      {/* ── R2 Storage ────────────────────────────────────────── */}
      <SetupBlock icon={Cloud} title="R2 Storage — Cloudflare" ok={env.r2}>
        <p className="text-xs text-[var(--color-text-muted)]">
          Används för att spara pipeline-artefakter (parquet, rapporter). Utan R2 lagras inget utanför Supabase.
        </p>
        <ol className="text-xs text-[var(--color-text-muted)] space-y-1 list-decimal list-inside">
          <li>Cloudflare Dashboard → R2 → Skapa bucket (t.ex. <code className="bg-[var(--color-bg-elevated)] px-1 rounded">marketscan</code>)</li>
          <li>R2 → Overview → Manage R2 API Tokens → Create API Token (Object Read & Write)</li>
          <li>Kopiera: Access Key ID, Secret Access Key, och endpoint-URL</li>
          <li>Sätt dessa tre env vars i Vercel API-projektet:</li>
        </ol>
        <div className="space-y-1">
          <CodeSnip code="R2_KEY_ID=<Access Key ID>" />
          <CodeSnip code="R2_SECRET=<Secret Access Key>" />
          <CodeSnip code="R2_ENDPOINT=https://<account-id>.r2.cloudflarestorage.com" />
          <CodeSnip code="R2_BUCKET=marketscan" />
        </div>
      </SetupBlock>

      {/* ── Supabase Service Role ─────────────────────────────── */}
      <SetupBlock icon={Key} title="Supabase Service Role Key" ok={env.supabase}>
        <p className="text-xs text-[var(--color-text-muted)]">
          Krävs för admin-operationer (ta bort konton, se alla profiler). Den vanliga anon-nyckeln räcker för läsning.
        </p>
        <ol className="text-xs text-[var(--color-text-muted)] space-y-1 list-decimal list-inside">
          <li>Supabase Dashboard → Project → Settings → API</li>
          <li>Kopiera <strong>service_role</strong> secret (INTE anon-nyckeln)</li>
          <li>Sätt i Vercel API-projektet:</li>
        </ol>
        <CodeSnip code="SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." />
        <p className="text-[10px] text-[var(--color-down)]">
          ⚠ service_role bypasses RLS — använd ALDRIG i frontend-koden.
        </p>
      </SetupBlock>

      {/* ── Admin-roll i Supabase ─────────────────────────────── */}
      <SetupBlock icon={Users} title="Sätt admin-roll (SQL)" ok={undefined}>
        <p className="text-xs text-[var(--color-text-muted)]">
          Kör i Supabase SQL Editor (ersätt e-postadressen):
        </p>
        <CodeSnip code={`UPDATE auth.users\nSET raw_app_meta_data = raw_app_meta_data || '{"role":"admin"}'::jsonb\nWHERE email = 'din@epost.se';\n\nUPDATE profiles SET role = 'admin' WHERE id = (\n  SELECT id FROM auth.users WHERE email = 'din@epost.se'\n);`} />
        <p className="text-[10px] text-[var(--color-text-muted)]">Logga ut och in igen efter SQL:en — JWT måste förnyas.</p>
      </SetupBlock>

      {/* ── Databas-migrationer ───────────────────────────────── */}
      <SetupBlock icon={Table2} title="Databasmigrationer" ok={undefined}>
        <p className="text-xs text-[var(--color-text-muted)]">
          Kör dessa SQL-filer i Supabase SQL Editor om du inte gjort det:
        </p>
        <div className="space-y-1 text-xs text-[var(--color-text-muted)]">
          {[
            { file: "012_profile_extensions.sql", desc: "experience_level, onboarding, tema, email-notiser" },
            { file: "018_rls_hardening.sql", desc: "RLS-policys + client_errors-tabell" },
            { file: "022_fund_holdings.sql", desc: "fund_holdings-tabell" },
          ].map(({ file, desc }) => (
            <div key={file} className="flex items-start gap-2 p-2 rounded-lg bg-[var(--color-bg-elevated)]">
              <Database size={11} strokeWidth={1.5} className="text-[var(--color-text-muted)] mt-0.5 shrink-0" />
              <div>
                <code className="font-mono text-[10px] text-[var(--color-text-primary)]">{file}</code>
                <p className="text-[10px] mt-0.5">{desc}</p>
              </div>
            </div>
          ))}
        </div>
        <a
          href="https://supabase.com/dashboard"
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 text-xs text-[var(--color-accent)] hover:underline"
        >
          <ExternalLink size={11} strokeWidth={1.5} />
          Öppna Supabase Dashboard
        </a>
      </SetupBlock>

      {/* ── Universum-storlek ─────────────────────────────────── */}
      <SetupBlock icon={TrendingUp} title="Universum-storlek (~558 aktier)">
        <p className="text-xs text-[var(--color-text-muted)]">
          Pipelinen kör som standard med segmenten <code className="bg-[var(--color-bg-elevated)] px-1 rounded">large_cap</code> + <code className="bg-[var(--color-bg-elevated)] px-1 rounded">mid_cap</code>.
          För att nå ~1500 aktier, kör även <strong>Småbolag</strong>-pipelines regelbundet (knappen ovan) och aktivera <code className="bg-[var(--color-bg-elevated)] px-1 rounded">small_cap</code> + <code className="bg-[var(--color-bg-elevated)] px-1 rounded">micro_cap</code> i pipeline-schemat.
        </p>
        <p className="text-xs text-[var(--color-text-muted)]">
          I GitHub Actions workflow <code className="bg-[var(--color-bg-elevated)] px-1 rounded">pipeline.yml</code>, lägg till ett nytt schemalagt steg med mode <code className="bg-[var(--color-bg-elevated)] px-1 rounded">smallcap</code> (kör t.ex. lördag kl. 08:00).
        </p>
      </SetupBlock>

    </div>
  );
}

// ─── Diagnostik (djup självtest) ───────────────────────────────────────────────

type DeepDiag = {
  ok: boolean;
  summary: string;
  issues: string[];
  env: {
    required: Record<string, { present: boolean; feature: string }>;
    optional: Record<string, { present: boolean; feature: string }>;
  };
  tables: Record<string, { exists: boolean; rows?: number; authenticated_read?: string; auth_error?: string }>;
  migrations: Record<string, boolean>;
};

export function DiagnosticsSection() {
  const { data, isLoading, error, refetch, isFetching } = useQuery({
    queryKey: ["admin-diag-deep"],
    queryFn: () => api<DeepDiag>("/api/admin/diagnostics/deep"),
    staleTime: 0,
  });

  if (isLoading) return <div className="py-10 text-center text-xs text-[var(--color-text-muted)]">Kör diagnostik…</div>;
  if (error) return <ErrorBlock message="Kunde inte köra diagnostik (är du admin?)" onRetry={refetch} />;
  if (!data) return null;

  return (
    <div className="space-y-4 mt-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {data.ok
            ? <CheckCircle2 size={18} className="text-[var(--color-up)]" />
            : <AlertTriangle size={18} className="text-[var(--color-warn)]" />}
          <span className="text-sm font-semibold text-[var(--color-text-primary)]">{data.summary}</span>
        </div>
        <button onClick={() => refetch()} disabled={isFetching}
          className="flex items-center gap-1 text-xs text-[var(--color-accent)] hover:underline disabled:opacity-50">
          <RefreshCw size={11} className={isFetching ? "animate-spin" : ""} /> Kör igen
        </button>
      </div>

      {/* Issues — the important part */}
      {data.issues.length > 0 && (
        <div className="rounded-xl border border-[var(--color-warn)]/40 bg-[var(--color-warn)]/5 p-3 space-y-1.5">
          <p className="text-xs font-semibold text-[var(--color-text-primary)]">Problem att åtgärda</p>
          {data.issues.map((iss, i) => (
            <div key={i} className="flex gap-2 text-xs text-[var(--color-text-secondary)]">
              <XCircle size={13} className="text-[var(--color-down)] shrink-0 mt-0.5" />
              <span>{iss}</span>
            </div>
          ))}
        </div>
      )}

      {/* Env */}
      <div className="rounded-xl border border-[var(--color-border)] p-3">
        <p className="text-xs font-semibold mb-2 text-[var(--color-text-primary)]">Miljövariabler</p>
        <div className="grid grid-cols-2 gap-1.5">
          {Object.entries(data.env.required).map(([k, v]) => (
            <div key={k} className="flex items-center gap-1.5 text-[11px]">
              {v.present ? <CheckCircle2 size={12} className="text-[var(--color-up)]" /> : <XCircle size={12} className="text-[var(--color-down)]" />}
              <span className="font-mono text-[var(--color-text-secondary)]">{k}</span>
            </div>
          ))}
          {Object.entries(data.env.optional).map(([k, v]) => (
            <div key={k} className="flex items-center gap-1.5 text-[11px] opacity-70">
              {v.present ? <CheckCircle2 size={12} className="text-[var(--color-up)]" /> : <AlertTriangle size={12} className="text-[var(--color-text-muted)]" />}
              <span className="font-mono text-[var(--color-text-muted)]">{k}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Tables */}
      <div className="rounded-xl border border-[var(--color-border)] p-3">
        <p className="text-xs font-semibold mb-2 text-[var(--color-text-primary)]">Tabeller (authenticated-åtkomst)</p>
        <div className="space-y-1">
          {Object.entries(data.tables).map(([t, v]) => {
            const ok = v.exists && v.authenticated_read === "ok";
            return (
              <div key={t} className="flex items-center justify-between text-[11px]">
                <span className="flex items-center gap-1.5">
                  {ok ? <CheckCircle2 size={12} className="text-[var(--color-up)]" /> : <XCircle size={12} className="text-[var(--color-down)]" />}
                  <span className="font-mono text-[var(--color-text-secondary)]">{t}</span>
                </span>
                <span className="text-[var(--color-text-muted)]">
                  {!v.exists ? "saknas" : v.authenticated_read === "ok" ? `${v.rows ?? 0} rader` : "rättighet nekad"}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Migrations */}
      <div className="rounded-xl border border-[var(--color-border)] p-3">
        <p className="text-xs font-semibold mb-2 text-[var(--color-text-primary)]">Migrationer (härledda)</p>
        <div className="grid grid-cols-2 gap-1.5">
          {Object.entries(data.migrations).map(([m, applied]) => (
            <div key={m} className="flex items-center gap-1.5 text-[11px]">
              {applied ? <CheckCircle2 size={12} className="text-[var(--color-up)]" /> : <XCircle size={12} className="text-[var(--color-down)]" />}
              <span className="font-mono text-[var(--color-text-secondary)]">{m}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
