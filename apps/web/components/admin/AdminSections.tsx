import { useQuery } from "@tanstack/react-query";
import { RefreshCw } from "lucide-react";
import { api } from "@/lib/api";
import { KpiCard, StatusPill, RunsTable, DistTable, type PipelineRun } from "./StatusHelpers";

export function StatusSection() {
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
              {data.last_runs.map((run, i) => (
                <tr key={run.id} className="bg-[var(--color-bg-surface)] border-b border-[var(--color-border)]">
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

export function PipelineSection() {
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

export function UniversumSection() {
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

export function MattSection() {
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

export function SettingsSection() {
  return (
    <div className="rounded-xl p-5 border bg-[var(--color-bg-surface)] border-[var(--color-border)]">
      <p className="text-sm text-[var(--color-text-secondary)]">
        Faktorvikter, feature flags och användarhantering konfigureras via miljövariabler
        och Supabase-dashboard. Direktredigering av vikter implementeras i nästa fas.
      </p>
    </div>
  );
}
