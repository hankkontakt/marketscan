"use client";

import { useEffect, useState } from "react";
import { Check } from "lucide-react";
import { useNotificationPrefs, useSaveNotificationPrefs, type NotificationPrefs } from "@/hooks/useNotificationPrefs";
import { cn } from "@/lib/utils";

const TOGGLES: { key: keyof NotificationPrefs; label: string; desc: string }[] = [
  { key: "on_new_stark",       label: "Ny STARK-signal",   desc: "När en bevakad aktie får köpläge STARK" },
  { key: "on_score_move",      label: "Betygsrörelse",     desc: "När betyget rör sig mer än din tröskel" },
  { key: "on_insider_cluster", label: "Insiderkluster",    desc: "När flera insiders köper en bevakad aktie" },
  { key: "on_mews_flag",       label: "Mångdubblar-flagga", desc: "När en bevakad aktie flaggas som kandidat" },
  { key: "on_earnings_memo",   label: "Rapportanalys",     desc: "När en ny AI-rapportanalys publiceras" },
];

export function NotificationSection() {
  const { data } = useNotificationPrefs();
  const save = useSaveNotificationPrefs();
  const [local, setLocal] = useState<NotificationPrefs | null>(null);

  useEffect(() => { if (data) setLocal(data); }, [data]);

  if (!local) {
    return <div className="mt-6 h-40 rounded-xl skeleton" />;
  }

  function set<K extends keyof NotificationPrefs>(key: K, val: NotificationPrefs[K]) {
    setLocal(p => p ? { ...p, [key]: val } : p);
  }

  return (
    <div className="mt-6 rounded-2xl border p-5 bg-[var(--color-bg-surface)] border-[var(--color-border)] space-y-5">
      <div>
        <h2 className="text-base font-semibold text-[var(--color-text-primary)]">Notiser</h2>
        <p className="text-xs text-[var(--color-text-muted)] mt-0.5">
          Få notiser i appen när något händer på dina bevakade aktier eller innehav.
        </p>
      </div>

      <div className="space-y-3">
        {TOGGLES.map(t => (
          <label key={t.key} className="flex items-start justify-between gap-4 cursor-pointer">
            <div>
              <p className="text-sm font-medium text-[var(--color-text-primary)]">{t.label}</p>
              <p className="text-xs text-[var(--color-text-muted)]">{t.desc}</p>
            </div>
            <button
              type="button"
              onClick={() => set(t.key, !local[t.key] as never)}
              className={cn("w-10 h-6 rounded-full transition-colors shrink-0 relative",
                local[t.key] ? "bg-[var(--color-accent)]" : "bg-[var(--color-bg-elevated)]")}
            >
              <span className={cn("absolute top-0.5 w-5 h-5 rounded-full bg-white transition-all",
                local[t.key] ? "left-[18px]" : "left-0.5")} />
            </button>
          </label>
        ))}
      </div>

      {/* Tröskel */}
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="text-sm font-medium text-[var(--color-text-primary)]">Tröskel för betygsrörelse</p>
          <p className="text-xs text-[var(--color-text-muted)]">Minsta förändring i poäng för en notis</p>
        </div>
        <input
          type="number" min={1} max={50}
          value={local.score_move_threshold}
          onChange={e => set("score_move_threshold", Math.max(1, Number(e.target.value)) as never)}
          className="w-16 h-8 px-2 rounded-lg text-sm text-center border bg-[var(--color-bg-elevated)] border-[var(--color-border)] text-[var(--color-text-primary)]"
        />
      </div>

      {/* E-post */}
      <label className="flex items-start justify-between gap-4 cursor-pointer border-t border-[var(--color-border)] pt-4">
        <div>
          <p className="text-sm font-medium text-[var(--color-text-primary)]">E-post för viktiga notiser</p>
          <p className="text-xs text-[var(--color-text-muted)]">Skicka även mejl vid insiderkluster och nya STARK-signaler</p>
        </div>
        <button
          type="button"
          onClick={() => set("email_enabled", !local.email_enabled as never)}
          className={cn("w-10 h-6 rounded-full transition-colors shrink-0 relative",
            local.email_enabled ? "bg-[var(--color-accent)]" : "bg-[var(--color-bg-elevated)]")}
        >
          <span className={cn("absolute top-0.5 w-5 h-5 rounded-full bg-white transition-all",
            local.email_enabled ? "left-[18px]" : "left-0.5")} />
        </button>
      </label>

      <button
        onClick={() => save.mutate(local)}
        disabled={save.isPending}
        className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium text-white bg-[var(--color-accent)] disabled:opacity-50"
      >
        <Check size={14} strokeWidth={2} />
        {save.isPending ? "Sparar…" : save.isSuccess ? "Sparat" : "Spara inställningar"}
      </button>
    </div>
  );
}
