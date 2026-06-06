"use client";

import { useState } from "react";
import Link from "next/link";
import { MetricCard } from "@/components/ui/MetricCard";
import { Briefcase, Trash2, MessageSquare, PieChart, ShieldAlert, Plus, X, Check, TrendingUp, Building2, Target } from "lucide-react";
import { usePortfolio, useRemoveHolding, useAddHolding, usePortfolioRisk } from "@/hooks/usePortfolio";
import { toast } from "sonner";
import { api } from "@/lib/api";
import {
  formatPrice, formatPctChange, formatScore, signalLabel, signalClass,
  scoreColorClass, changeClass,
} from "@/lib/format";
import { PieChart as RechartsPie, Pie, Cell, Tooltip, ResponsiveContainer } from "recharts";
import { cn } from "@/lib/utils";
import { InfoTooltip } from "@/components/ui/InfoTooltip";

export function PortfoljView() {
  const { data: portfolio, isLoading } = usePortfolio();
  const remove = useRemoveHolding();
  const addHolding = useAddHolding();
  const [showAdd, setShowAdd] = useState(false);
  const [addTicker, setAddTicker] = useState("");
  const [addShares, setAddShares] = useState("");
  const [addCost, setAddCost] = useState("");
  const [aiQuestion, setAiQuestion] = useState("");
  const [aiResponse, setAiResponse] = useState("");
  const [aiLoading, setAiLoading] = useState("");
  const [chatHistory, setChatHistory] = useState<{ role: string; content: string }[]>([]);

  const holdings = portfolio?.holdings ?? [];

  const totalValue = holdings.reduce((sum, h) => sum + (h.price ?? 0) * h.shares, 0);
  const totalCost = holdings.reduce((sum, h) => sum + (h.cost_basis ?? 0) * h.shares, 0);
  const totalReturn = totalCost > 0 ? (totalValue - totalCost) / totalCost : null;

  async function askAI() {
    if (!aiQuestion.trim() || !portfolio) return;
    setAiLoading("Analyserar...");
    const context = {
      total_value: totalValue,
      total_return: totalReturn,
      holdings: holdings.map((h) => ({
        ticker: h.ticker, name: h.name, shares: h.shares,
        price: h.price, score_total: h.score_total, entry_signal: h.entry_signal,
      })),
    };
    try {
      const newHistory = [...chatHistory, { role: "user", content: aiQuestion }];
      const res = await api<{ response: string }>("/api/ai/portfolio-coach", {
        method: "POST",
        body: JSON.stringify({ question: aiQuestion, portfolio_context: context, history: chatHistory }),
      });
      setChatHistory([...newHistory, { role: "assistant", content: res.response }]);
      setAiResponse(res.response);
      setAiQuestion("");
    } catch {
      setAiResponse("Kunde inte kontakta AI just nu.");
    } finally {
      setAiLoading("");
    }
  }

  if (isLoading) return <PortfoljSkeleton />;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-xl font-semibold text-[var(--color-text-primary)]">Min portfölj</h1>
          <p className="text-xs mt-0.5 text-[var(--color-text-muted)]">
            {holdings.length} innehav
          </p>
        </div>
        <div className="flex items-center gap-3">
          {totalValue > 0 && (
            <div className="text-right">
              <div className="text-2xl font-bold tabular text-[var(--color-text-primary)]">
                {formatPrice(totalValue)}
              </div>
              {totalReturn != null && (
                <div className={cn("text-sm tabular", changeClass(totalReturn))}>
                  {formatPctChange(totalReturn)}{" "}
                  <span className="inline-flex items-center gap-1">
                    total avkastning
                    <InfoTooltip text="Portföljens totala avkastning sedan start." />
                  </span>
                </div>
              )}
            </div>
          )}
          <button
            onClick={() => setShowAdd(!showAdd)}
            className={cn(
              "flex items-center gap-1.5 px-3 py-2 rounded-xl text-sm font-medium border transition-colors",
              showAdd
                ? "bg-[var(--color-accent)] text-white border-[var(--color-accent)]"
                : "bg-[var(--color-bg-surface)] text-[var(--color-text-secondary)] border-[var(--color-border)]",
            )}
          >
            <Plus size={14} strokeWidth={1.5} />
            Lägg till
          </button>
        </div>
      </div>

      {/* Add holding form */}
      {showAdd && (
        <div className="rounded-2xl border p-5 space-y-4 bg-[var(--color-bg-surface)] border-[var(--color-border)]">
          <h3 className="text-sm font-semibold text-[var(--color-text-primary)]">
            Lägg till innehav
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div className="space-y-1">
              <label className="text-xs text-[var(--color-text-muted)]">Ticker</label>
              <input
                value={addTicker}
                onChange={(e) => setAddTicker(e.target.value.toUpperCase())}
                placeholder="t.ex. VOLV-B.ST"
                className="w-full h-9 px-3 rounded-lg text-sm border focus:outline-none uppercase bg-[var(--color-bg-elevated)] border-[var(--color-border)] text-[var(--color-text-primary)]"
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs text-[var(--color-text-muted)]">Antal aktier</label>
              <input
                type="number" min="0" step="1"
                value={addShares}
                onChange={(e) => setAddShares(e.target.value)}
                placeholder="100"
                className="w-full h-9 px-3 rounded-lg text-sm border focus:outline-none bg-[var(--color-bg-elevated)] border-[var(--color-border)] text-[var(--color-text-primary)]"
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs text-[var(--color-text-muted)]">Inköpskurs (valfri)</label>
              <input
                type="number" min="0" step="0.01"
                value={addCost}
                onChange={(e) => setAddCost(e.target.value)}
                placeholder="287,40"
                className="w-full h-9 px-3 rounded-lg text-sm border focus:outline-none bg-[var(--color-bg-elevated)] border-[var(--color-border)] text-[var(--color-text-primary)]"
              />
            </div>
          </div>
          <div className="flex gap-2">
            <button
              disabled={!addTicker || !addShares || addHolding.isPending}
              onClick={() => {
                if (!addTicker || !addShares) return;
                addHolding.mutate(
                  { ticker: addTicker, shares: parseFloat(addShares), cost_basis: addCost ? parseFloat(addCost) : undefined },
                  {
                    onSuccess: () => {
                      toast.success(`${addShares} aktier i ${addTicker} tillagda`);
                      setShowAdd(false); setAddTicker(""); setAddShares(""); setAddCost("");
                    },
                    onError: () => toast.error("Kunde inte lägga till innehavet"),
                  }
                );
              }}
              className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium text-white disabled:opacity-40 bg-[var(--color-accent)]"
            >
              <Check size={14} strokeWidth={2} />
              {addHolding.isPending ? "Sparar..." : "Lägg till"}
            </button>
            <button
              onClick={() => { setShowAdd(false); setAddTicker(""); setAddShares(""); setAddCost(""); }}
              className="px-4 py-2 rounded-lg text-sm border border-[var(--color-border)] text-[var(--color-text-muted)]"
            >
              Avbryt
            </button>
          </div>
        </div>
      )}

      {/* Holdings table */}
      {holdings.length === 0 ? (
        <EmptyPortfolio />
      ) : (
        <div className="rounded-xl overflow-hidden border border-[var(--color-border)]">
          <table className="w-full text-xs border-collapse">
            <thead>
              <tr className="bg-[var(--color-bg-surface)]" style={{ borderBottom: "1px solid var(--color-border)" }}>
                {["Aktie", "Antal", "Kurs", "Idag", "Värde", "Totalbetyg", "Köpläge", ""].map((h) => (
                  <th key={h} className="px-4 py-2.5 text-left text-[11px] font-medium text-[var(--color-text-muted)]">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {holdings.map((h, i) => (
                <tr
                  key={h.id}
                  className="bg-[var(--color-bg-surface)]"
                  style={{ borderBottom: "1px solid var(--color-border)" }}
                >
                  <td className="px-4 py-3">
                    <Link href={`/aktie/${h.ticker}`}
                          className="hover:text-[var(--color-accent)] transition-colors">
                      <div className="font-mono font-semibold text-[var(--color-text-primary)]">{h.ticker}</div>
                      <div className="text-[var(--color-text-muted)] text-[11px] truncate max-w-28">{h.name}</div>
                    </Link>
                  </td>
                  <td className="px-4 py-3 tabular font-mono text-[var(--color-text-secondary)]">
                    {h.shares}
                  </td>
                  <td className="px-4 py-3 tabular font-mono text-[var(--color-text-primary)]">
                    {formatPrice(h.price)}
                  </td>
                  <td className={cn("px-4 py-3 tabular font-mono", changeClass(h.change_pct))}>
                    {formatPctChange(h.change_pct)}
                  </td>
                  <td className="px-4 py-3 tabular font-mono text-[var(--color-text-primary)]">
                    {formatPrice((h.price ?? 0) * h.shares)}
                  </td>
                  <td className="px-4 py-3">
                    <span className={cn("font-mono font-bold text-xs", scoreColorClass(h.score_total))}>
                      {h.score_total != null ? formatScore(h.score_total) : "—"}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    {h.entry_signal && (
                      <span className={cn("px-2 py-0.5 rounded text-[11px] font-medium", signalClass(h.entry_signal))}>
                        {signalLabel(h.entry_signal)}
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <button
                      onClick={() => remove.mutate(h.id)}
                      className="text-[var(--color-text-muted)] hover:text-[var(--color-down)] transition-colors"
                      aria-label="Ta bort innehav"
                    >
                      <Trash2 size={13} strokeWidth={1.5} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Allocation + Risk — plan §10: "allokering-donut + riskanalys" */}
      {holdings.length > 1 && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <AllocationDonut holdings={holdings} totalValue={totalValue} />
          <RiskPanel holdings={holdings} />
        </div>
      )}

      {/* AI Coach */}
      {holdings.length > 0 && (
        <div className="rounded-xl p-5 border bg-[var(--color-bg-surface)] border-[var(--color-border)]">
          <div className="flex items-center gap-2 mb-4">
            <MessageSquare size={15} strokeWidth={1.5} className="text-[var(--color-accent)]" />
            <h2 className="text-sm font-medium text-[var(--color-text-primary)]">Fråga om din portfölj</h2>
            <InfoTooltip text="Få AI-genererade råd om din portfölj." />
          </div>

          {/* Chat history */}
          {chatHistory.length > 0 && (
            <div className="space-y-3 mb-4 max-h-64 overflow-y-auto">
              {chatHistory.map((m, i) => (
                <div key={i} className={cn(
                  "rounded-lg px-3 py-2 text-xs leading-relaxed",
                  m.role === "user"
                    ? "bg-[var(--color-accent-soft)] text-[var(--color-text-primary)] self-end ml-8"
                    : "bg-[var(--color-bg-elevated)] text-[var(--color-text-secondary)]"
                )}>
                  {m.content}
                </div>
              ))}
            </div>
          )}

          <div className="flex gap-2">
            <input
              value={aiQuestion}
              onChange={(e) => setAiQuestion(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && askAI()}
              placeholder="Fråga om din portfölj... t.ex. 'Är min portfölj för koncentrerad?'"
              className="flex-1 h-9 px-3 rounded-lg text-xs border
                         bg-[var(--color-bg-elevated)] border-[var(--color-border)]
                         text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)]
                         focus:border-[var(--color-accent)] focus:outline-none"
            />
            <button
              onClick={askAI}
              disabled={!!aiLoading || !aiQuestion.trim()}
              className="px-4 h-9 rounded-lg text-xs font-medium transition-colors
                         bg-[var(--color-accent)] text-white hover:bg-[var(--color-accent-hover)]
                         disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {aiLoading || "Fråga"}
            </button>
          </div>

          <div className="flex flex-wrap gap-2 mt-2">
            {[
              "Hur koncentrerad är min portfölj?",
              "Vilka innehav har lägst betyg?",
              "Vad är portföljens beta?",
            ].map((q) => (
              <button
                key={q}
                onClick={() => setAiQuestion(q)}
                className="text-[11px] px-2 py-1 rounded border text-[var(--color-text-muted)]
                           border-[var(--color-border)] hover:border-[var(--color-border-strong)]
                           hover:text-[var(--color-text-secondary)] transition-colors"
              >
                {q}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function EmptyPortfolio() {
  return (
    <div className="rounded-xl p-12 text-center border bg-[var(--color-bg-surface)] border-[var(--color-border)]">
      <Briefcase size={32} strokeWidth={1} className="text-[var(--color-text-muted)] mx-auto mb-3" />
      <p className="text-sm text-[var(--color-text-secondary)]">Ingen portfölj än</p>
      <p className="text-xs mt-1 text-[var(--color-text-muted)]">
        Lägg till innehav från aktiekort-sidan
      </p>
    </div>
  );
}

function PortfoljSkeleton() {
  return (
    <div className="space-y-4">
      <div className="skeleton h-16 rounded-xl" />
      {Array.from({ length: 5 }).map((_, i) => (
        <div key={i} className="skeleton h-12 rounded-xl" />
      ))}
    </div>
  );
}

// Allocation donut (plan §10: "allokering-donut")
const DONUT_COLORS = [
  "#5B8DEF", "#3FB68B", "#D9A441", "#E0645C",
  "#9AA1AC", "#7B6EF6", "#4ABDE8", "#F0A05A",
];

function AllocationDonut({ holdings, totalValue }: {
  holdings: { ticker: string; shares: number; price: number | null }[];
  totalValue: number;
}) {
  const data = holdings
    .filter((h) => h.price && h.price > 0)
    .map((h) => ({
      name: h.ticker,
      value: (h.price ?? 0) * h.shares,
      pct: totalValue > 0 ? ((h.price ?? 0) * h.shares) / totalValue : 0,
    }))
    .sort((a, b) => b.value - a.value);

  return (
    <div className="rounded-xl p-4 border bg-[var(--color-bg-surface)] border-[var(--color-border)]">
      <div className="flex items-center gap-2 mb-4">
        <PieChart size={14} strokeWidth={1.5} className="text-[var(--color-accent)]" />
        <h3 className="text-sm font-medium text-[var(--color-text-secondary)]">Allokering</h3>
      </div>
      <div className="flex items-center gap-4">
        <ResponsiveContainer width={120} height={120}>
          <RechartsPie>
            <Pie
              data={data}
              cx="50%" cy="50%"
              innerRadius={36} outerRadius={54}
              dataKey="value"
              strokeWidth={0}
            >
              {data.map((_, i) => (
                <Cell key={i} fill={DONUT_COLORS[i % DONUT_COLORS.length]} />
              ))}
            </Pie>
            <Tooltip
              contentStyle={{
                background: "var(--color-bg-surface)",
                border: "1px solid var(--color-border-strong)",
                borderRadius: 8,
                fontSize: 11,
                color: "var(--color-text-primary)",
              }}
              formatter={(v: number) => [formatPrice(v), "Värde"]}
            />
          </RechartsPie>
        </ResponsiveContainer>
        <div className="flex-1 space-y-1.5 min-w-0">
          {data.slice(0, 6).map((d, i) => (
            <div key={d.name} className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full shrink-0"
                   style={{ background: DONUT_COLORS[i % DONUT_COLORS.length] }} />
              <span className="font-mono text-xs text-[var(--color-text-secondary)] truncate">{d.name}</span>
              <span className="font-mono text-xs tabular ml-auto text-[var(--color-text-primary)]">
                {(d.pct * 100).toFixed(0)}%
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// Risk panel (P3-5: portfolio risk endpoint — sector allocation, concentration, avg score)
const SECTOR_COLORS = [
  "#5B8DEF", "#3FB68B", "#D9A441", "#E0645C",
  "#9AA1AC", "#7B6EF6", "#4ABDE8", "#F0A05A",
  "#E882D9", "#6BB59B", "#C98B6B", "#A0A4B8",
];

function RiskPanel({ holdings }: {
  holdings: { ticker: string; name: string | null }[];
}) {
  const { data: risk, isLoading } = usePortfolioRisk();

  if (isLoading) return <RiskPanelSkeleton />;
  if (!risk || risk.count === 0) {
    return (
      <div className="rounded-xl p-4 border bg-[var(--color-bg-surface)] border-[var(--color-border)]">
        <div className="flex items-center gap-2 mb-4">
          <ShieldAlert size={14} strokeWidth={1.5} className="text-[var(--color-warn)]" />
          <h3 className="text-sm font-medium text-[var(--color-text-secondary)]">Risk & Allokering</h3>
        </div>
        <p className="text-xs text-[var(--color-text-muted)]">
          Ingen riskdata tillgänglig. Lägg till innehav med scan_resultat för att se sektorallokering.
        </p>
      </div>
    );
  }

  const topSectors = risk.sector_allocation.slice(0, 6);

  return (
    <div className="rounded-xl p-4 border bg-[var(--color-bg-surface)] border-[var(--color-border)]">
      <div className="flex items-center gap-2 mb-4">
        <ShieldAlert size={14} strokeWidth={1.5} className="text-[var(--color-warn)]" />
        <h3 className="text-sm font-medium text-[var(--color-text-secondary)]">Risk & Allokering</h3>
      </div>

      {/* Metric cards row */}
      <div className="grid grid-cols-2 gap-2 mb-4">
        <MetricCard
          label="Totalvärde"
          value={formatPrice(risk.total_value)}
          tooltip="Marknadsvärde baserat på senast kända kurs"
        />
        <MetricCard
          label="Antal innehav"
          value={risk.count}
          tooltip="Totalt antal aktier i portföljen"
        />
        <MetricCard
          label="Snittbetyg"
          value={risk.score_avg != null ? risk.score_avg.toFixed(1) : "—"}
          variant={risk.score_avg != null ? (risk.score_avg >= 60 ? "positive" : risk.score_avg >= 40 ? "neutral" : "negative") : "default"}
          tooltip="Genomsnittligt Marketscan-betyg (0–100)"
        />
        <MetricCard
          label="Sektorkoncentration"
          value={`${risk.concentration_pct}%`}
          variant={risk.concentration_pct > 50 ? "negative" : risk.concentration_pct > 30 ? "neutral" : "positive"}
          tooltip="Andel av portföljvärdet i den största sektorn"
        />
      </div>

      {/* Sector allocation bars */}
      {topSectors.length > 0 && (
        <div className="space-y-2">
          <div className="flex items-center gap-1.5 mb-2">
            <Building2 size={13} strokeWidth={1.5} className="text-[var(--color-text-muted)]" />
            <span className="text-xs font-medium text-[var(--color-text-secondary)]">Sektorallokering</span>
            <InfoTooltip text="Hur portföljen är fördelad över olika sektorer." />
          </div>
          {topSectors.map((s, i) => (
            <div key={s.sector} className="space-y-0.5">
              <div className="flex justify-between text-xs">
                <span className="text-[var(--color-text-secondary)] truncate mr-2">{s.sector}</span>
                <span className="font-mono tabular text-[var(--color-text-muted)] shrink-0">
                  {s.pct}% · {formatPrice(s.value)}
                </span>
              </div>
              <div className="h-2 rounded-full bg-[var(--color-bg-elevated)] overflow-hidden">
                <div
                  className="h-full rounded-full transition-all duration-500"
                  style={{
                    width: `${s.pct}%`,
                    background: SECTOR_COLORS[i % SECTOR_COLORS.length],
                  }}
                />
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Concentration warning */}
      {risk.concentration_pct > 50 && (
        <div className="mt-3 flex items-start gap-2 rounded-lg border border-[var(--color-down)]/20 bg-[var(--color-down)]/5 p-2.5">
          <Target size={14} strokeWidth={1.5} className="text-[var(--color-down)] shrink-0 mt-0.5" />
          <p className="text-xs text-[var(--color-text-muted)]">
            Hög koncentration: <strong>{risk.concentration_pct}%</strong> i en sektor. Överväg att diversifiera för att minska risken.
          </p>
        </div>
      )}
    </div>
  );
}

function RiskPanelSkeleton() {
  return (
    <div className="rounded-xl p-4 border bg-[var(--color-bg-surface)] border-[var(--color-border)]">
      <div className="flex items-center gap-2 mb-4">
        <div className="skeleton h-4 w-4 rounded" />
        <div className="skeleton h-4 w-28 rounded" />
      </div>
      <div className="grid grid-cols-2 gap-2 mb-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="skeleton h-16 rounded-xl" />
        ))}
      </div>
      <div className="space-y-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="space-y-1">
            <div className="skeleton h-3 w-full rounded" />
            <div className="skeleton h-2 w-full rounded" />
          </div>
        ))}
      </div>
    </div>
  );
}
