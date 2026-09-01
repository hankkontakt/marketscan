/**
 * MarketScan Decision API v2 TypeScript Contracts (Phase 6)
 * Single source of truth for Screener, Stock Page, Compare, Watchlist, and Portfolio.
 */

export type ThesisBand =
  | "EXCEPTIONAL"
  | "STRONG"
  | "POSITIVE"
  | "MIXED"
  | "WEAK"
  | "INSUFFICIENT";

export type SetupState =
  | "CONFIRMED"
  | "PULLBACK"
  | "NEUTRAL"
  | "EXTENDED"
  | "DAMAGED"
  | "EVENT_RISK"
  | "INSUFFICIENT";

export type RiskState =
  | "LOW"
  | "MEDIUM"
  | "HIGH"
  | "VERY_HIGH"
  | "EVENT"
  | "INSUFFICIENT";

export type DataGrade = "A" | "B" | "C" | "D" | "E" | "F";

export interface FactorDriver {
  factor_name: string;
  label_sv: string;
  raw_score: number | null;
  reliability: number;
  contribution: number;
}

export interface PriceQuote {
  value: number;
  currency: string;
  change_pct: number;
  as_of: string;
}

export interface MasterRankDetails {
  score: number;
  band: ThesisBand;
  segment_percentile: number;
  weighted_coverage: number;
  model_version: string;
}

export interface SetupDetails {
  state: SetupState;
  ui_label_sv: string;
  reason_codes: string[];
}

export interface RiskDetails {
  state: RiskState;
  dominant_risk: string;
  liquidity_grade: string;
  risk_flags: string[];
}

export interface DataGradeDetails {
  grade: DataGrade;
  weighted_coverage: number;
  critical_warnings: string[];
}

export interface DecisionRowV2 {
  decision_snapshot_id: string;
  listing_id: string;
  ticker: string;
  name: string;
  segment: string;
  sector?: string | null;
  country: string;
  price: PriceQuote;
  master_rank: MasterRankDetails;
  setup: SetupDetails;
  risk: RiskDetails;
  data_grade: DataGradeDetails;
  positive_drivers: FactorDriver[];
  negative_drivers: FactorDriver[];
}

export interface ScreenerResponseV2 {
  total_count: number;
  rows: DecisionRowV2[];
  as_of: string;
  snapshot_id: string;
  active_filters: Record<string, unknown>;
}

export interface StockDecisionV2 extends DecisionRowV2 {
  factor_scores: Record<string, number | null>;
  factor_reliabilities: Record<string, number>;
  warnings: string[];
}
