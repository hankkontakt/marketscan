// GENERATED FILE — do not edit by hand.
// Source of truth: apps/api/schemas/decision_v3.py (OpenAPI).
// Regenerate: python scripts/generate_v3_types.py  (--check in CI/tests).


export interface DecisionProjectionV3 {
  decision_id: string;
  decision_snapshot_id: string;
  listing_id: string;
  ticker: string;
  mic: string;
  currency: string;
  tradability_state: string;
  decision_time: string;
  master_rank_score?: number | null;
  thesis_band: string;
  segment_percentile?: number | null;
  setup_vector?: Record<string, unknown>;
  setup_state: string;
  risk_vector?: Record<string, unknown>;
  risk_state: string;
  is_actionable: boolean;
  data_grade: string;
  coverage: number;
  stale_critical_count: number;
  street_context?: Record<string, unknown>;
  positive_drivers?: Record<string, unknown>[];
  negative_drivers?: Record<string, unknown>[];
  warnings?: string[];
  model_versions?: Record<string, string>;
  published_at: string;
  name?: string | null;
  segment?: string | null;
  price?: number | null;
  change_pct?: number | null;
  fx_rate_sek?: number | null;
  fx_rate_date?: string | null;
  fx_source?: string | null;
}

export interface ScreenerProjectionV3 {
  snapshot_id: string;
  as_of: string;
  total_count: number;
  rows: DecisionProjectionV3[];
}

export interface CurrentSnapshotV3 {
  current_snapshot_id?: string | null;
  published_at?: string | null;
  master_model_version?: string | null;
  code_sha?: string | null;
  manifest_count: number;
  actionable_count: number;
  excluded_count: number;
  quality_report?: Record<string, unknown>;
}

export interface ChangeEventV3 {
  id: number;
  snapshot_from?: string | null;
  snapshot_to: string;
  listing_id: string;
  ticker: string;
  decision_id?: string | null;
  transition_type: string;
  from_state?: string | null;
  to_state: string;
  reason_code: string;
  rank_delta?: number | null;
  created_at: string;
}

export interface ChangesProjectionV3 {
  snapshot_id?: string | null;
  as_of?: string | null;
  master_model_version?: string | null;
  total_count: number;
  rows: ChangeEventV3[];
}

export interface CompareRequestV3 {
  tickers: string[];
}

export interface CompareProjectionV3 {
  snapshot_id: string;
  as_of: string;
  total_count: number;
  rows: DecisionProjectionV3[];
}

export interface TransitionEventV3 {
  listing_id: string;
  ticker: string;
  decision_id?: string | null;
  transition_type: string;
  from_state?: string | null;
  to_state: string;
  reason_code: string;
  rank_delta?: number | null;
  snapshot_to: string;
  created_at: string;
}

export type V3DecisionTypes = DecisionProjectionV3 | ScreenerProjectionV3 | CurrentSnapshotV3 | ChangeEventV3 | ChangesProjectionV3 | CompareRequestV3 | CompareProjectionV3 | TransitionEventV3;
