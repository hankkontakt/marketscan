"use client";

import { useState } from "react";
import Link from "next/link";
import {
  FlaskConical, Play, Plus, Trash2, BarChart2, ChevronRight,
  Lock, Globe, Loader2, Check, X, Clock, RefreshCw,
  Filter, History, TrendingUp, ChevronDown,
} from "lucide-react";
import {
  useStrategies, useCreateStrategy, useDeleteStrategy, useTriggerBacktest,
} from "@/hooks/useStrategies";
import type { Strategy, StrategyRun } from "@/types/strategy";
import { cn } from "@/lib/utils";
import { toast } from "sonner";

// ─── Helpers ──────────────────────────────────────────────────────────────────

function RunStatusBadge({ status }: { status: StrategyRun["status"] }) {
  const configs = {
    pending:   { color: "text-yellow-400 bg-yellow-400/10", label: "Köar…" },
    running:   { color: "text-blue-400 bg-blue-400/10",    label: "Kör…" },
    completed: { color: "text-emerald-400 bg-emerald-400/10", label: "Klar" },
    failed:    { color: "text-red-400 bg-red-400/10",      label: "Fel" },
  };
  const { color, label } = configs[status] ?? configs.pending;
  return (
    <span className={cn("text-xs px-2 py-0.5 rounded-full font-medium", color)}>
      {(status === "pending" || status === "running") && (
        <Loader2 size={10} className="inline mr-1 animate-spin" />
      )}
      {label}
    </span>
  );
}

function MetricPill({ label, value, positive }: { label: string; value: string | null; positive?: boolean | null }) {
  const color = positive === true ? "text-emerald-400" : positive === false ? "text-red-400" : "text-[var(--color-text-primary)]";
  return (
    <div className="flex flex-col items-center">
      <span className={cn("text-base font-semibold tabular-nums", color)}>{value ?? "–"}</span>
      <span className="text-xs text-[var(--color-text-muted)]">{label}</span>
    </div>
  );
}

// ─── Create strategy form ─────────────────────────────────────────────────────

type FormState = {
  name: string;
  description: string;
  score_min: string;
  entry_signal: string;
  max_positions: string;
  position_sizing: "equal" | "score_weighted" | "kelly";
  rebalance_freq: "daily" | "weekly" | "monthly" | "quarterly";
  initial_capital: string;
  is_public: boolean;
};

const INITIAL_FORM: FormState = {
  name: "",
  description: "",
  score_min: "60",
  entry_signal: "",
  max_positions: "15",
  position_sizing: "equal",
  rebalance_freq: "monthly",
  initial_capital: "100000",
  is_public: false,
};

function CreateStrategyForm({ onClose }: { onClose: () => void }) {
  const [form, setForm] = useState<FormState>(INITIAL_FORM);
  const create = useCreateStrategy();

  const f = (key: keyof FormState) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) =>
    setForm(prev => ({ ...prev, [key]: e.target.value }));

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.name.trim()) { toast.error("Strategi måste ha ett namn"); return; }

    const filter_json: Record<string, unknown> = {};
    if (form.score_min) filter_json.score_min = Number(form.score_min);
    if (form.entry_signal) filter_json.entry_signal = form.entry_signal;

    try {
      await create.mutateAsync({
        name:            form.name,
        description:     form.description || null,
        filter_json,
        max_positions:   Number(form.max_positions) || 15,
        position_sizing: form.position_sizing,
        rebalance_freq:  form.rebalance_freq,
        initial_capital: Number(form.initial_capital) || 100_000,
        commission_pct:  0.001,
        is_public:       form.is_public,
      });
      toast.success("Strategi skapad!");
      onClose();
    } catch {
      toast.error("Kunde inte skapa strategi");
    }
  }

  const inputCls = "w-full px-3 py-2 rounded-lg border border-[var(--color-border)] bg-[var(--color-bg-elevated)] text-sm text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-accent)]";

  return (
    <form onSubmit={submit} className="rounded-xl border border-[var(--color-border)] bg-[var(--color-bg-card)] p-5 space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-[var(--color-text-primary)]">Ny strategi</h3>
        <button type="button" onClick={onClose} className="p-1 hover:bg-[var(--color-bg-elevated)] rounded">
          <X size={16} />
        </button>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div className="sm:col-span-2">
          <label className="text-xs text-[var(--color-text-muted)] mb-1 block">Namn *</label>
          <input className={inputCls} value={form.name} onChange={f("name")} placeholder="T.ex. Kvalitets-momentum" required />
        </div>

        <div className="sm:col-span-2">
          <label className="text-xs text-[var(--color-text-muted)] mb-1 block">Beskrivning</label>
          <textarea className={cn(inputCls, "resize-none h-16")} value={form.description} onChange={f("description")} placeholder="Valfri beskrivning…" />
        </div>

        <div>
          <label className="text-xs text-[var(--color-text-muted)] mb-1 block">Minsta betyg (0–100)</label>
          <input className={inputCls} type="number" min="0" max="100" value={form.score_min} onChange={f("score_min")} />
        </div>

        <div>
          <label className="text-xs text-[var(--color-text-muted)] mb-1 block">Inträde-signal</label>
          <select className={inputCls} value={form.entry_signal} onChange={f("entry_signal")}>
            <option value="">Alla signaler</option>
            <option value="STARK">STARK</option>
            <option value="VÄNTA">VÄNTA</option>
            <option value="SVAG">SVAG</option>
          </select>
        </div>

        <div>
          <label className="text-xs text-[var(--color-text-muted)] mb-1 block">Max positioner</label>
          <input className={inputCls} type="number" min="1" max="50" value={form.max_positions} onChange={f("max_positions")} />
        </div>

        <div>
          <label className="text-xs text-[var(--color-text-muted)] mb-1 block">Viktning</label>
          <select className={inputCls} value={form.position_sizing} onChange={f("position_sizing") as any}>
            <option value="equal">Lika viktning</option>
            <option value="score_weighted">Betyg-viktad</option>
            <option value="kelly">Kelly-kriteriet (½)</option>
          </select>
        </div>

        <div>
          <label className="text-xs text-[var(--color-text-muted)] mb-1 block">Rebalansering</label>
          <select className={inputCls} value={form.rebalance_freq} onChange={f("rebalance_freq") as any}>
            <option value="daily">Dagligen</option>
            <option value="weekly">Veckovis</option>
            <option value="monthly">Månadsvis</option>
            <option value="quarterly">Kvartalsvis</option>
          </select>
        </div>

        <div>
          <label className="text-xs text-[var(--color-text-muted)] mb-1 block">Startkapital (kr)</label>
          <input className={inputCls} type="number" min="1000" value={form.initial_capital} onChange={f("initial_capital")} />
        </div>

        <div className="flex items-center gap-2 pt-4">
          <input type="checkbox" id="is_public" checked={form.is_public} onChange={e => setForm(p => ({ ...p, is_public: e.target.checked }))} className="rounded" />
          <label htmlFor="is_public" className="text-sm text-[var(--color-text-secondary)]">Dela offentligt</label>
        </div>
      </div>

      <div className="flex gap-2 pt-2">
        <button type="submit" disabled={create.isPending}
          className="flex-1 py-2 rounded-lg bg-[var(--color-accent)] text-white text-sm font-medium disabled:opacity-50 flex items-center justify-center gap-2">
          {create.isPending && <Loader2 size={14} className="animate-spin" />}
          Skapa strategi
        </button>
        <button type="button" onClick={onClose}
          className="px-4 py-2 rounded-lg bg-[var(--color-bg-elevated)] text-sm text-[var(--color-text-muted)]">
          Avbryt
        </button>
      </div>
    </form>
  );
}

// ─── Strategy card ────────────────────────────────────────────────────────────

function StrategyCard({ strategy }: { strategy: Strategy }) {
  const trigger = useTriggerBacktest();
  const del = useDeleteStrategy();

  const latestRun = strategy.strategy_runs?.[0];
  const totalReturn = latestRun?.total_return_pct;
  const sharpe = latestRun?.sharpe_ratio;
  const maxDD = latestRun?.max_drawdown_pct;

  async function handleRun() {
    try {
      const res = await trigger.mutateAsync(strategy.id);
      toast.success(`Backtest köat (run #${res.run_id.slice(0, 8)})`);
    } catch {
      toast.error("Kunde inte starta backtest");
    }
  }

  async function handleDelete() {
    if (!confirm(`Ta bort "${strategy.name}"?`)) return;
    try {
      await del.mutateAsync(strategy.id);
      toast.success("Strategi borttagen");
    } catch {
      toast.error("Kunde inte ta bort");
    }
  }

  return (
    <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-bg-card)] p-4 hover:border-[var(--color-border-strong)] transition-colors group">
      <div className="flex items-start justify-between gap-2 mb-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <h3 className="font-medium text-[var(--color-text-primary)] truncate">{strategy.name}</h3>
            {strategy.is_public
              ? <Globe size={12} className="text-[var(--color-text-muted)] shrink-0" />
              : <Lock size={12} className="text-[var(--color-text-muted)] shrink-0" />
            }
            {!strategy._is_own && (
              <span className="text-xs px-1.5 py-0.5 rounded bg-[var(--color-bg-elevated)] text-[var(--color-text-muted)]">Publik</span>
            )}
          </div>
          {strategy.description && (
            <p className="text-xs text-[var(--color-text-muted)] mt-0.5 truncate">{strategy.description}</p>
          )}
        </div>

        {latestRun?.status && <RunStatusBadge status={latestRun.status} />}
      </div>

      {/* Filter summary */}
      <div className="flex flex-wrap gap-1.5 mb-3">
        {strategy.filter_json?.entry_signal && (
          <span className="text-xs px-2 py-0.5 rounded-full bg-[var(--color-accent-soft)] text-[var(--color-accent)]">
            {strategy.filter_json.entry_signal}
          </span>
        )}
        {strategy.filter_json?.score_min && (
          <span className="text-xs px-2 py-0.5 rounded-full bg-[var(--color-bg-elevated)] text-[var(--color-text-muted)]">
            Betyg ≥ {strategy.filter_json.score_min}
          </span>
        )}
        <span className="text-xs px-2 py-0.5 rounded-full bg-[var(--color-bg-elevated)] text-[var(--color-text-muted)]">
          {strategy.max_positions} pos · {strategy.rebalance_freq === "monthly" ? "månadsvis" : strategy.rebalance_freq === "weekly" ? "veckovis" : strategy.rebalance_freq}
        </span>
      </div>

      {/* Metrics row */}
      {latestRun?.status === "completed" && (
        <div className="flex gap-4 mb-3 pt-3 border-t border-[var(--color-border)]">
          <MetricPill
            label="Avkastning"
            value={totalReturn != null ? `${totalReturn > 0 ? "+" : ""}${totalReturn.toFixed(1)}%` : null}
            positive={totalReturn != null ? totalReturn > 0 : null}
          />
          <MetricPill
            label="Sharpe"
            value={sharpe?.toFixed(2) ?? null}
            positive={sharpe != null ? sharpe >= 1 : null}
          />
          <MetricPill
            label="Max drawdown"
            value={maxDD != null ? `${maxDD.toFixed(1)}%` : null}
            positive={maxDD != null ? maxDD > -15 : null}
          />
        </div>
      )}

      {/* Actions */}
      <div className="flex items-center gap-2">
        {strategy._is_own && (
          <button
            onClick={handleRun}
            disabled={trigger.isPending || latestRun?.status === "pending" || latestRun?.status === "running"}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[var(--color-accent)] text-white text-xs font-medium disabled:opacity-50 hover:opacity-90 transition-opacity"
          >
            {trigger.isPending ? <Loader2 size={12} className="animate-spin" /> : <Play size={12} />}
            Kör backtest
          </button>
        )}
        {latestRun?.status === "completed" && (
          <Link
            href={`/strategi-lab/${strategy.id}`}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[var(--color-bg-elevated)] text-xs text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-colors"
          >
            <BarChart2 size={12} /> Visa resultat
          </Link>
        )}
        {strategy._is_own && (
          <button onClick={handleDelete} disabled={del.isPending}
            className="ml-auto p-1.5 rounded-lg text-[var(--color-text-muted)] hover:text-red-400 hover:bg-red-400/10 transition-colors">
            <Trash2 size={14} />
          </button>
        )}
      </div>
    </div>
  );
}

// ─── How it works explainer ───────────────────────────────────────────────────

function HowItWorksBox() {
  const [open, setOpen] = useState(false);

  const STEPS = [
    {
      icon: Filter,
      title: "Definiera dina regler",
      text: "Välj vilka aktier strategin ska köpa — t.ex. \"betyg ≥ 65 och köpsignal STARK\". Du sätter också max antal positioner (t.ex. 15 aktier) och hur du fördelar kapitalet.",
    },
    {
      icon: History,
      title: "Systemet spelar tillbaka historiken",
      text: "Backtestet går igenom varje dag i historiken och frågar: \"Vilka aktier uppfyllde dina regler denna dag?\" — precis som om du hade suttit vid datorn varje morgon och kört screener.",
    },
    {
      icon: TrendingUp,
      title: "Se resultatet",
      text: "Du får en graf som visar hur 100 000 kr hade vuxit (eller krympt), plus tre nyckeltal: Avkastning (%), Sharpe-kvot (avkastning per risk-enhet — över 1 är bra) och Max drawdown (största tillfälliga förlust).",
    },
  ];

  const TERMS = [
    { term: "Rebalansering", def: "Hur ofta portföljen justeras — månadsvis innebär att du säljer/köper en gång i månaden för att matcha dina regler igen." },
    { term: "Viktning", def: "Lika: alla aktier får lika stor del av kapitalet. Betyg-viktad: aktier med högre betyg får mer kapital. Kelly: matematisk formel som anpassar storleken efter sannolikhet." },
    { term: "Sharpe-kvot", def: "Mäter hur mycket avkastning du fick per riskenhet. Över 1 = bra, över 2 = utmärkt, under 0 = sämre än att stå i kassan." },
    { term: "Max drawdown", def: "Den värsta tillfälliga nedgången under perioden, t.ex. -18% betyder att portföljen som värst tappade 18% från en topp innan den återhämtade sig." },
  ];

  return (
    <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-bg-card)] overflow-hidden">
      {/* Always-visible header */}
      <button
        onClick={() => setOpen(v => !v)}
        className="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-[var(--color-bg-elevated)] transition-colors"
      >
        <div className="flex items-center gap-2">
          <FlaskConical size={14} strokeWidth={1.5} className="text-[var(--color-accent)]" />
          <span className="text-sm font-medium text-[var(--color-text-secondary)]">Vad är Strategi Lab?</span>
        </div>
        <ChevronDown
          size={14}
          strokeWidth={1.5}
          className={cn("text-[var(--color-text-muted)] transition-transform", open && "rotate-180")}
        />
      </button>

      {open && (
        <div className="px-4 pb-4 space-y-5 border-t border-[var(--color-border)]">

          {/* One-liner */}
          <p className="pt-3 text-sm text-[var(--color-text-primary)] leading-relaxed">
            Strategi Lab låter dig testa en köpregel mot historisk data — <em>utan att riskera riktiga pengar</em>.
            Du ser vad som hade hänt om du följt din strategi under de senaste månaderna.
          </p>

          {/* 3-step workflow */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {STEPS.map((s, i) => (
              <div key={i} className="rounded-lg p-3 bg-[var(--color-bg-elevated)] space-y-1.5">
                <div className="flex items-center gap-2">
                  <span className="w-5 h-5 rounded-full bg-[var(--color-accent)] text-white text-[10px] font-bold flex items-center justify-center shrink-0">
                    {i + 1}
                  </span>
                  <span className="text-xs font-semibold text-[var(--color-text-primary)]">{s.title}</span>
                </div>
                <p className="text-xs text-[var(--color-text-muted)] leading-relaxed">{s.text}</p>
              </div>
            ))}
          </div>

          {/* Example */}
          <div
            className="rounded-lg px-3 py-2.5 text-xs space-y-1"
            style={{
              background: "color-mix(in srgb, var(--color-accent) 6%, transparent)",
              border: "1px solid color-mix(in srgb, var(--color-accent) 20%, transparent)",
            }}
          >
            <p className="font-semibold text-[var(--color-text-secondary)]">Exempel: "Kvalitets-momentum"</p>
            <p className="text-[var(--color-text-muted)]">
              Betyg ≥ 65 · Signal STARK · Max 15 aktier · Lika viktning · Rebalansera månadsvis · Startkapital 100 000 kr
            </p>
            <p className="text-[var(--color-text-muted)]">
              → Backtestet visar: +34% avkastning, Sharpe 1.4, max drawdown -12%. Det innebär att strategin
              historiskt gett bra avkastning med måttlig risk.
            </p>
          </div>

          {/* Glossary */}
          <div className="space-y-1.5">
            <p className="text-xs font-semibold text-[var(--color-text-secondary)]">Ordlista</p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {TERMS.map(({ term, def }) => (
                <div key={term} className="text-xs">
                  <span className="font-medium text-[var(--color-text-primary)]">{term}: </span>
                  <span className="text-[var(--color-text-muted)]">{def}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Caveat */}
          <p className="text-[10px] text-[var(--color-text-muted)] border-t border-[var(--color-border)] pt-2">
            ⚠ Historisk avkastning är ingen garanti för framtida resultat. Backtest visar hur strategin <em>hade presterat</em> — inte hur den <em>kommer</em> att prestera. Använd som ett verktyg för att förstå en strategis karaktär, inte som en köprekommendation.
          </p>
        </div>
      )}
    </div>
  );
}

// ─── Main view ────────────────────────────────────────────────────────────────

export function StrategiLabView() {
  const { data: strategies = [], isLoading } = useStrategies(true);
  const [showCreate, setShowCreate] = useState(false);
  const [tab, setTab] = useState<"mine" | "public">("mine");

  const mine   = strategies.filter(s => s._is_own);
  const public_ = strategies.filter(s => !s._is_own);
  const shown  = tab === "mine" ? mine : public_;

  return (
    <div className="max-w-4xl space-y-6">

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-[var(--color-text-primary)]">Strategi Lab</h1>
          <p className="text-xs text-[var(--color-text-muted)] mt-0.5">
            Backtestar screener-strategier mot historisk data från score_history
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Link
            href="/signal-analytics"
            className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-[var(--color-bg-elevated)] text-xs text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-colors"
          >
            Signalanalys <ChevronRight size={12} />
          </Link>
          <button
            onClick={() => setShowCreate(v => !v)}
            className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-[var(--color-accent)] text-white text-xs font-medium"
          >
            <Plus size={14} /> Ny strategi
          </button>
        </div>
      </div>

      {/* How it works — expanded explainer */}
      <HowItWorksBox />

      {/* Create form */}
      {showCreate && <CreateStrategyForm onClose={() => setShowCreate(false)} />}

      {/* Tabs */}
      <div className="flex gap-1 border-b border-[var(--color-border)]">
        {([["mine", `Mina (${mine.length})`], ["public", `Publika (${public_.length})`]] as const).map(([id, label]) => (
          <button
            key={id}
            onClick={() => setTab(id)}
            className={cn(
              "px-4 py-2 text-sm font-medium transition-colors -mb-px",
              tab === id
                ? "text-[var(--color-accent)] border-b-2 border-[var(--color-accent)]"
                : "text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]"
            )}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Strategy grid */}
      {isLoading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-48 rounded-xl bg-[var(--color-bg-elevated)] animate-pulse" />
          ))}
        </div>
      ) : shown.length === 0 ? (
        <div className="flex flex-col items-center gap-4 py-16 text-center">
          <FlaskConical size={40} strokeWidth={1} className="text-[var(--color-text-muted)]" />
          <div>
            <p className="text-[var(--color-text-secondary)] font-medium">
              {tab === "mine" ? "Inga egna strategier än" : "Inga publika strategier"}
            </p>
            {tab === "mine" && (
              <p className="text-xs text-[var(--color-text-muted)] mt-1">
                Skapa din första strategi för att backtesta mot historiska data
              </p>
            )}
          </div>
          {tab === "mine" && (
            <button
              onClick={() => setShowCreate(true)}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-[var(--color-accent)] text-white text-sm"
            >
              <Plus size={14} /> Skapa strategi
            </button>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {shown.map(s => <StrategyCard key={s.id} strategy={s} />)}
        </div>
      )}
    </div>
  );
}
