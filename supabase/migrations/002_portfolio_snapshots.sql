-- MarketScan 2.0 — Portfolio snapshots for period return calculation
-- Migration: 002_portfolio_snapshots
-- Run: supabase db push

-- ============================================================
-- PORTFOLIO SNAPSHOTS (RLS enforced)
-- ============================================================

CREATE TABLE IF NOT EXISTS portfolio_snapshots (
  id          UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     UUID          NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  date        DATE          NOT NULL,
  total_value NUMERIC(14,2) NOT NULL,
  total_cost  NUMERIC(14,2),
  created_at  TIMESTAMPTZ   DEFAULT NOW(),
  UNIQUE (user_id, date)
);

CREATE INDEX IF NOT EXISTS idx_portfolio_snapshots_user_date
  ON portfolio_snapshots (user_id, date DESC);

-- ============================================================
-- ROW LEVEL SECURITY
-- ============================================================

ALTER TABLE portfolio_snapshots ENABLE ROW LEVEL SECURITY;

-- Users can read their own snapshots
CREATE POLICY "portfolio_snapshots_own_select"
  ON portfolio_snapshots
  FOR SELECT
  USING (auth.uid() = user_id);

-- The snapshot creation endpoint uses the service role or anon key;
-- we allow insert/update via a policy that checks ownership.
CREATE POLICY "portfolio_snapshots_own_insert"
  ON portfolio_snapshots
  FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "portfolio_snapshots_own_update"
  ON portfolio_snapshots
  FOR UPDATE
  USING (auth.uid() = user_id);
