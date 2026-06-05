"use client";
import { AlertTriangle, RefreshCw } from "lucide-react";

export default function AppError({ error, reset }: { error: Error; reset: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center py-24 gap-4">
      <AlertTriangle size={36} strokeWidth={1.5} className="text-[var(--color-warn)]" />
      <p className="text-base font-medium text-[var(--color-text-secondary)]">Något gick fel</p>
      <p className="text-sm text-[var(--color-text-muted)] text-center max-w-sm">{error.message || "Ett oväntat fel inträffade."}</p>
      <button
        onClick={reset}
        className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm bg-[var(--color-accent)] text-white hover:opacity-90 transition-opacity"
      >
        <RefreshCw size={14} strokeWidth={1.5} />
        Försök igen
      </button>
    </div>
  );
}
