/**
 * Tracking-abstraktion. Lagrar events i Supabase via API:et.
 * Byta provider = byt implementering, behåll interface.
 *
 * Fallback: loggar till console.log i dev.
 */
type EventProps = Record<string, string | number | boolean>;

const IS_DEV = typeof location !== "undefined" && location.hostname === "localhost";

// Använd samma API_BASE som resten av appen (lib/api.ts-mönster)
// || inte ?? — Vercel injicerar tom sträng, ?? fångar den inte
const API_BASE =
  (typeof process !== "undefined" && process.env?.NEXT_PUBLIC_API_URL) ||
  "https://marketscan-api.vercel.app";

const QUEUE: Array<{ name: string; props?: EventProps }> = [];
let flushing = false;

async function flush() {
  if (flushing || QUEUE.length === 0) return;
  flushing = true;
  const batch = QUEUE.splice(0);
  try {
    await fetch(`${API_BASE}/api/tracking/events`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ events: batch }),
    });
  } catch {
    // Silent — tracking får aldrig krascha appen
  } finally {
    flushing = false;
  }
}

export function trackEvent(name: string, props?: EventProps): void {
  if (IS_DEV) {
    console.log("[tracking]", name, props);
  }
  QUEUE.push({ name, props });
  if (QUEUE.length >= 5) flush();
  // Auto-flush efter 2 sekunder om inget händer
  if (QUEUE.length === 1) setTimeout(flush, 2000);
}

export function trackPageView(url?: string): void {
  trackEvent("pageview", { url: url || (typeof location !== "undefined" ? location.pathname : "") });
}

export const EVENT = {
  ONBOARDING_COMPLETED: "onboarding_completed",
  BEGINNER_TOGGLE: "beginner_toggle",
  STOCK_PAGE_VIEW: "stock_page_view",
  EXPLAIN_CLICK: "explain_click",
  EXPLAIN_FOLLOWUP: "explain_followup",
  FEEDBACK_SUBMITTED: "feedback_submitted",
  THEME_CLICK: "theme_click",
  THEME_STOCK_CLICK: "theme_stock_click",
  WATCHLIST_ADD: "watchlist_add",
  VERDICT_EXPAND: "verdict_expand_numbers",
} as const;
