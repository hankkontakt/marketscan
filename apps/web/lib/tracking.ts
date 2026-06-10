/**
 * Tracking-abstraktion. Just nu Umami self-hosted.
 * Byta provider = byt implementering, behåll interface.
 *
 * Använd ALLTID EVENT-konstanterna, aldrig hårdkodade strängar.
 */
type EventProps = Record<string, string | number | boolean>;

declare global {
  interface Window {
    umami?: { track: (event: string, data?: EventProps) => void };
  }
}

export function trackEvent(name: string, props?: EventProps): void {
  if (typeof window !== "undefined" && window.umami) {
    window.umami.track(name, props);
  }
}

export function trackPageView(url?: string): void {
  if (typeof window !== "undefined" && window.umami) {
    window.umami.track("pageview", {
      url: url || window.location.pathname,
    });
  }
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
