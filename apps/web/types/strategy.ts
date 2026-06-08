// ─── Strategy Lab Types (Mega-project 3) ─────────────────────────────────────

export type PositionSizing = "equal" | "score_weighted" | "kelly";
export type RebalanceFreq = "daily" | "weekly" | "monthly" | "quarterly";
export type RunStatus = "pending" | "running" | "completed" | "failed";

export interface StrategyFilter {
  segments?: string[];
  score_min?: number;
  score_max?: number;
  sector?: string;
  entry_signal?: string;
  trend_signal?: string;
  piotroski_min?: number;
  conditions?: Array<{ field: string; op: string; value: number | string }>;
}

export interface Strategy {
  id: string;
  user_id: string;
  name: string;
  description: string | null;
  filter_json: StrategyFilter;
  max_positions: number;
  position_sizing: PositionSizing;
  rebalance_freq: RebalanceFreq;
  initial_capital: number;
  commission_pct: number;
  is_public: boolean;
  created_at: string;
  updated_at: string;
  _is_own?: boolean;
  strategy_runs?: StrategyRun[];
}

export interface StrategyRun {
  id: string;
  strategy_id: string;
  user_id: string;
  status: RunStatus;
  start_date: string | null;
  end_date: string | null;
  completed_at: string | null;
  created_at: string;
  // Metrics
  total_return_pct: number | null;
  cagr_pct: number | null;
  sharpe_ratio: number | null;
  sortino_ratio: number | null;
  max_drawdown_pct: number | null;
  calmar_ratio: number | null;
  volatility_ann: number | null;
  win_rate_pct: number | null;
  total_trades: number | null;
  avg_hold_days: number | null;
  profit_factor: number | null;
  final_capital: number | null;
  error_message?: string | null;
}

export interface EquityPoint {
  date: string;
  portfolio_value: number;
  daily_return_pct: number | null;
  num_positions: number | null;
  normalized?: number | null; // 100 = start, used for comparison
}

export interface BacktestResult {
  run: StrategyRun;
  equity_curve: EquityPoint[];
}

export interface CompareResult {
  run_id: string;
  strategy_name: string;
  metrics: {
    total_return_pct: number | null;
    cagr_pct: number | null;
    sharpe_ratio: number | null;
    sortino_ratio: number | null;
    max_drawdown_pct: number | null;
    calmar_ratio: number | null;
    volatility: number | null;
    win_rate_pct: number | null;
    total_trades: number | null;
    avg_hold_days: number | null;
    profit_factor: number | null;
  };
  equity_curve: EquityPoint[];
}

// ─── Signal Analytics ─────────────────────────────────────────────────────────

export interface SignalAnalytics {
  id: string;
  field: "entry_signal" | "trend_signal";
  from_signal: string;
  to_signal: string;
  sample_count: number;
  median_hold_days: number | null;
  avg_hold_days: number | null;
  pct75_hold_days: number | null;
  avg_return_5d: number | null;
  avg_return_10d: number | null;
  avg_return_20d: number | null;
  avg_return_60d: number | null;
  win_rate_20d: number | null;
  sector_breakdown: Record<string, number> | null;
  computed_at: string;
  label: string; // "VÄNTA → STARK"
}

export interface SignalAnalyticsDetail {
  stats: SignalAnalytics | null;
  examples: Array<{
    ticker: string;
    name: string | null;
    transition_date: string;
    price_at: number | null;
    score_total_at: number | null;
    current_score: number | null;
    current_signal: string | null;
  }>;
  label: string;
  field: string;
}
