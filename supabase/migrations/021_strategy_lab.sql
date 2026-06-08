-- MarketScan — Migration 021: Strategy Lab & Signal Analytics
-- Enables saving, running and comparing investment strategies as backtests.
-- Requires score_history (migration 020) for meaningful historical simulation.

-- ─── Strategies ──────────────────────────────────────────────────────────────
-- User-created screener strategies that can be backtested.
CREATE TABLE IF NOT EXISTS strategies (
  id              UUID    PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         UUID    NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  name            TEXT    NOT NULL,
  description     TEXT,

  -- Screener filter (same format as /api/scan query params, stored as JSONB)
  filter_json     JSONB   NOT NULL DEFAULT '{}',

  -- Backtest configuration
  max_positions   INT     NOT NULL DEFAULT 10,    -- max stocks held at once
  position_sizing TEXT    NOT NULL DEFAULT 'equal'
                  CHECK (position_sizing IN ('equal', 'score_weighted', 'kelly')),
  rebalance_freq  TEXT    NOT NULL DEFAULT 'monthly'
                  CHECK (rebalance_freq IN ('daily', 'weekly', 'monthly', 'quarterly')),
  initial_capital NUMERIC(14,2) NOT NULL DEFAULT 100000,
  commission_pct  NUMERIC(6,4) NOT NULL DEFAULT 0.05,  -- 0.05% per trade

  is_public       BOOLEAN NOT NULL DEFAULT false,
  created_at      TIMESTAMPTZ DEFAULT NOW(),
  updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_strategies_user
  ON strategies (user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_strategies_public
  ON strategies (is_public, created_at DESC) WHERE is_public = true;

ALTER TABLE strategies ENABLE ROW LEVEL SECURITY;

CREATE POLICY "strategies_own_or_public" ON strategies
  FOR SELECT
  USING (
    (select auth.uid()) = user_id
    OR is_public = true
  );

CREATE POLICY "strategies_own_write" ON strategies
  FOR ALL
  USING     ((select auth.uid()) = user_id)
  WITH CHECK((select auth.uid()) = user_id);


-- ─── Strategy Runs ────────────────────────────────────────────────────────────
-- Each execution of a strategy's backtest.
CREATE TABLE IF NOT EXISTS strategy_runs (
  id              UUID    PRIMARY KEY DEFAULT gen_random_uuid(),
  strategy_id     UUID    NOT NULL REFERENCES strategies(id) ON DELETE CASCADE,
  user_id         UUID    NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

  -- Date range of simulation
  start_date      DATE    NOT NULL,
  end_date        DATE    NOT NULL,

  -- Summary metrics
  total_return_pct  NUMERIC(10,4),
  cagr_pct          NUMERIC(8,4),
  sharpe_ratio      NUMERIC(8,4),
  sortino_ratio     NUMERIC(8,4),
  max_drawdown_pct  NUMERIC(8,4),
  calmar_ratio      NUMERIC(8,4),
  volatility_ann    NUMERIC(8,4),
  win_rate_pct      NUMERIC(6,2),
  total_trades      INT,
  avg_hold_days     NUMERIC(8,2),
  profit_factor     NUMERIC(8,4),

  -- Final portfolio value
  final_capital     NUMERIC(14,2),

  -- Status
  status        TEXT NOT NULL DEFAULT 'pending'
                CHECK (status IN ('pending', 'running', 'completed', 'failed')),
  error_msg     TEXT,

  started_at    TIMESTAMPTZ DEFAULT NOW(),
  completed_at  TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_strategy_runs_strategy
  ON strategy_runs (strategy_id, started_at DESC);

CREATE INDEX IF NOT EXISTS idx_strategy_runs_user
  ON strategy_runs (user_id, started_at DESC);

ALTER TABLE strategy_runs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "strategy_runs_own" ON strategy_runs
  FOR ALL
  USING     ((select auth.uid()) = user_id)
  WITH CHECK((select auth.uid()) = user_id);


-- ─── Strategy Daily Equity ───────────────────────────────────────────────────
-- Daily portfolio value during a strategy run (for equity curve chart).
CREATE TABLE IF NOT EXISTS strategy_daily_equity (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id       UUID NOT NULL REFERENCES strategy_runs(id) ON DELETE CASCADE,
  date         DATE NOT NULL,
  portfolio_value NUMERIC(14,2) NOT NULL,
  num_positions   INT,
  daily_return_pct NUMERIC(8,4),

  UNIQUE (run_id, date)
);

CREATE INDEX IF NOT EXISTS idx_strategy_daily_equity_run
  ON strategy_daily_equity (run_id, date ASC);

ALTER TABLE strategy_daily_equity ENABLE ROW LEVEL SECURITY;

-- Access via join to strategy_runs (user_id check)
CREATE POLICY "strategy_equity_own" ON strategy_daily_equity
  FOR SELECT
  USING (
    run_id IN (
      SELECT id FROM strategy_runs WHERE user_id = (select auth.uid())
    )
  );

CREATE POLICY "strategy_equity_own_write" ON strategy_daily_equity
  FOR ALL
  USING (
    run_id IN (
      SELECT id FROM strategy_runs WHERE user_id = (select auth.uid())
    )
  )
  WITH CHECK (
    run_id IN (
      SELECT id FROM strategy_runs WHERE user_id = (select auth.uid())
    )
  );


-- ─── Signal Persistence Cache ────────────────────────────────────────────────
-- Pre-aggregated signal analytics: how long signals last, avg forward returns.
-- Populated by backend_worker/signal_analytics.py (weekly).
CREATE TABLE IF NOT EXISTS signal_persistence_cache (
  id              UUID    PRIMARY KEY DEFAULT gen_random_uuid(),
  computed_at     TIMESTAMPTZ DEFAULT NOW(),

  -- Signal transition context
  field           TEXT    NOT NULL CHECK (field IN ('entry_signal', 'trend_signal')),
  from_signal     TEXT    NOT NULL,
  to_signal       TEXT    NOT NULL,

  -- Sample statistics
  sample_count    INT     NOT NULL DEFAULT 0,

  -- How long does the NEW signal typically last before changing again?
  median_hold_days  NUMERIC(8,2),
  avg_hold_days     NUMERIC(8,2),
  pct75_hold_days   NUMERIC(8,2),   -- 75th percentile hold duration

  -- Forward return after transition (price change from transition date)
  avg_return_5d   NUMERIC(8,4),
  avg_return_10d  NUMERIC(8,4),
  avg_return_20d  NUMERIC(8,4),
  avg_return_60d  NUMERIC(8,4),
  win_rate_20d    NUMERIC(6,2),    -- % of transitions with positive 20d return

  -- Breakdown by sector (JSON: {sector: avg_return_20d})
  sector_breakdown JSONB,

  UNIQUE (field, from_signal, to_signal)
);

-- Public read — aggregate analytics, no user data
ALTER TABLE signal_persistence_cache ENABLE ROW LEVEL SECURITY;

CREATE POLICY "signal_persistence_public_read" ON signal_persistence_cache
  FOR SELECT USING (true);
