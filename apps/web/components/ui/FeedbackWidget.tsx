"use client";

import { useState } from "react";
import { ThumbsUp, ThumbsDown, X } from "lucide-react";
import { useMutation } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { trackEvent, EVENT } from "@/lib/tracking";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

export function FeedbackWidget({
  component,
  context,
  className,
}: {
  component: string;
  context?: string;
  className?: string;
}) {
  const [rating, setRating] = useState<1 | 0 | -1 | null>(null);
  const [showComment, setShowComment] = useState(false);
  const [comment, setComment] = useState("");

  const mutation = useMutation({
    mutationFn: (body: { component: string; context?: string; rating: number; comment?: string }) =>
      api("/api/feedback", { method: "POST", body: JSON.stringify(body) }),
    onSuccess: () => {
      trackEvent(EVENT.FEEDBACK_SUBMITTED, { component, rating: rating ?? 0 });
      toast.success("Tack!");
    },
    onError: () => {},
  });

  function handleRate(r: 1 | -1) {
    setRating(r);
    setShowComment(true);
    mutation.mutate({ component, context, rating: r, comment: "" });
  }

  function submitComment() {
    const c = comment.trim();
    mutation.mutate({ component, context, rating: rating ?? 0, comment: c || undefined });
    setShowComment(false);
    setComment("");
  }

  return (
    <div className={cn("inline-flex items-center gap-1", className)}>
      <span className="text-[10px] text-[var(--color-text-muted)] select-none">
        {rating === null ? "Hjälpsamt?" : rating === 1 ? "Tack!" : "Noterat"}
      </span>
      <button
        onClick={() => handleRate(1)}
        className={cn(
          "p-1 rounded-md transition-colors",
          rating === 1 ? "text-[var(--color-up)] bg-[var(--color-up-soft)]" : "text-[var(--color-text-muted)] hover:text-[var(--color-up)]",
        )}
      >
        <ThumbsUp size={14} strokeWidth={1.5} />
      </button>
      <button
        onClick={() => handleRate(-1)}
        className={cn(
          "p-1 rounded-md transition-colors",
          rating === -1 ? "text-[var(--color-down)] bg-[var(--color-down-soft)]" : "text-[var(--color-text-muted)] hover:text-[var(--color-down)]",
        )}
      >
        <ThumbsDown size={14} strokeWidth={1.5} />
      </button>
      {showComment && (
        <span className="flex items-center gap-1 ml-1">
          <input
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && submitComment()}
            placeholder="Kort kommentar..."
            className="w-36 text-[11px] px-2 py-1 rounded border border-[var(--color-border)]
                       bg-[var(--color-bg-surface)] text-[var(--color-text-primary)]"
            autoFocus
          />
          <button onClick={submitComment}
            className="text-[10px] px-2 py-1 rounded bg-[var(--color-accent)] text-white">
            OK
          </button>
          <button onClick={() => setShowComment(false)}
            className="text-[var(--color-text-muted)]">
            <X size={12} />
          </button>
        </span>
      )}
    </div>
  );
}
