"use client";

import Link from "next/link";
import { Star, Bell, X, Plus, Trash2, ArrowRight } from "lucide-react";
import { useState } from "react";
import { useWatchlist } from "@/hooks/usePortfolio";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { InfoTooltip } from "@/components/ui/InfoTooltip";
import {
  formatPrice, formatPctChange, formatScore, signalLabel, signalClass,
  scoreColorClass, changeClass,
} from "@/lib/format";
import { cn } from "@/lib/utils";

interface PriceAlert {
  id: string;
  ticker: string;
  condition: "above" | "below";
  target_price: number;
  note: string | null;
  active: boolean;
}

export function BevakninarView() {
  const { data: watchlist = [], isLoading } = useWatchlist();
  const { data: alerts = [] } = useQuery<PriceAlert[]>({
    queryKey: ["alerts"],
    queryFn: () => api("/api/alerts"),
    staleTime: 60_000,
  });
  const qc = useQueryClient();

  const [addTicker, setAddTicker] = useState("");
  const [showAlertForm, setShowAlertForm] = useState<string | null>(null); // ticker
  const [alertPrice, setAlertPrice] = useState("");
  const [alertCond, setAlertCond] = useState<"above" | "below">("below");
  const [alertNote, setAlertNote] = useState("");

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
      api("/api/alerts", { method: "POST", body: JSON.stringify(body) }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["alerts"] });
      setShowAlertForm(null); setAlertPrice(""); setAlertNote("");
      toast.success("Larm skapat");
    },
    onError: () => toast.error("Logga in för att skapa larm"),
  });

  const deleteAlert = useMutation({
    mutationFn: (id: string) => api(`/api/alerts/${id}`, { method: "DELETE" }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["alerts"] }); toast.success("Larm borttaget"); },
  });

  return (
    <div className="max-w-3xl space-y-8">

      {/* ── Bevakningar ─────────────────────────────────── */}
      <section>
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-semibold" style={{ color: "var(--color-text-primary)" }}>
              Bevakningar
            </h1>
            <span className="text-xs px-2 py-0.5 rounded-full"
                  style={{ background: "var(--color-bg-elevated)", color: "var(--color-text-muted)" }}>
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
              className="h-9 px-3 rounded-xl text-sm border w-40 uppercase focus:outline-none"
              style={{
                background: "var(--color-bg-surface)", borderColor: "var(--color-border)",
                color: "var(--color-text-primary)",
              }}
            />
            <button
              onClick={() => addTicker.trim() && addWatch.mutate(addTicker.trim())}
              disabled={!addTicker.trim() || addWatch.isPending}
              className="h-9 px-3 rounded-xl text-sm font-medium text-white disabled:opacity-40"
              style={{ background: "var(--color-accent)" }}
            >
              <Plus size={14} strokeWidth={2} />
            </button>
          </div>
        </div>

        {isLoading ? (
          <div className="space-y-2">
            {[1,2,3].map(i => <div key={i} className="skeleton h-16 rounded-xl" />)}
          </div>
        ) : watchlist.length === 0 ? (
          <div className="rounded-2xl border p-10 text-center"
               style={{ background: "var(--color-bg-surface)", borderColor: "var(--color-border)" }}>
            <Star size={28} strokeWidth={1} style={{ color: "var(--color-border-strong)", margin: "0 auto 10px" }} />
            <p className="text-sm font-medium" style={{ color: "var(--color-text-secondary)" }}>
              Inga bevakningar ännu
            </p>
            <p className="text-xs mt-1" style={{ color: "var(--color-text-muted)" }}>
              Sök efter en aktie och klicka "Bevaka" på aktiekortet
            </p>
            <Link href="/screener"
                  className="inline-flex items-center gap-1 mt-3 text-xs"
                  style={{ color: "var(--color-accent)" }}>
              Gå till aktier <ArrowRight size={11} strokeWidth={1.5} />
            </Link>
          </div>
        ) : (
          <div className="rounded-2xl border overflow-hidden"
               style={{ borderColor: "var(--color-border)" }}>
            {watchlist.map((item) => (
              <div key={item.ticker}>
                <div
                  className="flex items-center gap-4 px-5 py-4 border-b transition-colors hover:bg-[var(--color-bg-elevated)]"
                  style={{ background: "var(--color-bg-surface)", borderColor: "var(--color-border)" }}
                >
                  <Link href={`/aktie/${item.ticker}`} className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-semibold" style={{ color: "var(--color-text-primary)" }}>
                        {item.ticker.replace(".ST", "")}
                      </span>
                      {item.entry_signal && (
                        <span className={cn("px-2 py-0.5 rounded text-[11px] font-medium",
                                            signalClass(item.entry_signal))}>
                          {signalLabel(item.entry_signal)}
                        </span>
                      )}
                    </div>
                    <div className="text-xs mt-0.5 truncate" style={{ color: "var(--color-text-muted)" }}>
                      {item.name}
                    </div>
                  </Link>

                  {item.score_total != null && (
                    <span className={cn("text-sm font-bold tabular", scoreColorClass(item.score_total))}>
                      {formatScore(item.score_total)}
                    </span>
                  )}

                  <div className="text-right">
                    <div className="text-sm tabular" style={{ color: "var(--color-text-primary)" }}>
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
                    className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs border transition-colors"
                    style={{
                      borderColor: alerts.some(a => a.ticker === item.ticker)
                        ? "var(--color-warn)" : "var(--color-border)",
                      color: alerts.some(a => a.ticker === item.ticker)
                        ? "var(--color-warn)" : "var(--color-text-muted)",
                    }}
                    title="Sätt prisriktkurslarm"
                  >
                    <Bell size={12} strokeWidth={1.5}
                          fill={alerts.some(a => a.ticker === item.ticker) ? "currentColor" : "none"} />
                    Larm
                  </button>

                  <button
                    onClick={() => removeWatch.mutate(item.ticker)}
                    className="transition-colors"
                    style={{ color: "var(--color-text-muted)" }}
                    aria-label="Ta bort bevakning"
                  >
                    <X size={15} strokeWidth={1.5} />
                  </button>
                </div>

                {/* Inline alarm form */}
                {showAlertForm === item.ticker && (
                  <div className="px-5 py-4 border-b"
                       style={{ background: "var(--color-bg-elevated)", borderColor: "var(--color-border)" }}>
                    <p className="text-xs font-medium mb-3" style={{ color: "var(--color-text-secondary)" }}>
                      Skapa prisriktkurslarm för {item.ticker.replace(".ST", "")}
                      <InfoTooltip text="Du får ett meddelande när aktiekursen når din angivna nivå." />
                    </p>
                    <div className="flex items-center gap-2 flex-wrap">
                      <select
                        value={alertCond}
                        onChange={(e) => setAlertCond(e.target.value as "above" | "below")}
                        className="h-8 px-2 rounded-lg text-xs border focus:outline-none"
                        style={{ background: "var(--color-bg-surface)", borderColor: "var(--color-border)", color: "var(--color-text-primary)" }}
                      >
                        <option value="below">Under</option>
                        <option value="above">Över</option>
                      </select>
                      <input
                        type="number" min="0" step="0.01"
                        value={alertPrice}
                        onChange={(e) => setAlertPrice(e.target.value)}
                        placeholder={`Riktkurs (nu ~${item.price ? Math.round(item.price) : "—"})`}
                        className="h-8 px-3 rounded-lg text-xs border focus:outline-none w-44"
                        style={{ background: "var(--color-bg-surface)", borderColor: "var(--color-border)", color: "var(--color-text-primary)" }}
                      />
                      <input
                        value={alertNote}
                        onChange={(e) => setAlertNote(e.target.value)}
                        placeholder="Anteckning (valfri)"
                        className="h-8 px-3 rounded-lg text-xs border focus:outline-none flex-1"
                        style={{ background: "var(--color-bg-surface)", borderColor: "var(--color-border)", color: "var(--color-text-primary)" }}
                      />
                      <button
                        disabled={!alertPrice || createAlert.isPending}
                        onClick={() => createAlert.mutate({
                          ticker: item.ticker,
                          condition: alertCond,
                          target_price: parseFloat(alertPrice),
                          note: alertNote || undefined,
                        })}
                        className="h-8 px-3 rounded-lg text-xs font-medium text-white disabled:opacity-40"
                        style={{ background: "var(--color-accent)" }}
                      >
                        Spara larm
                      </button>
                      <button onClick={() => setShowAlertForm(null)}
                              className="h-8 px-2 rounded-lg text-xs"
                              style={{ color: "var(--color-text-muted)" }}>
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
            <Bell size={15} strokeWidth={1.5} style={{ color: "var(--color-warn)" }} />
            <h2 className="text-sm font-semibold" style={{ color: "var(--color-text-primary)" }}>
              Aktiva larm
            </h2>
            <InfoTooltip text="Larm aktiveras när aktiekursen når din angivna nivå vid nästa dagliga uppdatering." />
          </div>
          <div className="rounded-2xl border overflow-hidden"
               style={{ borderColor: "var(--color-border)" }}>
            {alerts.map((alert, i) => (
              <div
                key={alert.id}
                className="flex items-center gap-4 px-5 py-3.5 border-b last:border-b-0"
                style={{ background: "var(--color-bg-surface)", borderColor: "var(--color-border)" }}
              >
                <Bell size={13} strokeWidth={1.5} style={{ color: "var(--color-warn)", flexShrink: 0 }} />
                <div className="flex-1 min-w-0">
                  <span className="text-sm font-semibold" style={{ color: "var(--color-text-primary)" }}>
                    {alert.ticker.replace(".ST", "")}
                  </span>
                  <span className="text-xs ml-2" style={{ color: "var(--color-text-muted)" }}>
                    {alert.condition === "below" ? "under" : "över"}{" "}
                    <span className="tabular font-medium" style={{ color: "var(--color-text-secondary)" }}>
                      {formatPrice(alert.target_price)}
                    </span>
                  </span>
                  {alert.note && (
                    <span className="text-xs ml-2 italic" style={{ color: "var(--color-text-muted)" }}>
                      — {alert.note}
                    </span>
                  )}
                </div>
                <button
                  onClick={() => deleteAlert.mutate(alert.id)}
                  className="transition-colors"
                  style={{ color: "var(--color-text-muted)" }}
                >
                  <Trash2 size={13} strokeWidth={1.5} />
                </button>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
