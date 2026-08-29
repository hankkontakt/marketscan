"use client";

import Link from "next/link";
import { Star, Bell, X, Plus, Trash2, ArrowRight, Zap } from "lucide-react";
import { useState } from "react";
import { useWatchlist } from "@/hooks/usePortfolio";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { InfoTooltip } from "@/components/ui/InfoTooltip";
import {
  useAlertRules, useCreateAlertRule, useUpdateAlertRule, useDeleteAlertRule, useTriggeredAlerts,
} from "@/hooks/useAlerts";
import type { AlertRule, AlertRuleType } from "@/types/alerts";
import {
  formatPrice, formatPctChange, formatScore, formatNumber, signalLabel, signalClass,
  scoreColorClass, changeClass,
} from "@/lib/format";
import { cn } from "@/lib/utils";
import { EMPTY_STATES } from "@/lib/labels";

interface PriceAlert {
  id: string;
  ticker: string;
  condition: "above" | "below";
  target_price: number;
  note: string | null;
  active: boolean;
}

// ─── Smarta larm ──────────────────────────────────────────────────────────────

const RULE_TYPE_LABELS: Record<AlertRuleType, string> = {
  price_cross: "Prisnivå",
  score_change: "Betygsändring",
  signal_change: "Signaländring",
  screen_match: "Screen-match",
  insider_cluster: "Insiderkluster",
  volatility_spike: "Volatilitetsspik",
};

// Typer som går att konfigurera med det minimala formuläret (övriga via API).
const RULE_TYPE_OPTIONS: AlertRuleType[] = [
  "price_cross", "score_change", "signal_change", "insider_cluster", "volatility_spike",
];

function ruleSummary(rule: AlertRule): string {
  const t = rule.ticker ? rule.ticker.replace(".ST", "") : "Alla aktier";
  switch (rule.rule_type) {
    case "price_cross": {
      const c = rule.conditions?.[0];
      if (c && c.field === "price" && typeof c.value === "number") {
        return `${t} — kurs ${c.op === ">=" ? "når" : "faller under"} ${formatPrice(c.value)}`;
      }
      return `${t} — prisnivå`;
    }
    case "score_change":
      return `${t} — betyg ändras ≥ ${formatNumber(rule.score_change_min ?? 10)} p`;
    case "signal_change":
      return `${t} — signal ändras`;
    case "screen_match":
      return `Matchar filter (${rule.conditions?.length ?? 0} villkor)`;
    case "insider_cluster":
      return `${t} — ≥ ${rule.insider_min_count ?? 2} insiderköp / 14 d`;
    case "volatility_spike":
      return `${t} — volatilitet +${rule.vol_spike_min_pct ?? 50}%`;
  }
}

export function BevakninarView() {
  const { data: watchlist = [], isLoading } = useWatchlist();
  const { data: alerts = [] } = useQuery<PriceAlert[]>({
    queryKey: ["alerts"],
    queryFn: () => api("/api/price-alerts"),
    staleTime: 60_000,
  });
  const qc = useQueryClient();

  const [addTicker, setAddTicker] = useState("");
  const [showAlertForm, setShowAlertForm] = useState<string | null>(null); // ticker
  const [alertPrice, setAlertPrice] = useState("");
  const [alertCond, setAlertCond] = useState<"above" | "below">("below");
  const [alertNote, setAlertNote] = useState("");

  // ── Smarta larm ────────────────────────────────────────────────────────────
  const { data: rules = [], isLoading: rulesLoading } = useAlertRules();
  const { data: triggered = [] } = useTriggeredAlerts({ limit: 5 });
  const createRule = useCreateAlertRule();
  const updateRule = useUpdateAlertRule();
  const deleteRule = useDeleteAlertRule();

  const [showRuleForm, setShowRuleForm] = useState(false);
  const [ruleName, setRuleName] = useState("");
  const [ruleType, setRuleType] = useState<AlertRuleType>("price_cross");
  const [ruleTicker, setRuleTicker] = useState("");
  const [ruleThreshold, setRuleThreshold] = useState("");
  const [ruleDirection, setRuleDirection] = useState<"below" | "above">("below");

  const thresholdRequired =
    ruleType === "price_cross" || ruleType === "score_change" ||
    ruleType === "insider_cluster" || ruleType === "volatility_spike";

  const thresholdPlaceholder =
    ruleType === "price_cross" ? "Riktkurs" :
    ruleType === "score_change" ? "Poängändring (min)" :
    ruleType === "insider_cluster" ? "Antal insiderköp (min)" :
    ruleType === "volatility_spike" ? "Volatilitetsökning % (min)" : "";

  const submitRule = () => {
    const ticker = ruleTicker.trim().toUpperCase() || null;
    const body: Omit<AlertRule, "id" | "user_id" | "created_at" | "last_triggered" | "trigger_count"> = {
      name: ruleName.trim(),
      rule_type: ruleType,
      ticker,
      conditions: [],
      score_change_min: null,
      insider_min_count: null,
      vol_spike_min_pct: null,
      trigger_once: false,
      active: true,
    };
    if (ruleType === "price_cross") {
      const v = parseFloat(ruleThreshold);
      if (Number.isFinite(v)) {
        body.conditions = [{ field: "price", op: ruleDirection === "above" ? ">=" : "<=", value: v }];
      }
    } else if (ruleType === "score_change") {
      body.score_change_min = parseFloat(ruleThreshold) || null;
    } else if (ruleType === "insider_cluster") {
      body.insider_min_count = parseInt(ruleThreshold, 10) || null;
    } else if (ruleType === "volatility_spike") {
      body.vol_spike_min_pct = parseFloat(ruleThreshold) || null;
    }
    createRule.mutate(body, {
      onSuccess: () => {
        toast.success("Larmregel skapad");
        setShowRuleForm(false); setRuleName(""); setRuleTicker(""); setRuleThreshold("");
      },
      onError: () => toast.error("Kunde inte skapa larmregel"),
    });
  };

  const toggleRule = (rule: AlertRule) =>
    updateRule.mutate({ id: rule.id, active: !rule.active }, {
      onError: () => toast.error("Kunde inte uppdatera larmregel"),
    });

  const removeRule = (id: string) =>
    deleteRule.mutate(id, {
      onSuccess: () => toast.success("Larmregel borttagen"),
      onError: () => toast.error("Kunde inte ta bort larmregel"),
    });

  const removeWatch = useMutation({
    mutationFn: (ticker: string) => api(`/api/watchlist/${ticker}`, { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["watchlist"] }),
  });

  const addWatch = useMutation({
    mutationFn: (ticker: string) => api(`/api/watchlist/${ticker}`, { method: "POST" }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["watchlist"] }); setAddTicker(""); },
    onError: () => toast.error("Logga in för att bevaka aktier"),
  });

  const createAlert = useMutation({
    mutationFn: (body: { ticker: string; condition: string; target_price: number; note?: string }) =>
      api("/api/price-alerts", { method: "POST", body: JSON.stringify(body) }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["alerts"] });
      setShowAlertForm(null); setAlertPrice(""); setAlertNote("");
      toast.success("Larm skapat");
    },
    onError: () => toast.error("Logga in för att skapa larm"),
  });

  const deleteAlert = useMutation({
    mutationFn: (id: string) => api(`/api/price-alerts/${id}`, { method: "DELETE" }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["alerts"] }); toast.success("Larm borttaget"); },
  });

  return (
    <div className="max-w-3xl space-y-8">

      {/* ── Bevakningar ─────────────────────────────────── */}
      <section>
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-semibold text-[var(--color-text-primary)]">
              Bevakningar
            </h1>
            <span className="text-xs px-2 py-0.5 rounded-full bg-[var(--color-bg-elevated)] text-[var(--color-text-muted)]">
              {watchlist.length}
            </span>
          </div>

          {/* Quick-add */}
          <div className="flex gap-2">
            <input
              value={addTicker}
              onChange={(e) => setAddTicker(e.target.value.toUpperCase())}
              onKeyDown={(e) => e.key === "Enter" && addTicker.trim() && addWatch.mutate(addTicker.trim())}
              placeholder="Lägg till ticker..."
              className="h-9 px-3 rounded-xl text-sm border w-40 uppercase focus:outline-none bg-[var(--color-bg-surface)] border-[var(--color-border)] text-[var(--color-text-primary)]"
            />
            <button
              onClick={() => addTicker.trim() && addWatch.mutate(addTicker.trim())}
              disabled={!addTicker.trim() || addWatch.isPending}
              className="h-9 px-3 rounded-xl text-sm font-medium text-white disabled:opacity-40 bg-[var(--color-accent)]"
            >
              <Plus size={14} strokeWidth={2} />
            </button>
          </div>
        </div>

        {isLoading ? (
          <div className="rounded-2xl border overflow-hidden border-[var(--color-border)]">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="flex items-center gap-4 px-5 py-4 border-b border-[var(--color-border)] bg-[var(--color-bg-surface)]">
                <div className="flex-1 min-w-0 space-y-2">
                  <div className="skeleton h-4 w-24 rounded" />
                  <div className="skeleton h-3 w-40 rounded" />
                </div>
                <div className="skeleton h-4 w-8 rounded" />
                <div className="space-y-1.5 text-right">
                  <div className="skeleton h-4 w-16 rounded ml-auto" />
                  <div className="skeleton h-3 w-12 rounded ml-auto" />
                </div>
                <div className="skeleton h-7 w-14 rounded-lg" />
                <div className="skeleton h-4 w-4 rounded" />
              </div>
            ))}
          </div>
        ) : watchlist.length === 0 ? (
          <div className="rounded-2xl border overflow-hidden border-[var(--color-border)]">
            <div className="p-10 text-center bg-[var(--color-bg-surface)]">
              <Star size={28} strokeWidth={1} style={{ color: "var(--color-border-strong)", margin: "0 auto 10px" }} />
              <p className="text-sm font-medium text-[var(--color-text-secondary)]">
                {EMPTY_STATES.watchlist.title}
              </p>
              <p className="text-xs mt-1 text-[var(--color-text-muted)]">
                {EMPTY_STATES.watchlist.description}
              </p>
              <Link href={EMPTY_STATES.watchlist.href}
                    className="inline-flex items-center gap-1 mt-3 text-xs text-[var(--color-accent)]">
                {EMPTY_STATES.watchlist.action} <ArrowRight size={11} strokeWidth={1.5} />
              </Link>
            </div>

            {/* Suggestion row */}
            <div className="border-t border-[var(--color-border)] px-5 py-3 bg-[var(--color-bg-elevated)]">
              <p className="text-xs text-[var(--color-text-muted)] mb-2">
                Förslag på aktier att börja bevaka:
              </p>
              <div className="flex flex-wrap gap-2">
                {["INVE-B.ST", "VOLV-B.ST", "ERIC-B.ST", "SEB-A.ST", "ATCO-A.ST"].map((ticker) => (
                  <button
                    key={ticker}
                    onClick={() => addWatch.mutate(ticker)}
                    disabled={addWatch.isPending}
                    className="px-3 py-1.5 rounded-lg text-xs border transition-colors
                               bg-[var(--color-bg-surface)] border-[var(--color-border)]
                               text-[var(--color-text-secondary)]
                               hover:border-[var(--color-accent)] hover:text-[var(--color-accent)]"
                  >
                    <Plus size={10} strokeWidth={2} className="inline mr-1" />
                    {ticker.replace(".ST", "")}
                  </button>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <div className="rounded-2xl border overflow-hidden border-[var(--color-border)]">
            {watchlist.map((item) => (
              <div key={item.ticker}>
                <div
                  className="flex items-center gap-4 px-5 py-4 border-b transition-colors hover:bg-[var(--color-bg-elevated)] bg-[var(--color-bg-surface)] border-[var(--color-border)]"
                >
                  <Link href={`/aktie/${item.ticker}`} className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-semibold text-[var(--color-text-primary)] truncate">
                        {item.name}
                      </span>
                      {item.entry_signal && (
                        <span className={cn("px-2 py-0.5 rounded text-[11px] font-medium",
                                            signalClass(item.entry_signal))}>
                          {signalLabel(item.entry_signal)}
                        </span>
                      )}
                    </div>
                    <div className="font-mono text-xs mt-0.5 text-[var(--color-text-muted)]">
                      {item.ticker.replace(".ST", "")}
                    </div>
                  </Link>

                  {item.score_total != null && (
                    <span className={cn("text-sm font-bold tabular", scoreColorClass(item.score_total))}>
                      {formatScore(item.score_total)}
                    </span>
                  )}

                  <div className="text-right">
                    <div className="text-sm tabular text-[var(--color-text-primary)]">
                      {item.price != null ? formatPrice(item.price) : "—"}
                    </div>
                    {item.change_pct != null && (
                      <div className={cn("text-xs tabular", changeClass(item.change_pct))}>
                        {formatPctChange(item.change_pct)}
                      </div>
                    )}
                  </div>

                  {/* Larm-knapp */}
                  <button
                    onClick={() => setShowAlertForm(showAlertForm === item.ticker ? null : item.ticker)}
                    className={cn(
                      "flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs border transition-colors",
                      alerts.some(a => a.ticker === item.ticker)
                        ? "border-[var(--color-warn)] text-[var(--color-warn)]"
                        : "border-[var(--color-border)] text-[var(--color-text-muted)]",
                    )}
                    title="Sätt prisriktkurslarm"
                  >
                    <Bell size={12} strokeWidth={1.5}
                          fill={alerts.some(a => a.ticker === item.ticker) ? "currentColor" : "none"} />
                    Larm
                  </button>

                  <button
                    onClick={() => removeWatch.mutate(item.ticker)}
                    className="transition-colors text-[var(--color-text-muted)]"
                    aria-label="Ta bort bevakning"
                  >
                    <X size={15} strokeWidth={1.5} />
                  </button>
                </div>

                {/* Inline alarm form */}
                {showAlertForm === item.ticker && (
                  <div className="px-5 py-4 border-b bg-[var(--color-bg-elevated)] border-[var(--color-border)]">
                    <p className="text-xs font-medium mb-3 text-[var(--color-text-secondary)]">
                      Skapa prisriktkurslarm för {item.ticker.replace(".ST", "")}
                      <InfoTooltip text="Du får ett meddelande när aktiekursen når din angivna nivå." />
                    </p>
                    <div className="flex items-center gap-2 flex-wrap">
                      <select
                        value={alertCond}
                        onChange={(e) => setAlertCond(e.target.value as "above" | "below")}
                        className="h-8 px-2 rounded-lg text-xs border focus:outline-none bg-[var(--color-bg-surface)] border-[var(--color-border)] text-[var(--color-text-primary)]"
                      >
                        <option value="below">Under</option>
                        <option value="above">Över</option>
                      </select>
                      <input
                        type="number" min="0" step="0.01"
                        value={alertPrice}
                        onChange={(e) => setAlertPrice(e.target.value)}
                        placeholder={`Riktkurs (nu ~${item.price ? Math.round(item.price) : "—"})`}
                        className="h-8 px-3 rounded-lg text-xs border focus:outline-none w-44 bg-[var(--color-bg-surface)] border-[var(--color-border)] text-[var(--color-text-primary)]"
                      />
                      <input
                        value={alertNote}
                        onChange={(e) => setAlertNote(e.target.value)}
                        placeholder="Anteckning (valfri)"
                        className="h-8 px-3 rounded-lg text-xs border focus:outline-none flex-1 bg-[var(--color-bg-surface)] border-[var(--color-border)] text-[var(--color-text-primary)]"
                      />
                      <button
                        disabled={!alertPrice || createAlert.isPending}
                        onClick={() => createAlert.mutate({
                          ticker: item.ticker,
                          condition: alertCond,
                          target_price: parseFloat(alertPrice),
                          note: alertNote || undefined,
                        })}
                        className="h-8 px-3 rounded-lg text-xs font-medium text-white disabled:opacity-40 bg-[var(--color-accent)]"
                      >
                        Spara larm
                      </button>
                      <button onClick={() => setShowAlertForm(null)}
                              className="h-8 px-2 rounded-lg text-xs text-[var(--color-text-muted)]">
                        <X size={12} />
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </section>

      {/* ── Aktiva larm ─────────────────────────────────── */}
      {alerts.length > 0 && (
        <section>
          <div className="flex items-center gap-2 mb-4">
            <Bell size={15} strokeWidth={1.5} className="text-[var(--color-warn)]" />
            <h2 className="text-sm font-semibold text-[var(--color-text-primary)]">
              Aktiva larm
            </h2>
            <InfoTooltip text="Larm aktiveras när aktiekursen når din angivna nivå vid nästa dagliga uppdatering." />
          </div>
          <div className="rounded-2xl border overflow-hidden border-[var(--color-border)]">
            {alerts.map((alert) => (
              <div
                key={alert.id}
                className="flex items-center gap-4 px-5 py-3.5 border-b last:border-b-0 bg-[var(--color-bg-surface)] border-[var(--color-border)]"
              >
                <Bell size={13} strokeWidth={1.5} className="text-[var(--color-warn)] shrink-0" />
                <div className="flex-1 min-w-0">
                  <span className="text-sm font-semibold text-[var(--color-text-primary)]">
                    {alert.ticker.replace(".ST", "")}
                  </span>
                  <span className="text-xs ml-2 text-[var(--color-text-muted)]">
                    {alert.condition === "below" ? "under" : "över"}{" "}
                    <span className="tabular font-medium text-[var(--color-text-secondary)]">
                      {formatPrice(alert.target_price)}
                    </span>
                  </span>
                  {alert.note && (
                    <span className="text-xs ml-2 italic text-[var(--color-text-muted)]">
                      — {alert.note}
                    </span>
                  )}
                </div>
                <button
                  onClick={() => deleteAlert.mutate(alert.id)}
                  className="transition-colors text-[var(--color-text-muted)]"
                >
                  <Trash2 size={13} strokeWidth={1.5} />
                </button>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* ── Smarta larm ─────────────────────────────────── */}
      <section>
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Zap size={15} strokeWidth={1.5} className="text-[var(--color-accent)]" />
            <h2 className="text-sm font-semibold text-[var(--color-text-primary)]">
              Smarta larm
            </h2>
            <span className="text-xs px-2 py-0.5 rounded-full bg-[var(--color-bg-elevated)] text-[var(--color-text-muted)]">
              {rules.length}
            </span>
            <InfoTooltip text="Regler utvärderas vid nästa dagliga uppdatering. Fler inställningar (villkor, engångslarm) via API." />
          </div>
          <button
            onClick={() => setShowRuleForm(!showRuleForm)}
            className="flex items-center gap-1 h-9 px-3 rounded-xl text-sm font-medium text-white bg-[var(--color-accent)]"
          >
            <Plus size={14} strokeWidth={2} />
            Ny regel
          </button>
        </div>

        {/* Ny regel-formulär */}
        {showRuleForm && (
          <div className="px-5 py-4 mb-4 rounded-2xl border bg-[var(--color-bg-elevated)] border-[var(--color-border)]">
            <p className="text-xs font-medium mb-3 text-[var(--color-text-secondary)]">
              Skapa en smart larmregel
              <InfoTooltip text="Du får en notis när regeln utlöses vid nästa dagliga uppdatering." />
            </p>
            <div className="flex items-center gap-2 flex-wrap">
              <input
                value={ruleName}
                onChange={(e) => setRuleName(e.target.value)}
                placeholder="Namn på regeln"
                className="h-8 px-3 rounded-lg text-xs border focus:outline-none w-40 bg-[var(--color-bg-surface)] border-[var(--color-border)] text-[var(--color-text-primary)]"
              />
              <select
                value={ruleType}
                onChange={(e) => setRuleType(e.target.value as AlertRuleType)}
                className="h-8 px-2 rounded-lg text-xs border focus:outline-none bg-[var(--color-bg-surface)] border-[var(--color-border)] text-[var(--color-text-primary)]"
              >
                {RULE_TYPE_OPTIONS.map((t) => (
                  <option key={t} value={t}>{RULE_TYPE_LABELS[t]}</option>
                ))}
              </select>
              <input
                value={ruleTicker}
                onChange={(e) => setRuleTicker(e.target.value.toUpperCase())}
                placeholder="Ticker (valfri)"
                className="h-8 px-3 rounded-lg text-xs border focus:outline-none w-28 bg-[var(--color-bg-surface)] border-[var(--color-border)] text-[var(--color-text-primary)]"
              />
              {thresholdRequired ? (
                <>
                  {ruleType === "price_cross" && (
                    <select
                      value={ruleDirection}
                      onChange={(e) => setRuleDirection(e.target.value as "below" | "above")}
                      className="h-8 px-2 rounded-lg text-xs border focus:outline-none bg-[var(--color-bg-surface)] border-[var(--color-border)] text-[var(--color-text-primary)]"
                    >
                      <option value="below">Under</option>
                      <option value="above">Över</option>
                    </select>
                  )}
                  <input
                    type="number" min="0" step="0.01"
                    value={ruleThreshold}
                    onChange={(e) => setRuleThreshold(e.target.value)}
                    placeholder={thresholdPlaceholder}
                    className="h-8 px-3 rounded-lg text-xs border focus:outline-none w-36 bg-[var(--color-bg-surface)] border-[var(--color-border)] text-[var(--color-text-primary)]"
                  />
                </>
              ) : (
                <span className="text-xs text-[var(--color-text-muted)]">
                  Fler inställningar via API
                </span>
              )}
              <button
                disabled={!ruleName.trim() || (thresholdRequired && !ruleThreshold.trim()) || createRule.isPending}
                onClick={submitRule}
                className="h-8 px-3 rounded-lg text-xs font-medium text-white disabled:opacity-40 bg-[var(--color-accent)]"
              >
                Spara regel
              </button>
              <button onClick={() => setShowRuleForm(false)}
                      className="h-8 px-2 rounded-lg text-xs text-[var(--color-text-muted)]">
                <X size={12} />
              </button>
            </div>
          </div>
        )}

        {rulesLoading ? (
          <div className="rounded-2xl border overflow-hidden border-[var(--color-border)]">
            {Array.from({ length: 2 }).map((_, i) => (
              <div key={i} className="flex items-center gap-4 px-5 py-4 border-b border-[var(--color-border)] bg-[var(--color-bg-surface)]">
                <div className="flex-1 min-w-0 space-y-2">
                  <div className="skeleton h-4 w-32 rounded" />
                  <div className="skeleton h-3 w-48 rounded" />
                </div>
                <div className="skeleton h-6 w-10 rounded-full" />
                <div className="skeleton h-4 w-4 rounded" />
              </div>
            ))}
          </div>
        ) : rules.length === 0 ? (
          <div className="rounded-2xl border overflow-hidden border-[var(--color-border)]">
            <div className="p-8 text-center bg-[var(--color-bg-surface)]">
              <Zap size={24} strokeWidth={1} style={{ color: "var(--color-border-strong)", margin: "0 auto 10px" }} />
              <p className="text-sm font-medium text-[var(--color-text-secondary)]">
                Inga smarta larm ännu
              </p>
              <p className="text-xs mt-1 text-[var(--color-text-muted)]">
                Skapa en regel så får du notis när betyg, kurs eller signaler rör sig.
              </p>
            </div>
          </div>
        ) : (
          <div className="rounded-2xl border overflow-hidden border-[var(--color-border)]">
            {rules.map((rule) => (
              <div
                key={rule.id}
                className="flex items-center gap-4 px-5 py-3.5 border-b last:border-b-0 bg-[var(--color-bg-surface)] border-[var(--color-border)]"
              >
                <Zap size={13} strokeWidth={1.5} className="text-[var(--color-accent)] shrink-0" />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold text-[var(--color-text-primary)] truncate">
                      {rule.name}
                    </span>
                    <span className="text-[11px] px-2 py-0.5 rounded bg-[var(--color-bg-elevated)] text-[var(--color-text-muted)]">
                      {RULE_TYPE_LABELS[rule.rule_type]}
                    </span>
                    {!rule.active && (
                      <span className="text-[11px] text-[var(--color-text-muted)]">Pausad</span>
                    )}
                  </div>
                  <div className="text-xs mt-0.5 text-[var(--color-text-muted)]">
                    {ruleSummary(rule)}
                  </div>
                </div>
                <div className="text-right text-[11px] text-[var(--color-text-muted)] shrink-0">
                  {rule.trigger_count > 0 ? `${rule.trigger_count} utlösningar` : "Ej utlöst"}
                  {rule.last_triggered && (
                    <div className="tabular">
                      {new Date(rule.last_triggered).toLocaleDateString("sv-SE")}
                    </div>
                  )}
                </div>
                <button
                  type="button"
                  onClick={() => toggleRule(rule)}
                  aria-label={rule.active ? "Pausa regel" : "Aktivera regel"}
                  title={rule.active ? "Pausa" : "Aktivera"}
                  className={cn("w-10 h-6 rounded-full transition-colors shrink-0 relative",
                    rule.active ? "bg-[var(--color-accent)]" : "bg-[var(--color-bg-elevated)]")}
                >
                  <span className={cn("absolute top-0.5 w-5 h-5 rounded-full bg-white transition-all",
                    rule.active ? "left-[18px]" : "left-0.5")} />
                </button>
                <button
                  onClick={() => removeRule(rule.id)}
                  className="transition-colors text-[var(--color-text-muted)]"
                  aria-label="Ta bort larmregel"
                >
                  <Trash2 size={13} strokeWidth={1.5} />
                </button>
              </div>
            ))}
          </div>
        )}

        {/* Senaste utlösningar */}
        {triggered.length > 0 && (
          <div className="mt-4">
            <h3 className="text-xs font-semibold mb-2 text-[var(--color-text-secondary)]">
              Senaste utlösningar
            </h3>
            <div className="rounded-2xl border overflow-hidden border-[var(--color-border)]">
              {triggered.map((t) => (
                <div
                  key={t.id}
                  className="flex items-center gap-4 px-5 py-3 border-b last:border-b-0 bg-[var(--color-bg-surface)] border-[var(--color-border)]"
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-[var(--color-text-primary)] truncate">
                        {t.rule_name}
                      </span>
                      {t.ticker && (
                        <span className="text-xs text-[var(--color-text-muted)]">
                          {t.ticker.replace(".ST", "")}
                        </span>
                      )}
                    </div>
                    {t.detail && (
                      <div className="text-xs mt-0.5 text-[var(--color-text-muted)] truncate">
                        {t.detail}
                      </div>
                    )}
                  </div>
                  <span className="text-[11px] text-[var(--color-text-muted)] shrink-0 tabular">
                    {new Date(t.triggered_at).toLocaleDateString("sv-SE")}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
