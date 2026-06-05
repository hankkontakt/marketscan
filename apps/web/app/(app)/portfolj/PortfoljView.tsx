"use client";

import { useState } from "react";
import Link from "next/link";
import { Briefcase, Plus, Trash2, MessageSquare, TrendingUp, AlertTriangle } from "lucide-react";
import { usePortfolio, useRemoveHolding } from "@/hooks/usePortfolio";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import {
  formatPrice, formatPctChange, formatScore, signalLabel, signalClass,
  scoreColorClass, changeClass, formatMarketCap,
} from "@/lib/format";
import { cn } from "@/lib/utils";

export function PortfoljView() {
  const { data: portfolio, isLoading } = usePortfolio();
  const remove = useRemoveHolding();
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
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-xl font-semibold text-[var(--color-text-primary)]">Min portfölj</h1>
          {portfolio && (
            <p className="text-xs mt-0.5 text-[var(--color-text-muted)]">
              {holdings.length} innehav
            </p>
          )}
        </div>
        {totalValue > 0 && (
          <div className="text-right">
            <div className="text-2xl font-bold font-mono tabular text-[var(--color-text-primary)]">
              {formatPrice(totalValue)}
            </div>
            {totalReturn != null && (
              <div className={cn("text-sm font-mono tabular", changeClass(totalReturn))}>
                {formatPctChange(totalReturn)} total avkastning
              </div>
            )}
          </div>
        )}
      </div>

      {/* Holdings table */}
      {holdings.length === 0 ? (
        <EmptyPortfolio />
      ) : (
        <div className="rounded-xl overflow-hidden border"
             style={{ borderColor: "var(--color-border)" }}>
          <table className="w-full text-xs border-collapse">
            <thead>
              <tr style={{ background: "var(--color-bg-surface)", borderBottom: "1px solid var(--color-border)" }}>
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
                  style={{
                    background: i % 2 === 0 ? "var(--color-bg-base)" : "var(--color-bg-surface)",
                    borderBottom: "1px solid var(--color-border)",
                  }}
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

      {/* AI Coach */}
      {holdings.length > 0 && (
        <div className="rounded-xl p-5 border"
             style={{ background: "var(--color-bg-surface)", borderColor: "var(--color-border)" }}>
          <div className="flex items-center gap-2 mb-4">
            <MessageSquare size={15} strokeWidth={1.5} style={{ color: "var(--color-accent)" }} />
            <h2 className="text-sm font-medium text-[var(--color-text-primary)]">AI-portföljcoach</h2>
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
    <div className="rounded-xl p-12 text-center border"
         style={{ background: "var(--color-bg-surface)", borderColor: "var(--color-border)" }}>
      <Briefcase size={32} strokeWidth={1} style={{ color: "var(--color-text-muted)", margin: "0 auto 12px" }} />
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
