"use client";

import Link from "next/link";
import { Star, X, Plus, Trash2, ArrowRight, Zap } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "@/lib/api";
import { toast } from "sonner";
import { useWatchlist } from "@/hooks/usePortfolio";
import {
  useAlertRules, useCreateAlertRule, useUpdateAlertRule, useDeleteAlertRule, useTriggeredAlerts,
} from "@/hooks/useAlerts";
import type { AlertRule, AlertRuleType, TriggeredAlert } from "@/types/alerts";
import { v3StockByTicker } from "@/lib/v3";
import type { DecisionProjectionV3 } from "@/lib/types/decision_v3";
import {
  THESIS_BAND_CONFIG, SETUP_STATE_CONFIG, RISK_STATE_CONFIG, DATA_GRADE_CONFIG,
  TRADABILITY_CONFIG, badgeFor, FALLBACK_THESIS, FALLBACK_SETUP, FALLBACK_RISK, FALLBACK_TRADABILITY,
} from "@/components/screener-v3/badges";
import { formatPrice, formatPctChange } from "@/lib/format";
import { cn } from "@/lib/utils";
import { EMPTY_STATES } from "@/lib/labels";

// ─── V3-utökade typer ─────────────────────────────────────────────────────────

/** De fem nya transition-regeltyperna (migration 088). */
type TransitionRuleType =
  | "thesis_transition"
  | "setup_transition"
  | "risk_transition"
  | "data_grade_transition"
  | "tradability_transition";

type RuleTypeOption = AlertRuleType | TransitionRuleType;

/** triggered_alerts.decision_id (migration 088) — saknas i bas-typen. */
interface TriggeredAlertV3 extends TriggeredAlert {
  decision_id?: string | null;
}

// ─── Regeltyper ───────────────────────────────────────────────────────────────

const RULE_TYPE_LABELS: Record<string, string> = {
  price_cross: "Prisnivå",
  score_change: "Betygsändring",
  signal_change: "Signaländring",
  screen_match: "Screen-match",
  insider_cluster: "Insiderkluster",
  volatility_spike: "Volatilitetsspik",
  thesis_transition: "Tes-transition",
  setup_transition: "Setup-transition",
  risk_transition: "Risk-transition",
  data_grade_transition: "Data-transition",
  tradability_transition: "Tradability-transition",
};

// Legacy-typer som går att konfigurera med det minimala formuläret (screen_match
// kräver compound-villkor och skapas via API) + de fem nya transition-typerna.
const RULE_TYPE_OPTIONS: RuleTypeOption[] = [
  "price_cross", "score_change", "signal_change", "insider_cluster", "volatility_spike",
  "thesis_transition", "setup_transition", "risk_transition", "data_grade_transition", "tradability_transition",
];

const TRANSITION_TYPES: ReadonlySet<string> = new Set([
  "thesis_transition", "setup_transition", "risk_transition", "data_grade_transition", "tradability_transition",
]);

function ruleSummary(rule: AlertRule): string {
  const t = rule.ticker ? rule.ticker.replace(".ST", "") : "Alla aktier";
  switch (rule.rule_type as string) {
    case "price_cross": {
      const c = rule.conditions?.[0];
      if (c && c.field === "price" && typeof c.value === "number") {
        return `${t} — kurs ${c.op === ">=" ? "når" : "faller under"} ${formatPrice(c.value)}`;
      }
      return `${t} — prisnivå`;
    }
    case "score_change":
      return `${t} — betyg ändras ≥ ${rule.score_change_min ?? 10} p`;
    case "signal_change":
      return `${t} — signal ändras`;
    case "screen_match":
      return `Matchar filter (${rule.conditions?.length ?? 0} villkor)`;
    case "insider_cluster":
      return `${t} — ≥ ${rule.insider_min_count ?? 2} insiderköp / 14 d`;
    case "volatility_spike":
      return `${t} — volatilitet +${rule.vol_spike_min_pct ?? 50}%`;
    case "thesis_transition":
      return `${t} — tes ändras mellan snapshots`;
    case "setup_transition":
      return `${t} — setup ändras mellan snapshots`;
    case "risk_transition":
      return `${t} — risk ändras mellan snapshots`;
    case "data_grade_transition":
      return `${t} — datakvalitet ändras mellan snapshots`;
    case "tradability_transition":
      return `${t} — tradability ändras mellan snapshots`;
    default:
      return `${t} — ${RULE_TYPE_LABELS[rule.rule_type] ?? rule.rule_type}`;
  }
}

// ─── V3-badges (Thesis/Setup/Risk/Data) ───────────────────────────────────────

function ProjectionBadges({ proj }: { proj: DecisionProjectionV3 }) {
  const thesis = badgeFor(THESIS_BAND_CONFIG, proj.thesis_band, FALLBACK_THESIS);
  const setup = badgeFor(SETUP_STATE_CONFIG, proj.setup_state, FALLBACK_SETUP);
  const risk = badgeFor(RISK_STATE_CONFIG, proj.risk_state, FALLBACK_RISK);
  const dataGrade = DATA_GRADE_CONFIG[proj.data_grade] ?? { label: proj.data_grade, bg: "bg-zinc-500/15", text: "text-zinc-500" };
  return (
    <>
      <span className={cn("inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border", thesis.bg, thesis.text, thesis.border)}>
        {thesis.label}
      </span>
      <span className={cn("inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium border", setup.bg, setup.text, setup.border)}>
        {setup.label}
      </span>
      <span className={cn("inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium border", risk.bg, risk.text, risk.border)}>
        {risk.label}
      </span>
      <span
        className={cn("inline-flex items-center justify-center w-5 h-5 rounded text-xs font-bold", dataGrade.bg, dataGrade.text)}
        title={`Datakvalitet ${proj.data_grade}`}
      >
        {dataGrade.label}
      </span>
    </>
  );
}

// ─── Vy ───────────────────────────────────────────────────────────────────────

export function BevakninarViewV3() {
  const { data: watchlist = [], isLoading: watchlistLoading } = useWatchlist();
  const qc = useQueryClient();

  // ── V3-projektioner för bevakade tickers (max 20, aldrig syntetiska) ──────
  const [projections, setProjections] = useState<Record<string, DecisionProjectionV3>>({});
  const [missing, setMissing] = useState<Record<string, string>>({});
  const [projLoading, setProjLoading] = useState(false);

  const loadProjections = useCallback(async (tickers: string[]) => {
    const limited = tickers.slice(0, 20);
    setProjLoading(true);
    setProjections({});
    setMissing({});
    try {
      const results = await Promise.allSettled(limited.map((t) => v3StockByTicker(t)));
      const projMap: Record<string, DecisionProjectionV3> = {};
      const missMap: Record<string, string> = {};
      results.forEach((result, i) => {
        const ticker = limited[i];
        if (result.status === "fulfilled") {
          projMap[ticker] = result.value;
        } else {
          const err = result.reason;
          if (err instanceof ApiError && err.status === 404) {
            missMap[ticker] = "Ingen publicerad projektion";
          } else if (err instanceof ApiError && err.status === 503) {
            missMap[ticker] = "Projektionskällan otillgänglig";
          } else if (err instanceof ApiError) {
            missMap[ticker] = err.message;
          } else {
            missMap[ticker] = "Kunde inte hämtas";
          }
        }
      });
      setProjections(projMap);
      setMissing(missMap);
    } finally {
      setProjLoading(false);
    }
  }, []);

  useEffect(() => {
    if (watchlist.length > 0) void loadProjections(watchlist.map((w) => w.ticker));
  }, [watchlist, loadProjections]);

  // ── Bevakningar (lägg till / ta bort) ──────────────────────────────────────
  const [addTicker, setAddTicker] = useState("");

  const removeWatch = useMutation({
    mutationFn: (ticker: string) => api(`/api/watchlist/${ticker}`, { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["watchlist"] }),
  });

  const addWatch = useMutation({
    mutationFn: (ticker: string) => api(`/api/watchlist/${ticker}`, { method: "POST" }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["watchlist"] }); setAddTicker(""); },
    onError: () => toast.error("Logga in för att bevaka aktier"),
  });

  // ── Smarta larm ────────────────────────────────────────────────────────────
  const { data: rules = [], isLoading: rulesLoading } = useAlertRules();
  const { data: triggered = [] } = useTriggeredAlerts({ limit: 20 });
  const createRule = useCreateAlertRule();
  const updateRule = useUpdateAlertRule();
  const deleteRule = useDeleteAlertRule();

  const [showRuleForm, setShowRuleForm] = useState(false);
  const [ruleName, setRuleName] = useState("");
  const [ruleType, setRuleType] = useState<RuleTypeOption>("price_cross");
  const [ruleTicker, setRuleTicker] = useState("");
  const [ruleThreshold, setRuleThreshold] = useState("");
  const [ruleDirection, setRuleDirection] = useState<"below" | "above">("below");

  const isTransitionType = TRANSITION_TYPES.has(ruleType);

  const thresholdRequired =
    !isTransitionType && (
      ruleType === "price_cross" || ruleType === "score_change" ||
      ruleType === "insider_cluster" || ruleType === "volatility_spike"
    );

  const thresholdPlaceholder =
    ruleType === "price_cross" ? "Riktkurs" :
    ruleType === "score_change" ? "Poängändring (min)" :
    ruleType === "insider_cluster" ? "Antal insiderköp (min)" :
    ruleType === "volatility_spike" ? "Volatilitetsökning % (min)" : "";

  const submitRule = () => {
    const ticker = ruleTicker.trim().toUpperCase() || null;
    const body: Omit<AlertRule, "id" | "user_id" | "created_at" | "last_triggered" | "trigger_count"> = {
      name: ruleName.trim(),
      rule_type: ruleType as AlertRuleType,
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

  const triggeredV3 = (triggered ?? []) as TriggeredAlertV3[];

  const inputCls =
    "h-8 px-3 rounded-lg text-xs border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 " +
    "text-zinc-900 dark:text-zinc-100 focus:outline-none focus:ring-2 focus:ring-emerald-500/40";

  return (
    <div className="w-full space-y-6 max-w-7xl mx-auto px-4 sm:px-6 py-6">

      {/* ── Bevakningar ─────────────────────────────────── */}
      <section>
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-semibold text-zinc-900 dark:text-zinc-50">
              Bevakningar
            </h1>
            <span className="text-xs px-2 py-0.5 rounded-full bg-zinc-100 dark:bg-zinc-800 text-zinc-500 dark:text-zinc-400">
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
              className={cn(inputCls, "w-40 uppercase")}
            />
            <button
              onClick={() => addTicker.trim() && addWatch.mutate(addTicker.trim())}
              disabled={!addTicker.trim() || addWatch.isPending}
              className="h-8 px-3 rounded-lg text-sm font-medium text-white disabled:opacity-40 bg-emerald-600 hover:bg-emerald-700 dark:bg-emerald-500 dark:hover:bg-emerald-600 transition-colors"
            >
              <Plus size={14} strokeWidth={2} />
            </button>
          </div>
        </div>

        {watchlistLoading ? (
          <div className="rounded-2xl border border-zinc-200 dark:border-zinc-800 overflow-hidden bg-white dark:bg-zinc-950">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="flex items-center gap-4 px-5 py-4 border-b last:border-b-0 border-zinc-100 dark:border-zinc-900">
                <div className="flex-1 min-w-0 space-y-2">
                  <div className="skeleton h-4 w-24 rounded" />
                  <div className="skeleton h-3 w-40 rounded" />
                </div>
                <div className="skeleton h-4 w-8 rounded" />
                <div className="space-y-1.5 text-right">
                  <div className="skeleton h-4 w-16 rounded ml-auto" />
                  <div className="skeleton h-3 w-12 rounded ml-auto" />
                </div>
                <div className="skeleton h-4 w-4 rounded" />
              </div>
            ))}
          </div>
        ) : watchlist.length === 0 ? (
          <div className="rounded-2xl border border-zinc-200 dark:border-zinc-800 overflow-hidden bg-white dark:bg-zinc-950">
            <div className="p-10 text-center">
              <Star size={28} strokeWidth={1} className="mx-auto mb-2.5 text-zinc-300 dark:text-zinc-600" />
              <p className="text-sm font-medium text-zinc-700 dark:text-zinc-300">
                {EMPTY_STATES.watchlist.title}
              </p>
              <p className="text-xs mt-1 text-zinc-500">
                {EMPTY_STATES.watchlist.description}
              </p>
              <Link href={EMPTY_STATES.watchlist.href}
                    className="inline-flex items-center gap-1 mt-3 text-xs text-emerald-600 dark:text-emerald-400">
                {EMPTY_STATES.watchlist.action} <ArrowRight size={11} strokeWidth={1.5} />
              </Link>
            </div>

            {/* Suggestion row */}
            <div className="border-t border-zinc-100 dark:border-zinc-900 px-5 py-3 bg-zinc-50/50 dark:bg-zinc-900/50">
              <p className="text-xs text-zinc-500 mb-2">
                Förslag på aktier att börja bevaka:
              </p>
              <div className="flex flex-wrap gap-2">
                {["INVE-B.ST", "VOLV-B.ST", "ERIC-B.ST", "SEB-A.ST", "ATCO-A.ST"].map((ticker) => (
                  <button
                    key={ticker}
                    onClick={() => addWatch.mutate(ticker)}
                    disabled={addWatch.isPending}
                    className="px-3 py-1.5 rounded-lg text-xs border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 text-zinc-600 dark:text-zinc-300 hover:border-emerald-500/50 hover:text-emerald-600 dark:hover:text-emerald-400 transition-colors"
                  >
                    <Plus size={10} strokeWidth={2} className="inline mr-1" />
                    {ticker.replace(".ST", "")}
                  </button>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <div className="rounded-2xl border border-zinc-200 dark:border-zinc-800 overflow-hidden bg-white dark:bg-zinc-950">
            {watchlist.map((item) => {
              const proj = projections[item.ticker];
              const missReason = missing[item.ticker];
              const tradability = proj ? badgeFor(TRADABILITY_CONFIG, proj.tradability_state, FALLBACK_TRADABILITY) : null;

              return (
                <div
                  key={item.ticker}
                  className="flex items-center gap-4 px-5 py-4 border-b last:border-b-0 border-zinc-100 dark:border-zinc-900 hover:bg-zinc-50/80 dark:hover:bg-zinc-900/50 transition-colors"
                >
                  <Link href={`/aktie/${item.ticker}`} className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-semibold text-zinc-900 dark:text-zinc-100 truncate">
                        {proj?.name ?? item.name ?? item.ticker.replace(".ST", "")}
                      </span>
                      {proj && tradability && proj.tradability_state !== "ACTIVE" && (
                        <span className={cn("inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium border shrink-0", tradability.bg, tradability.text, tradability.border)}>
                          {tradability.label}
                        </span>
                      )}
                    </div>
                    <div className="font-mono text-xs mt-0.5 text-zinc-500">
                      {item.ticker.replace(".ST", "")}
                    </div>
                  </Link>

                  {/* V3-badges: Thesis / Setup / Risk / Data */}
                  <div className="flex items-center gap-1.5 flex-wrap justify-end max-w-[440px] shrink-0">
                    {projLoading ? (
                      <span className="text-xs text-zinc-400">Laddar…</span>
                    ) : proj ? (
                      <ProjectionBadges proj={proj} />
                    ) : missReason ? (
                      <span className="text-xs text-zinc-400" title={missReason}>{missReason}</span>
                    ) : null}
                  </div>

                  {/* Kurs / Idag */}
                  <div className="text-right shrink-0">
                    <div className="text-sm tabular text-zinc-900 dark:text-zinc-100">
                      {proj?.price != null
                        ? formatPrice(proj.price, proj.currency)
                        : item.price != null ? formatPrice(item.price) : "—"}
                    </div>
                    {proj?.change_pct != null ? (
                      <div className={cn("text-xs tabular", proj.change_pct >= 0 ? "text-emerald-600 dark:text-emerald-400" : "text-rose-600 dark:text-rose-400")}>
                        {formatPctChange(proj.change_pct)}
                      </div>
                    ) : item.change_pct != null ? (
                      <div className={cn("text-xs tabular", item.change_pct >= 0 ? "text-emerald-600 dark:text-emerald-400" : "text-rose-600 dark:text-rose-400")}>
                        {formatPctChange(item.change_pct)}
                      </div>
                    ) : null}
                  </div>

                  <button
                    onClick={() => removeWatch.mutate(item.ticker)}
                    className="transition-colors text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-300 shrink-0"
                    aria-label="Ta bort bevakning"
                  >
                    <X size={15} strokeWidth={1.5} />
                  </button>
                </div>
              );
            })}
            {watchlist.length > 20 && (
              <div className="px-5 py-2.5 border-t border-zinc-100 dark:border-zinc-900 text-[11px] text-zinc-400 bg-zinc-50/50 dark:bg-zinc-900/50">
                V3-projektioner visas för de 20 första bevakningarna.
              </div>
            )}
          </div>
        )}
      </section>

      {/* ── Smarta larm ─────────────────────────────────── */}
      <section>
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Zap size={15} strokeWidth={1.5} className="text-emerald-600 dark:text-emerald-400" />
            <h2 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
              Smarta larm
            </h2>
            <span className="text-xs px-2 py-0.5 rounded-full bg-zinc-100 dark:bg-zinc-800 text-zinc-500 dark:text-zinc-400">
              {rules.length}
            </span>
          </div>
          <button
            onClick={() => setShowRuleForm(!showRuleForm)}
            className="flex items-center gap-1 h-9 px-3 rounded-xl text-sm font-medium text-white bg-emerald-600 hover:bg-emerald-700 dark:bg-emerald-500 dark:hover:bg-emerald-600 transition-colors"
          >
            <Plus size={14} strokeWidth={2} />
            Ny regel
          </button>
        </div>

        {/* Ny regel-formulär */}
        {showRuleForm && (
          <div className="px-5 py-4 mb-4 rounded-2xl border border-zinc-200 dark:border-zinc-800 bg-zinc-50/50 dark:bg-zinc-900/50">
            <p className="text-xs font-medium mb-3 text-zinc-600 dark:text-zinc-300">
              Skapa en smart larmregel
            </p>
            <div className="flex items-center gap-2 flex-wrap">
              <input
                value={ruleName}
                onChange={(e) => setRuleName(e.target.value)}
                placeholder="Namn på regeln"
                className={cn(inputCls, "w-40")}
              />
              <select
                value={ruleType}
                onChange={(e) => setRuleType(e.target.value as RuleTypeOption)}
                className={cn(inputCls, "px-2 w-auto")}
              >
                {RULE_TYPE_OPTIONS.map((t) => (
                  <option key={t} value={t}>{RULE_TYPE_LABELS[t]}</option>
                ))}
              </select>
              <input
                value={ruleTicker}
                onChange={(e) => setRuleTicker(e.target.value.toUpperCase())}
                placeholder="Ticker (valfri)"
                className={cn(inputCls, "w-28")}
              />
              {thresholdRequired ? (
                <>
                  {ruleType === "price_cross" && (
                    <select
                      value={ruleDirection}
                      onChange={(e) => setRuleDirection(e.target.value as "below" | "above")}
                      className={cn(inputCls, "px-2 w-auto")}
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
                    className={cn(inputCls, "w-36")}
                  />
                </>
              ) : (
                <span className="text-xs text-zinc-500">
                  {isTransitionType ? "Ren transition — inga villkor" : "Fler inställningar via API"}
                </span>
              )}
              <button
                disabled={!ruleName.trim() || (thresholdRequired && !ruleThreshold.trim()) || createRule.isPending}
                onClick={submitRule}
                className="h-8 px-3 rounded-lg text-xs font-medium text-white disabled:opacity-40 bg-emerald-600 hover:bg-emerald-700 dark:bg-emerald-500 dark:hover:bg-emerald-600 transition-colors"
              >
                Spara regel
              </button>
              <button onClick={() => setShowRuleForm(false)}
                      className="h-8 px-2 rounded-lg text-xs text-zinc-500">
                <X size={12} />
              </button>
            </div>
          </div>
        )}

        {rulesLoading ? (
          <div className="rounded-2xl border border-zinc-200 dark:border-zinc-800 overflow-hidden bg-white dark:bg-zinc-950">
            {Array.from({ length: 2 }).map((_, i) => (
              <div key={i} className="flex items-center gap-4 px-5 py-4 border-b last:border-b-0 border-zinc-100 dark:border-zinc-900">
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
          <div className="rounded-2xl border border-zinc-200 dark:border-zinc-800 overflow-hidden bg-white dark:bg-zinc-950">
            <div className="p-8 text-center">
              <Zap size={24} strokeWidth={1} className="mx-auto mb-2.5 text-zinc-300 dark:text-zinc-600" />
              <p className="text-sm font-medium text-zinc-700 dark:text-zinc-300">
                Inga smarta larm ännu
              </p>
              <p className="text-xs mt-1 text-zinc-500">
                Skapa en regel så får du notis när betyg, kurs, tes, setup, risk eller datakvalitet rör sig.
              </p>
            </div>
          </div>
        ) : (
          <div className="rounded-2xl border border-zinc-200 dark:border-zinc-800 overflow-hidden bg-white dark:bg-zinc-950">
            {rules.map((rule) => (
              <div
                key={rule.id}
                className="flex items-center gap-4 px-5 py-3.5 border-b last:border-b-0 border-zinc-100 dark:border-zinc-900"
              >
                <Zap size={13} strokeWidth={1.5} className="text-emerald-600 dark:text-emerald-400 shrink-0" />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold text-zinc-900 dark:text-zinc-100 truncate">
                      {rule.name}
                    </span>
                    <span className="text-[11px] px-2 py-0.5 rounded bg-zinc-100 dark:bg-zinc-800 text-zinc-500 dark:text-zinc-400">
                      {RULE_TYPE_LABELS[rule.rule_type] ?? rule.rule_type}
                    </span>
                    {!rule.active && (
                      <span className="text-[11px] text-zinc-500">Pausad</span>
                    )}
                  </div>
                  <div className="text-xs mt-0.5 text-zinc-500">
                    {ruleSummary(rule)}
                  </div>
                </div>
                <div className="text-right text-[11px] text-zinc-500 shrink-0">
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
                    rule.active ? "bg-emerald-600 dark:bg-emerald-500" : "bg-zinc-200 dark:bg-zinc-800")}
                >
                  <span className={cn("absolute top-0.5 w-5 h-5 rounded-full bg-white transition-all",
                    rule.active ? "left-[18px]" : "left-0.5")} />
                </button>
                <button
                  onClick={() => removeRule(rule.id)}
                  className="transition-colors text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-300"
                  aria-label="Ta bort larmregel"
                >
                  <Trash2 size={13} strokeWidth={1.5} />
                </button>
              </div>
            ))}
          </div>
        )}

        {/* Senaste utlösningar */}
        {triggeredV3.length > 0 && (
          <div className="mt-4">
            <h3 className="text-xs font-semibold mb-2 text-zinc-600 dark:text-zinc-300">
              Senaste utlösningar
            </h3>
            <div className="rounded-2xl border border-zinc-200 dark:border-zinc-800 overflow-hidden bg-white dark:bg-zinc-950">
              {triggeredV3.map((t) => (
                <div
                  key={t.id}
                  className="flex items-center gap-4 px-5 py-3 border-b last:border-b-0 border-zinc-100 dark:border-zinc-900"
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-zinc-900 dark:text-zinc-100 truncate">
                        {t.rule_name}
                      </span>
                      {t.ticker && (
                        <span className="text-xs text-zinc-500">
                          {t.ticker.replace(".ST", "")}
                        </span>
                      )}
                    </div>
                    {t.detail && (
                      <div className="text-xs mt-0.5 text-zinc-500 truncate">
                        {t.detail}
                      </div>
                    )}
                    {t.decision_id && (
                      <div className="mt-1">
                        {t.ticker ? (
                          <Link
                            href={`/aktie/${t.ticker}`}
                            title={t.decision_id}
                            className="inline-flex items-center gap-1 text-[10px] font-mono text-zinc-400 hover:text-emerald-600 dark:hover:text-emerald-400 transition-colors"
                          >
                            <code className="truncate max-w-[220px]">{t.decision_id}</code>
                            <ArrowRight size={10} strokeWidth={1.5} />
                          </Link>
                        ) : (
                          <code title={t.decision_id} className="block font-mono text-[10px] text-zinc-400 truncate max-w-[220px]">
                            {t.decision_id}
                          </code>
                        )}
                      </div>
                    )}
                  </div>
                  <span className="text-[11px] text-zinc-500 shrink-0 tabular">
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