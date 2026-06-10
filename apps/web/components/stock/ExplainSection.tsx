"use client";

import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { Sparkles, Send } from "lucide-react";
import { api } from "@/lib/api";
import { trackEvent, EVENT } from "@/lib/tracking";
import { cn } from "@/lib/utils";
import { FeedbackWidget } from "@/components/ui/FeedbackWidget";
import type { ScanRow } from "@/types/scan";

interface ExplainResponse {
  ticker: string;
  explanation: string;
  level: string;
  cached_date: string;
}

interface FollowupResponse {
  ticker: string;
  answer: string;
  cached_date: string;
}

interface ChatMessage {
  role: "ai" | "user";
  text: string;
}

export function ExplainSection({
  ticker,
  stock,
}: {
  ticker: string;
  stock: ScanRow;
}) {
  const [showFollowup, setShowFollowup] = useState(false);
  const [followupQuestion, setFollowupQuestion] = useState("");
  const [chat, setChat] = useState<ChatMessage[]>([]);

  const { data, isLoading, error } = useQuery<ExplainResponse>({
    queryKey: ["explain", ticker],
    queryFn: () =>
      api<ExplainResponse>(`/api/ai/explain/${ticker}`, {
        method: "POST",
        body: JSON.stringify({ stock_data: stock }),
      }),
    staleTime: 8 * 60 * 60 * 1000, // 8 hours
  });

  const followupMutation = useMutation<FollowupResponse, Error, string>({
    mutationFn: (question: string) =>
      api<FollowupResponse>(`/api/ai/explain/${ticker}/followup`, {
        method: "POST",
        body: JSON.stringify({
          stock_data: stock,
          previous_explanation: data?.explanation ?? "",
          question,
        }),
      }),
  });

  function handleFollowup() {
    if (!followupQuestion.trim()) return;
    trackEvent(EVENT.EXPLAIN_FOLLOWUP, { ticker });
    setChat((prev) => [...prev, { role: "user", text: followupQuestion }]);
    followupMutation.mutate(followupQuestion, {
      onSuccess: (res) => {
        setChat((prev) => [...prev, { role: "ai", text: res.answer }]);
        setFollowupQuestion("");
      },
    });
  }

  if (isLoading) {
    return (
      <div className="rounded-xl border p-4 bg-[var(--color-bg-surface)] border-[var(--color-border)] space-y-3">
        <div className="flex items-center gap-2">
          <Sparkles size={16} className="text-[var(--color-accent)]" />
          <div className="skeleton h-4 w-32 rounded" />
        </div>
        <div className="skeleton h-20 rounded-lg" />
        <div className="skeleton h-4 w-64 rounded" />
      </div>
    );
  }

  if (error || !data) {
    return null;
  }

  return (
    <div className="rounded-xl border p-4 bg-[var(--color-bg-surface)] border-[var(--color-border)] space-y-3">
      {/* Header */}
      <div className="flex items-center gap-2">
        <Sparkles size={16} className="text-[var(--color-accent)]" />
        <span className="text-sm font-medium text-[var(--color-text-secondary)]">
          AI-förklaring
        </span>
        {data.cached_date && (
          <span className="text-[10px] text-[var(--color-text-muted)] ml-auto">
            {data.cached_date}
          </span>
        )}
      </div>

      {/* Explanation text */}
      <p className="text-sm text-[var(--color-text-primary)] leading-relaxed whitespace-pre-line">
        {data.explanation}
      </p>

      {/* Disclaimer */}
      <p className="text-[10px] text-[var(--color-text-muted)] italic">
        AI-genererad — inte finansiell rådgivning
      </p>

      {/* Feedback */}
      <FeedbackWidget
        component="explain"
        context={`${ticker}`}
      />

      {/* Follow-up chat */}
      {chat.length > 0 && (
        <div className="space-y-2 pt-2 border-t border-[var(--color-border)]">
          {chat.map((msg, i) => (
            <div
              key={i}
              className={cn(
                "text-sm rounded-lg px-3 py-2 max-w-[90%]",
                msg.role === "user"
                  ? "bg-[var(--color-accent-soft)] text-[var(--color-accent)] ml-auto"
                  : "bg-[var(--color-bg-elevated)] text-[var(--color-text-primary)]",
              )}
            >
              {msg.text}
            </div>
          ))}
          {followupMutation.isPending && (
            <div className="skeleton h-12 w-3/4 rounded-lg" />
          )}
        </div>
      )}

      {/* "Fråga mer" button / input */}
      {!showFollowup ? (
        <button
          onClick={() => {
            trackEvent(EVENT.EXPLAIN_CLICK, { ticker });
            setShowFollowup(true);
          }}
          className="flex items-center gap-1.5 text-xs font-medium text-[var(--color-accent)] hover:underline"
        >
          <Sparkles size={12} strokeWidth={1.5} />
          Fråga mer
        </button>
      ) : (
        <div className="flex items-center gap-2">
          <input
            autoFocus
            value={followupQuestion}
            onChange={(e) => setFollowupQuestion(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") handleFollowup();
            }}
            placeholder="Skriv din följdfråga..."
            className="flex-1 h-8 px-3 rounded-lg text-xs border bg-[var(--color-bg-elevated)] border-[var(--color-border)] text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-accent)]"
          />
          <button
            onClick={handleFollowup}
            disabled={!followupQuestion.trim() || followupMutation.isPending}
            className="flex items-center gap-1 h-8 px-3 rounded-lg text-xs font-medium bg-[var(--color-accent)] text-white disabled:opacity-40"
          >
            <Send size={12} strokeWidth={1.5} />
            Skicka
          </button>
        </div>
      )}
    </div>
  );
}
