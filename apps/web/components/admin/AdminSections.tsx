import React, { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import {
  RefreshCw, Play, Database, ExternalLink, CheckCircle2,
  XCircle, AlertTriangle, Copy, Key, Cloud, GitBranch, Table2,
  Users, TrendingUp,
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
