"use client";

import React from "react";
import { api } from "@/lib/api";
import { AlertTriangle, RefreshCw } from "lucide-react";

interface Props {
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

/**
 * Catches render errors and reports them to /api/debug/client-error.
 * Falls back to a calming error UI instead of crashing the whole app.
 */
export class ErrorBoundary extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    // Report to backend (fire-and-forget)
    api("/api/debug/client-error", {
      method: "POST",
      body: JSON.stringify({
        message: error.message,
        stack: error.stack,
        url: typeof window !== "undefined" ? window.location.href : undefined,
      }),
    }).catch(() => {});
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback;

      return (
        <div className="flex flex-col items-center justify-center py-24 gap-4">
          <AlertTriangle size={36} strokeWidth={1.5} className="text-[var(--color-warn)]" />
          <p className="text-base font-medium text-[var(--color-text-secondary)]">Något gick fel</p>
          <p className="text-sm text-[var(--color-text-muted)] text-center max-w-sm">
            {this.state.error?.message || "Ett oväntat fel inträffade."}
          </p>
          <button
            onClick={() => this.setState({ hasError: false, error: null })}
            className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm bg-[var(--color-accent)] text-white hover:opacity-90 transition-opacity"
          >
            <RefreshCw size={14} strokeWidth={1.5} />
            Försök igen
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}

/**
 * Install global error handlers (window.onerror, onunhandledrejection).
 * Call once at app root.
 */
export function installGlobalErrorCapture() {
  if (typeof window === "undefined") return;

  window.onerror = (_msg, _url, _line, _col, error) => {
    api("/api/debug/client-error", {
      method: "POST",
      body: JSON.stringify({
        message: error?.message || String(_msg),
        stack: error?.stack,
        url: window.location.href,
      }),
    }).catch(() => {});
    return false;
  };

  window.onunhandledrejection = (event) => {
    const error = event.reason instanceof Error ? event.reason : new Error(String(event.reason));
    api("/api/debug/client-error", {
      method: "POST",
      body: JSON.stringify({
        message: error.message,
        stack: error.stack,
        url: window.location.href,
      }),
    }).catch(() => {});
  };
}
