"use client";

import { useState, useRef, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { HelpCircle, X } from "lucide-react";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

interface MicroLessonResponse {
  topic: string;
  question: string;
  explanation: string;
  cached_date: string;
}

interface Props {
  topic: string;
  label?: string;
}

export function MicroLesson({ topic, label }: Props) {
  const [open, setOpen] = useState(false);
  const popupRef = useRef<HTMLDivElement>(null);

  const { data } = useQuery<MicroLessonResponse>({
    queryKey: ["micro-lesson", topic],
    queryFn: () =>
      api<MicroLessonResponse>("/api/ai/micro-lesson", {
        method: "POST",
        body: JSON.stringify({ topic }),
      }),
    staleTime: 24 * 60 * 60 * 1000, // 24 hours
    enabled: open,
  });

  // Close on click outside
  useEffect(() => {
    if (!open) return;
    const handleClick = (e: MouseEvent) => {
      if (popupRef.current && !popupRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [open]);

  return (
    <span className="relative inline-flex">
      <button
        onClick={() => setOpen((v) => !v)}
        aria-label={label ?? `Förklara ${topic}`}
        className={cn(
          "inline-flex items-center justify-center align-middle shrink-0",
          "w-3.5 h-3.5 rounded-full",
          "text-[9px] font-bold leading-none",
          "cursor-help select-none transition-colors",
          open
            ? "text-[var(--color-accent)] border-[var(--color-accent)]"
            : "text-[var(--color-text-muted)] border-[var(--color-border-strong)]",
          "border hover:text-[var(--color-accent)] hover:border-[var(--color-accent)]",
        )}
      >
        ?
      </button>

      {open && (
        <div
          ref={popupRef}
          className={cn(
            "absolute z-50 w-72 p-4 rounded-xl shadow-lg",
            "bg-[var(--color-bg-surface)] text-[var(--color-text-primary)]",
          )}
          style={{ border: "1px solid var(--color-border-strong)", top: "calc(100% + 4px)", left: "50%", transform: "translateX(-50%)" }}
        >
          {/* Arrow */}
          <div
            className="absolute w-3 h-3 rotate-45 bg-[var(--color-bg-surface)]"
            style={{ top: -6.5, left: "50%", marginLeft: -6, borderLeft: "1px solid var(--color-border-strong)", borderTop: "1px solid var(--color-border-strong)" }}
          />

          <div className="flex items-start justify-between gap-2 mb-2">
            <h4 className="text-xs font-semibold text-[var(--color-text-primary)]">
              {data?.question ?? "Laddar..."}
            </h4>
            <button
              onClick={() => setOpen(false)}
              className="shrink-0 text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]"
            >
              <X size={12} strokeWidth={1.5} />
            </button>
          </div>

          {data ? (
            <p className="text-xs text-[var(--color-text-secondary)] leading-relaxed">
              {data.explanation}
            </p>
          ) : (
            <div className="space-y-2">
              <div className="skeleton h-3 w-full rounded" />
              <div className="skeleton h-3 w-5/6 rounded" />
              <div className="skeleton h-3 w-4/6 rounded" />
            </div>
          )}

          {data && (
            <button
              onClick={() => setOpen(false)}
              className="mt-3 w-full py-1.5 rounded-lg text-xs font-medium text-white bg-[var(--color-accent)] hover:opacity-90"
            >
              Stäng
            </button>
          )}
        </div>
      )}
    </span>
  );
}
