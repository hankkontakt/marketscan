import React from "react";
import { cn } from "@/lib/utils";
import { CheckCircle, XCircle, Clock } from "lucide-react";

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

export const KpiCard = React.memo(function KpiCard({ label, value, status }: { label: string; value: string; status?: string }) {
  return (
    <div className="rounded-xl p-4 border bg-[var(--color-bg-surface)] border-[var(--color-border)]">
      <div className="text-xs text-[var(--color-text-muted)] mb-1">{label}</div>
      <div className="text-lg font-mono font-bold text-[var(--color-text-primary)]">
        {status ? <StatusPill status={status} /> : value}
      </div>
    </div>
  );
});

export const StatusPill = React.memo(function StatusPill({ status }: { status: string }) {
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
});

export function RunsTable({ runs }: { runs: PipelineRun[] }) {
  return (
    <div className="rounded-xl overflow-hidden border border-[var(--color-border)]">
      <table className="w-full text-xs">
        <thead>
          <tr className="bg-[var(--color-bg-surface)]" style={{ borderBottom: "1px solid var(--color-border)" }}>
            {["Typ", "Status", "Ok", "Tid", "Startat"].map((h) => (
              <th key={h} className="px-4 py-2 text-left font-medium text-[var(--color-text-muted)]">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {runs.map((run, i) => (
            <tr key={run.id} className="bg-[var(--color-bg-surface)]" style={{
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

export function DistTable({ title, data, total }: { title: string; data: Record<string, number>; total: number }) {
  return (
    <div className="rounded-xl p-4 border bg-[var(--color-bg-surface)] border-[var(--color-border)]">
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

export type { PipelineRun };
