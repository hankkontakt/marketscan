"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Activity, BarChart2, Users, Globe, Settings, CheckCircle, XCircle, Clock, RefreshCw,
} from "lucide-react";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

const SECTIONS = ["Status", "Pipeline", "Universum", "Mått", "Inställningar"] as const;
type Section = (typeof SECTIONS)[number];

const SECTION_ICONS = {
  Status: Activity,
  Pipeline: RefreshCw,
  Universum: Globe,
  Mått: BarChart2,
  Inställningar: Settings,
} as const;

export function KontrollpanelView() {
  const [section, setSection] = useState<Section>("Status");

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold text-[var(--color-text-primary)]">Kontrollpanel</h1>

      {/* Section tabs */}
      <div className="flex gap-1 flex-wrap">
        {SECTIONS.map((s) => {
          const Icon = SECTION_ICONS[s];
          return (
            <button
              key={s}
              onClick={() => setSection(s)}
              className={cn(
                "flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs transition-colors",
                section === s
                  ? "bg-[var(--color-accent)] text-white"
                  : "bg-[var(--color-bg-surface)] text-[var(--color-text-secondary)] border border-[var(--color-border)] hover:border-[var(--color-border-strong)]",
              )}
            >
              <Icon size={13} strokeWidth={1.5} />
              {s}
            </button>
          );
        })}
      </div>

      {section === "Status"      && <StatusSection />}
      {section === "Pipeline"    && <PipelineSection />}
      {section === "Universum"   && <UniversumSection />}
      {section === "Mått"        && <MattSection />}
      {section === "Inställningar" && <SettingsSection />}
    </div>
  );
}

// ─── Status ──────────────────────────────────────────────────────────────────

function StatusSection() {
  const { data, isLoading, refetch } = useQuery({
    queryKey: ["admin-status"],
    queryFn: () => api<{ scan_rows: number; last_runs: PipelineRun[] }>("/api/admin/status"),
    staleTime: 30_000,
  });

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h2 className="text-sm font-medium text-[var(--color-text-secondary)]">Systemstatus</h2>
        <button onClick={() => refetch()}
                className="text-xs text-[var(--color-accent)] flex items-center gap-1 hover:underline">
          <RefreshCw size={11} strokeWidth={1.5} />
          Uppdatera
        </button>
      </div>

      {isLoading ? <div className="skeleton h-24 rounded-xl" /> : (
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          <KpiCard label="Aktier i scan" value={String(data?.scan_rows ?? "—")} />
          <KpiCard
            label="Senaste körning"
            value={data?.last_runs[0]?.status ?? "—"}
            status={data?.last_runs[0]?.status}
          />
          <KpiCard
            label="Körtid"
            value={data?.last_runs[0]?.duration_s ? `${data.last_runs[0].duration_s}s` : "—"}
          />
        </div>
      )}

      {data?.last_runs && data.last_runs.length > 0 && (
        <div className="rounded-xl overflow-hidden border"
             style={{ borderColor: "var(--color-border)" }}>
          <table className="w-full text-xs border-collapse">
            <thead>
              <tr style={{ background: "var(--color-bg-surface)", borderBottom: "1px solid var(--color-border)" }}>
                {["Typ", "Status", "Ok", "Fel", "Tid", "Startat"].map((h) => (
                  <th key={h} className="px-4 py-2 text-left font-medium text-[var(--color-text-muted)]">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.last_runs.map((run, i) => (
                <tr key={run.id} style={{
                  background: i % 2 === 0 ? "var(--color-bg-base)" : "var(--color-bg-surface)",
                  borderBottom: "1px solid var(--color-border)",
                }}>
                  <td className="px-4 py-2.5 font-mono">{run.run_type}</td>
                  <td className="px-4 py-2.5">
                    <StatusPill status={run.status} />
                  </td>
                  <td className="px-4 py-2.5 tabular font-mono text-[var(--color-up)]">{run.tickers_ok}</td>
                  <td className="px-4 py-2.5 tabular font-mono text-[var(--color-down)]">{run.tickers_err}</td>
                  <td className="px-4 py-2.5 tabular font-mono text-[var(--color-text-muted)]">{run.duration_s}s</td>
                  <td className="px-4 py-2.5 text-[var(--color-text-muted)]">
                    {run.started_at ? new Date(run.started_at).toLocaleString("sv-SE") : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ─── Pipeline ─────────────────────────────────────────────────────────────────

function PipelineSection() {
  const { data: runs = [], isLoading, refetch } = useQuery({
    queryKey: ["pipeline-runs"],
    queryFn: () => api<PipelineRun[]>("/api/admin/pipeline-runs"),
    staleTime: 30_000,
  });

  return (
    <div className="space-y-4">
      <h2 className="text-sm font-medium text-[var(--color-text-secondary)]">Körningshistorik</h2>
      <p className="text-xs text-[var(--color-text-muted)]">
        Pipeline startas automatiskt av GitHub Actions (morgon 06:15, kväll 18:30, veckovis söndag 08:00).
        Manuell körning triggas via GitHub Actions workflow_dispatch.
      </p>
      {isLoading
        ? <div className="skeleton h-48 rounded-xl" />
        : <RunsTable runs={runs} />
      }
    </div>
  );
}

// ─── Universum ───────────────────────────────────────────────────────────────

function UniversumSection() {
  const { data, isLoading } = useQuery({
    queryKey: ["admin-universe"],
    queryFn: () => api<{
      by_sector: Record<string, number>;
      by_segment: Record<string, number>;
      by_country: Record<string, number>;
      low_liquidity: number;
      total: number;
    }>("/api/admin/universe"),
    staleTime: 60_000,
  });

  if (isLoading) return <div className="skeleton h-48 rounded-xl" />;
  if (!data) return null;

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
      <DistTable title="Per segment" data={data.by_segment} total={data.total} />
      <DistTable title="Per sektor" data={data.by_sector} total={data.total} />
      <DistTable title="Per land" data={data.by_country} total={data.total} />
    </div>
  );
}

// ─── Mått ─────────────────────────────────────────────────────────────────────

function MattSection() {
  const { data, isLoading } = useQuery({
    queryKey: ["score-distribution"],
    queryFn: () => api<{
      buckets: { range: string; count: number }[];
      total: number;
      by_signal: Record<string, number>;
    }>("/api/admin/score-distribution"),
    staleTime: 60_000,
  });

  if (isLoading) return <div className="skeleton h-48 rounded-xl" />;
  if (!data) return null;

  const max = Math.max(...data.buckets.map((b) => b.count), 1);

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      {/* Score distribution */}
      <div className="rounded-xl p-4 border"
           style={{ background: "var(--color-bg-surface)", borderColor: "var(--color-border)" }}>
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
      <div className="rounded-xl p-4 border"
           style={{ background: "var(--color-bg-surface)", borderColor: "var(--color-border)" }}>
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

// ─── Settings ────────────────────────────────────────────────────────────────

function SettingsSection() {
  return (
    <div className="rounded-xl p-5 border"
         style={{ background: "var(--color-bg-surface)", borderColor: "var(--color-border)" }}>
      <p className="text-sm text-[var(--color-text-secondary)]">
        Faktorvikter, feature flags och användarhantering konfigureras via miljövariabler
        och Supabase-dashboard. Direktredigering av vikter implementeras i nästa fas.
      </p>
    </div>
  );
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

interface PipelineRun {
  id: string;
  run_type: string;
  status: string;
  tickers_ok: number;
  tickers_err: number;
  duration_s: number;
  error_msg: string | null;
  started_at: string;
}

function KpiCard({ label, value, status }: { label: string; value: string; status?: string }) {
  return (
    <div className="rounded-xl p-4 border"
         style={{ background: "var(--color-bg-surface)", borderColor: "var(--color-border)" }}>
      <div className="text-xs text-[var(--color-text-muted)] mb-1">{label}</div>
      <div className="text-lg font-mono font-bold text-[var(--color-text-primary)]">
        {status ? <StatusPill status={status} /> : value}
      </div>
    </div>
  );
}

function StatusPill({ status }: { status: string }) {
  const styles: Record<string, { icon: React.ReactNode; cls: string }> = {
    success: { icon: <CheckCircle size={12} strokeWidth={1.5} />, cls: "text-[var(--color-up)]" },
    failed:  { icon: <XCircle size={12} strokeWidth={1.5} />,    cls: "text-[var(--color-down)]" },
    running: { icon: <Clock size={12} strokeWidth={1.5} />,       cls: "text-[var(--color-warn)]" },
  };
  const s = styles[status] ?? styles.running;
  return (
    <span className={cn("flex items-center gap-1 text-xs font-medium", s.cls)}>
      {s.icon}
      {status}
    </span>
  );
}

function RunsTable({ runs }: { runs: PipelineRun[] }) {
  return (
    <div className="rounded-xl overflow-hidden border"
         style={{ borderColor: "var(--color-border)" }}>
      <table className="w-full text-xs">
        <thead>
          <tr style={{ background: "var(--color-bg-surface)", borderBottom: "1px solid var(--color-border)" }}>
            {["Typ", "Status", "Ok", "Tid", "Startat"].map((h) => (
              <th key={h} className="px-4 py-2 text-left font-medium text-[var(--color-text-muted)]">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {runs.map((run, i) => (
            <tr key={run.id} style={{
              background: i % 2 === 0 ? "var(--color-bg-base)" : "var(--color-bg-surface)",
              borderBottom: "1px solid var(--color-border)",
            }}>
              <td className="px-4 py-2.5 font-mono">{run.run_type}</td>
              <td className="px-4 py-2.5"><StatusPill status={run.status} /></td>
              <td className="px-4 py-2.5 tabular font-mono">{run.tickers_ok}</td>
              <td className="px-4 py-2.5 tabular font-mono text-[var(--color-text-muted)]">{run.duration_s}s</td>
              <td className="px-4 py-2.5 text-[var(--color-text-muted)]">
                {new Date(run.started_at).toLocaleString("sv-SE")}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function DistTable({ title, data, total }: { title: string; data: Record<string, number>; total: number }) {
  return (
    <div className="rounded-xl p-4 border"
         style={{ background: "var(--color-bg-surface)", borderColor: "var(--color-border)" }}>
      <h3 className="text-sm font-medium mb-3 text-[var(--color-text-secondary)]">{title}</h3>
      <dl className="space-y-2">
        {Object.entries(data)
          .sort(([, a], [, b]) => b - a)
          .map(([key, count]) => (
            <div key={key} className="flex justify-between items-center">
              <dt className="text-xs text-[var(--color-text-secondary)] truncate mr-2">{key}</dt>
              <dd className="text-xs font-mono tabular shrink-0 text-[var(--color-text-primary)]">
                {count} <span className="text-[var(--color-text-muted)]">({((count / total) * 100).toFixed(0)}%)</span>
              </dd>
            </div>
          ))}
      </dl>
    </div>
  );
}
