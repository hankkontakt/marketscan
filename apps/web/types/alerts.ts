// ─── Smart Alerts Types (Mega-project 2) ─────────────────────────────────────

export type AlertRuleType =
  | "price_cross"
  | "score_change"
  | "signal_change"
  | "screen_match"
  | "insider_cluster"
  | "volatility_spike";

export interface AlertCondition {
  field: string;
  op: ">=" | "<=" | ">" | "<" | "=" | "!=";
  value: number | string;
}

export interface AlertRule {
  id: string;
  user_id: string;
  name: string;
  rule_type: AlertRuleType;
  ticker: string | null;
  conditions: AlertCondition[];
  score_change_min: number | null;
  insider_min_count: number | null;
  vol_spike_min_pct: number | null;
  trigger_once: boolean;
  active: boolean;
  last_triggered: string | null;
  trigger_count: number;
  created_at: string;
}

export interface TriggeredAlert {
  id: string;
  user_id: string;
  rule_id: string;
  rule_name: string;
  rule_type: AlertRuleType;
  ticker: string | null;
  detail: string | null;
  score_at: number | null;
  price_at: number | null;
  triggered_at: string;
}

// ─── Score History ─────────────────────────────────────────────────────────────

export interface ScoreHistoryPoint {
  scan_date: string;
  score_total: number | null;
  score_value: number | null;
  score_momentum: number | null;
  score_quality: number | null;
  score_growth: number | null;
  score_risk: number | null;
  score_dividend: number | null;
  entry_signal: string | null;
  trend_signal: string | null;
  piotroski_f: number | null;
  price: number | null;
  vol_20d: number | null;
}

export interface ScoreMover {
  ticker: string;
  name: string | null;
  score_total: number | null;
  prev_score: number;
  score_change: number;
  entry_signal: string | null;
  trend_signal: string | null;
  sector: string | null;
}

export interface SignalTransition {
  transition_date: string;
  field: "entry_signal" | "trend_signal";
  from_value: string | null;
  to_value: string | null;
  score_total_at: number | null;
  price_at: number | null;
}
