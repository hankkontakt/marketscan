import { useQuery, useMutation } from "@tanstack/react-query";
import {
  RefreshCw, Play, Activity, Globe, Database, ExternalLink, CheckCircle2,
  XCircle, AlertTriangle,
} from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { KpiCard, StatusPill, RunsTable, DistTable, type PipelineRun } from "./StatusHelpers";
import { useState } from "react";

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

// ─── Pipeline ────────────────────────────────────────────────────────────────

const PIPELINE_MODES = [
  { mode: "morning", label: "Morgon" },
  { mode: "evening", label: "Kväll" },
  { mode: "weekly", label: "Vecka" },
  { mode: "smallcap", label: "Småbolag" },
  { mode: "refresh_missing", label: "Fyll saknad data" },
  { mode: "retry_rate_limited", label: "Kör om rate-limitade" },
] as const;

export function PipelineSection() {
  const { data: runs = [], isLoading, refetch } = useQuery({
    queryKey: ["pipeline-runs"],
    queryFn: () => api<PipelineRun[]>("/api/admin/pipeline-runs"),
    staleTime: 30_000,
  });

  const triggerMutation = useMutation({
    mutationFn: (body: { mode: string; tickers?: string[] }) =>
      api<{ status: string; mode: string; link: string }>("/api/admin/pipeline/trigger", {
        method: "POST",
        body: JSON.stringify(body),
      }),
  });

  const [targetedInput, setTargetedInput] = useState("");

  const handleTrigger = (mode: string) => {
    triggerMutation.mutate(
      { mode },
      { onSuccess: () => { setTimeout(refetch, 2000); } },
    );
  };

  const handleTargeted = () => {
    const tickers = targetedInput.split(",").map((t) => t.trim().toUpperCase()).filter(Boolean);
    if (tickers.length === 0) return;
    triggerMutation.mutate(
      { mode: "targeted", tickers },
      { onSuccess: () => {
        setTargetedInput("");
        setTimeout(refetch, 2000);
      }},
    );
  };

  return (
    <div className="space-y-5 mt-4">
      <div className="flex justify-between items-center">
        <h2 className="text-sm font-medium text-[var(--color-text-secondary)]">Pipeline-kontroll</h2>
      </div>

      {/* Trigger buttons */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2">
        {PIPELINE_MODES.map(({ mode, label }) => (
          <button
            key={mode}
            onClick={() => handleTrigger(mode)}
            disabled={triggerMutation.isPending}
            className="flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium
                       bg-[var(--color-accent-soft)] text-[var(--color-accent)] border border-[var(--color-accent)]/20
                       hover:bg-[var(--color-accent)]/20 transition-colors disabled:opacity-40"
          >
            <Play size={12} strokeWidth={1.5} />
            {label}
          </button>
        ))}
      </div>

      {triggerMutation.isSuccess && (
        <div className="flex items-center gap-2 text-xs text-[var(--color-up)]">
          <CheckCircle2 size={14} />
          Pipeline {triggerMutation.data?.mode} startad —
          <a href={triggerMutation.data?.link} target="_blank" rel="noopener noreferrer"
             className="text-[var(--color-accent)] hover:underline flex items-center gap-0.5">
            visa i GitHub <ExternalLink size={10} />
          </a>
        </div>
      )}
      {triggerMutation.isError && (
        <div className="flex items-center gap-2 text-xs text-[var(--color-down)]">
          <XCircle size={14} />
          {triggerMutation.error instanceof ApiError
            ? triggerMutation.error.message
            : "Kunde inte starta pipeline"}
        </div>
      )}

      {/* Targeted tickers */}
      <div className="rounded-xl p-4 border border-[var(--color-border)] bg-[var(--color-bg-surface)]">
        <h3 className="text-xs font-medium text-[var(--color-text-secondary)] mb-2">Riktade tickers</h3>
        <p className="text-[10px] text-[var(--color-text-muted)] mb-2">
          Komma-separerade tickers (max 50). Startar en pipeline som hämtar just dessa.
        </p>
        <div className="flex gap-2">
          <input
            type="text"
            value={targetedInput}
            onChange={(e) => setTargetedInput(e.target.value)}
            placeholder="VOLV-B.ST, TSLA, SSAB A.ST"
            className="flex-1 h-9 px-3 rounded-lg text-xs bg-[var(--color-bg-elevated)]
                       text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)]
                       outline-none border border-[var(--color-border)] focus:ring-2 focus:ring-[var(--color-accent)]"
          />
          <button
            onClick={handleTargeted}
            disabled={triggerMutation.isPending || !targetedInput.trim()}
            className="px-3 py-1.5 rounded-lg text-xs font-medium bg-[var(--color-accent)] text-white
                       hover:opacity-90 transition-opacity disabled:opacity-40"
          >
            Kör
          </button>
        </div>
      </div>

      {/* Runs history */}
      <p className="text-xs text-[var(--color-text-muted)]">
        Pipeline startas automatiskt av GitHub Actions (morgon 06:15, kväll 18:30, veckovis söndag 08:00).
        Manuell körning via knapparna ovan.
      </p>

      {isLoading
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

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-4">
      {/* Score distribution */}
      <div className="rounded-xl p-4 border bg-[var(--color-bg-surface)] border-[var(--color-border)]">
        <h3 className="text-sm font-medium mb-4 text-[var(--color-text-secondary)]">
          Totalbetyg-fördelning ({data.total} aktier)
        </h3>
        <div className="flex items-end gap-1 h-32">
          {data.buckets.map((b) => (
            <div key={b.range} className="flex-1 flex flex-col items-center gap-1">
              <div
                className="w-full rounded-t"
                style={{
                  height: `${(b.count / max) * 100}%`,
                  background: "var(--color-accent)",
                  opacity: 0.7,
                  minHeight: b.count > 0 ? 4 : 0,
                }}
                title={`${b.range}: ${b.count}`}
              />
            </div>
          ))}
        </div>
        <div className="flex justify-between mt-1">
          <span className="text-[10px] text-[var(--color-text-muted)]">0</span>
          <span className="text-[10px] text-[var(--color-text-muted)]">100</span>
        </div>
      </div>

      {/* By signal */}
      <div className="rounded-xl p-4 border bg-[var(--color-bg-surface)] border-[var(--color-border)]">
        <h3 className="text-sm font-medium mb-4 text-[var(--color-text-secondary)]">Per köpläge</h3>
        <dl className="space-y-3">
          {Object.entries(data.by_signal).map(([sig, count]) => (
            <div key={sig} className="flex justify-between">
              <dt className="text-xs text-[var(--color-text-secondary)]">{sig}</dt>
              <dd className="text-xs font-mono tabular text-[var(--color-text-primary)]">
                {count} ({((count / data.total) * 100).toFixed(0)}%)
              </dd>
            </div>
          ))}
        </dl>
      </div>
    </div>
  );
}

// ─── Inställningar ───────────────────────────────────────────────────────────

export function SettingsSection() {
  return (
    <div className="rounded-xl p-5 border bg-[var(--color-bg-surface)] border-[var(--color-border)] mt-4">
      <p className="text-sm text-[var(--color-text-secondary)]">
        Faktorvikter, feature flags och användarhantering konfigureras via miljövariabler
        och Supabase-dashboard. Direktredigering av vikter implementeras i nästa fas.
      </p>
    </div>
  );
}
