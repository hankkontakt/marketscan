-- MarketScan — Migration 019: Portfolio Risk Analytics
-- Enables deep risk metrics, portfolio optimization, and rebalancing suggestions.

-- ─── Portfolio Risk Cache ─────────────────────────────────────────────────────
-- Stores nightly-computed risk metrics per user portfolio.
-- Populated by backend_worker/risk_analyzer.py (GitHub Actions cron).
CREATE TABLE IF NOT EXISTS portfolio_risk_cache (
  id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  computed_at     TIMESTAMPTZ DEFAULT NOW(),

  -- Return metrics
  sharpe_ratio    NUMERIC(8,4),
  sortino_ratio   NUMERIC(8,4),
  calmar_ratio    NUMERIC(8,4),
  total_return_pct NUMERIC(10,4),
  cagr_pct        NUMERIC(8,4),

  -- Risk metrics
  volatility_ann  NUMERIC(8,4),   -- annualised portfolio volatility
  max_drawdown_pct NUMERIC(8,4),  -- max peak-to-trough
  var_95_pct      NUMERIC(8,4),   -- 1-day 95% VaR (historical simulation)
  cvar_95_pct     NUMERIC(8,4),   -- conditional VaR (expected shortfall)
  beta_market     NUMERIC(8,4),   -- beta vs OMXS30/SPY

  -- Composition metrics
  num_holdings    INT,
  top_holding_pct NUMERIC(6,2),   -- largest single position weight
  sector_hhi      NUMERIC(8,4),   -- Herfindahl-Hirschman Index (0=perfect, 1=mono)

  -- Optimal weights (JSON: {ticker: weight})
  hrp_weights     JSONB,
  minvar_weights  JSONB,

  -- Correlation matrix (JSON: [[row...], ...])
  correlation_matrix JSONB,
  tickers_ordered    TEXT[],       -- order of tickers in correlation_matrix

  UNIQUE (user_id)
);

CREATE INDEX IF NOT EXISTS idx_risk_cache_user
  ON portfolio_risk_cache (user_id, computed_at DESC);

ALTER TABLE portfolio_risk_cache ENABLE ROW LEVEL SECURITY;

CREATE POLICY "risk_cache_own" ON portfolio_risk_cache
  FOR ALL
  USING     ((select auth.uid()) = user_id)
  WITH CHECK((select auth.uid()) = user_id);


-- ─── Portfolio Factor Exposure ────────────────────────────────────────────────
-- Factor scores aggregated from holdings' scan_results columns.
-- Updated alongside risk_cache by risk_analyzer.py.
CREATE TABLE IF NOT EXISTS portfolio_factor_exposure (
  id          UUID    PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     UUID    NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  computed_at TIMESTAMPTZ DEFAULT NOW(),

  -- Factor scores (0-100, portfolio weighted average)
  factor_value      NUMERIC(6,2),
  factor_momentum   NUMERIC(6,2),
  factor_quality    NUMERIC(6,2),
  factor_growth     NUMERIC(6,2),
  factor_dividend   NUMERIC(6,2),
  factor_risk       NUMERIC(6,2),   -- low = defensive (inverted)

  -- Benchmark comparison (scan_results universe average)
  bench_value      NUMERIC(6,2),
  bench_momentum   NUMERIC(6,2),
  bench_quality    NUMERIC(6,2),
  bench_growth     NUMERIC(6,2),
  bench_dividend   NUMERIC(6,2),
  bench_risk       NUMERIC(6,2),

  UNIQUE (user_id)
);

ALTER TABLE portfolio_factor_exposure ENABLE ROW LEVEL SECURITY;

CREATE POLICY "factor_exposure_own" ON portfolio_factor_exposure
  FOR ALL
  USING     ((select auth.uid()) = user_id)
  WITH CHECK((select auth.uid()) = user_id);


-- ─── Rebalancing Targets ─────────────────────────────────────────────────────
-- User-defined target allocations. Used by /api/portfolio/rebalance.
CREATE TABLE IF NOT EXISTS rebalancing_targets (
  id          UUID    PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     UUID    NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  name        TEXT    NOT NULL DEFAULT 'Mitt mål',
  -- JSON: [{ticker: "VOLV B", target_pct: 10.0}, ...]
  -- OR: [{sector: "Technology", target_pct: 25.0}]
  targets     JSONB   NOT NULL DEFAULT '[]',
  method      TEXT    NOT NULL DEFAULT 'ticker'  -- 'ticker' | 'sector'
               CHECK (method IN ('ticker', 'sector')),
  created_at  TIMESTAMPTZ DEFAULT NOW(),
  updated_at  TIMESTAMPTZ DEFAULT NOW(),

  UNIQUE (user_id, name)
);

ALTER TABLE rebalancing_targets ENABLE ROW LEVEL SECURITY;

CREATE POLICY "rebalancing_targets_own" ON rebalancing_targets
  FOR ALL
  USING     ((select auth.uid()) = user_id)
  WITH CHECK((select auth.uid()) = user_id);
