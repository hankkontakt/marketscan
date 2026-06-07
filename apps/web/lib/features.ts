/**
 * Feature flags — controls which nav items/pages are visible.
 * A flag being true means the feature HAS data and should be shown.
 * Used to avoid showing empty/404 pages before pipeline has filled them.
 */

export type FeatureFlag = keyof typeof FEATURE_FLAGS;

export const FEATURE_FLAGS = {
  /** Small-cap scanner data available */
  smallcap: false,
  /** ML predictions available */
  predictions: false,
  /** Options data available */
  options: false,
  /** Backtest results available */
  backtests: false,
  /** Sector rotation data available */
  sectorRotation: false,
  /** Insider trades data available */
  insiderTrades: false,
  /** Transactions + TWR (built, needs real price data) */
  transactions: false,
  /** AI journal timeline */
  aiJournal: false,
  /** Portfolio optimization */
  portfolioOptimization: false,
  /** Paper trading */
  paperTrading: false,
} as const;

export function isFeatureEnabled(flag: FeatureFlag): boolean {
  return FEATURE_FLAGS[flag];
}

/**
 * Nav items that depend on a feature flag being enabled.
 * When flag is null, the item is always shown.
 */
export const FEATURE_GATED_NAV_ITEMS: Record<string, { flag: FeatureFlag | null }> = {
  "/smallcap": { flag: "smallcap" },
  "/options": { flag: "options" },
  "/kontrollpanel": { flag: null }, // always shown if admin
};
