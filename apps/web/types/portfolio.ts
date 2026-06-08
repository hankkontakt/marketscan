export interface Holding {
  id: string;
  portfolio_id: string;
  ticker: string;
  shares: number;
  cost_basis: number | null;
  added_at: string;
  name: string | null;
  price: number | null;
  change_pct: number | null;
  score_total: number | null;
  entry_signal: string | null;
  trend_signal: string | null;
}

export interface Portfolio {
  id: string;
  user_id: string;
  name: string;
  created_at: string;
  holdings: Holding[];
}

export interface WatchlistItem {
  id: string;
  ticker: string;
  added_at: string;
  name: string | null;
  price: number | null;
  change_pct: number | null;
  score_total: number | null;
  entry_signal: string | null;
  trend_signal: string | null;
}

export interface PriceAlert {
  id: string;
  ticker: string;
  condition: string;
  target_price: number;
  note: string | null;
  active: boolean;
  triggered_at: string | null;
  created_at: string;
}

export interface PeriodReturn {
  pct: number | null;
  positive: boolean | null;
}

export interface PortfolioHistory {
  periods: Record<string, PeriodReturn>;
}

export interface SectorAllocation {
  sector: string;
  value: number;
  pct: number;
}

export interface PortfolioRisk {
  tickers: string[];
  sector_allocation: SectorAllocation[];
  concentration_pct: number;
  total_value: number;
  count: number;
  score_avg: number | null;
}

export interface Transaction {
  id: string;
  ticker: string;
  type: "buy" | "sell" | "deposit" | "withdrawal";
  shares: number | null;
  price: number | null;
  amount: number | null;
  traded_at: string;
  note: string | null;
  created_at: string;
}

export interface TWResponse {
  twr: number | null;
  total_return_pct: number | null;
  periods: Record<string, number | null>;
}

// ─── Risk Analytics (Mega-project 1) ──────────────────────────────────────────

export interface RiskMetrics {
  sharpe_ratio: number | null;
  sortino_ratio: number | null;
  calmar_ratio: number | null;
  total_return_pct: number | null;
  cagr_pct: number | null;
  volatility_ann: number | null;
  max_drawdown_pct: number | null;
  var_95_pct: number | null;
  cvar_95_pct: number | null;
  beta_market: number | null;
  num_holdings: number | null;
  top_holding_pct: number | null;
  sector_hhi: number | null;
  computed_at: string | null;
  is_cached: boolean;
}

export interface FactorExposure {
  factor_value: number | null;
  factor_momentum: number | null;
  factor_quality: number | null;
  factor_growth: number | null;
  factor_dividend: number | null;
  factor_risk: number | null;
  bench_value: number | null;
  bench_momentum: number | null;
  bench_quality: number | null;
  bench_growth: number | null;
  bench_dividend: number | null;
  bench_risk: number | null;
  computed_at: string | null;
}

export interface CorrelationMatrix {
  tickers: string[];
  matrix: number[][];
}

export interface OptimizeResult {
  method: "hrp" | "minvar" | "equal";
  weights: Record<string, number>;
  expected_return_pct: number | null;
  expected_vol_pct: number | null;
}

export interface HoldingDrift {
  ticker: string;
  name: string | null;
  current_pct: number;
  target_pct: number | null;
  drift_pct: number;
  action: "buy" | "sell" | "hold";
  amount_sek: number | null;
}

export interface RebalanceResult {
  total_value: number;
  drifted: boolean;
  holdings: HoldingDrift[];
  target_name: string | null;
}

export interface RebalancingTarget {
  id: string;
  name: string;
  method: "ticker" | "sector";
  targets: Array<{ ticker?: string; sector?: string; target_pct: number }>;
  updated_at: string;
}
