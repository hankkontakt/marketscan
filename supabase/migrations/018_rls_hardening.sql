-- MarketScan — Migration 018: RLS hardening + client_errors table
-- Rewrites all bare USING(...) policies to FOR ALL ... USING(...) WITH CHECK(...)
-- so INSERT, UPDATE, and DELETE operations are explicitly guarded.
-- Also creates the client_errors table referenced by apps/api/core/request_id.py.

-- ────────────────────────────────────────────────────────────────────────────
-- PROFILES
-- ────────────────────────────────────────────────────────────────────────────
DROP POLICY IF EXISTS "profiles_own" ON profiles;
CREATE POLICY "profiles_own" ON profiles
  FOR ALL
  USING     ((select auth.uid()) = id)
  WITH CHECK((select auth.uid()) = id);

-- ────────────────────────────────────────────────────────────────────────────
-- PORTFOLIOS
-- ────────────────────────────────────────────────────────────────────────────
DROP POLICY IF EXISTS "portfolios_own" ON portfolios;
CREATE POLICY "portfolios_own" ON portfolios
  FOR ALL
  USING     ((select auth.uid()) = user_id)
  WITH CHECK((select auth.uid()) = user_id);

-- ────────────────────────────────────────────────────────────────────────────
-- HOLDINGS  (ownership via portfolio)
-- ────────────────────────────────────────────────────────────────────────────
DROP POLICY IF EXISTS "holdings_own" ON holdings;
CREATE POLICY "holdings_own" ON holdings
  FOR ALL
  USING (
    portfolio_id IN (
      SELECT id FROM portfolios WHERE user_id = (select auth.uid())
    )
  )
  WITH CHECK (
    portfolio_id IN (
      SELECT id FROM portfolios WHERE user_id = (select auth.uid())
    )
  );

-- ────────────────────────────────────────────────────────────────────────────
-- WATCHLIST
-- ────────────────────────────────────────────────────────────────────────────
DROP POLICY IF EXISTS "watchlist_own" ON watchlist;
CREATE POLICY "watchlist_own" ON watchlist
  FOR ALL
  USING     ((select auth.uid()) = user_id)
  WITH CHECK((select auth.uid()) = user_id);

-- ────────────────────────────────────────────────────────────────────────────
-- PRICE ALERTS
-- ────────────────────────────────────────────────────────────────────────────
DROP POLICY IF EXISTS "price_alerts_own" ON price_alerts;
CREATE POLICY "price_alerts_own" ON price_alerts
  FOR ALL
  USING     ((select auth.uid()) = user_id)
  WITH CHECK((select auth.uid()) = user_id);

-- ────────────────────────────────────────────────────────────────────────────
-- SAVED SCREENS
-- ────────────────────────────────────────────────────────────────────────────
DROP POLICY IF EXISTS "saved_screens_own" ON saved_screens;
CREATE POLICY "saved_screens_own" ON saved_screens
  FOR ALL
  USING     ((select auth.uid()) = user_id)
  WITH CHECK((select auth.uid()) = user_id);

-- ────────────────────────────────────────────────────────────────────────────
-- PORTFOLIO SNAPSHOTS
-- Add WITH CHECK to UPDATE; add explicit DELETE policy.
-- ────────────────────────────────────────────────────────────────────────────
DROP POLICY IF EXISTS "portfolio_snapshots_own_update" ON portfolio_snapshots;
CREATE POLICY "portfolio_snapshots_own_update" ON portfolio_snapshots
  FOR UPDATE
  USING     ((select auth.uid()) = user_id)
  WITH CHECK((select auth.uid()) = user_id);

DROP POLICY IF EXISTS "portfolio_snapshots_own_delete" ON portfolio_snapshots;
CREATE POLICY "portfolio_snapshots_own_delete" ON portfolio_snapshots
  FOR DELETE
  USING ((select auth.uid()) = user_id);

-- ────────────────────────────────────────────────────────────────────────────
-- NOTIFICATION PREFERENCES
-- ────────────────────────────────────────────────────────────────────────────
DROP POLICY IF EXISTS "notification_preferences_own" ON notification_preferences;
CREATE POLICY "notification_preferences_own" ON notification_preferences
  FOR ALL
  USING     ((select auth.uid()) = user_id)
  WITH CHECK((select auth.uid()) = user_id);

-- ────────────────────────────────────────────────────────────────────────────
-- NOTIFICATIONS
-- Replace bare FOR-ALL USING with explicit per-operation policies.
-- INSERT is intentionally excluded (notifications are inserted by service_role).
-- ────────────────────────────────────────────────────────────────────────────
DROP POLICY IF EXISTS "notifications_own" ON notifications;
CREATE POLICY "notifications_own_select" ON notifications
  FOR SELECT
  USING ((select auth.uid()) = user_id);

DROP POLICY IF EXISTS "notifications_own_delete" ON notifications;
CREATE POLICY "notifications_own_delete" ON notifications
  FOR DELETE
  USING ((select auth.uid()) = user_id);

-- Keep the existing UPDATE policy (already has USING + WITH CHECK); re-create
-- to ensure it uses the cached auth.uid() pattern for performance.
DROP POLICY IF EXISTS "notifications_own_update" ON notifications;
CREATE POLICY "notifications_own_update" ON notifications
  FOR UPDATE
  USING     ((select auth.uid()) = user_id)
  WITH CHECK((select auth.uid()) = user_id);

-- ────────────────────────────────────────────────────────────────────────────
-- USER TICKER REQUESTS
-- Add explicit DELETE so users can remove their own pending requests.
-- ────────────────────────────────────────────────────────────────────────────
DROP POLICY IF EXISTS "user_ticker_requests_own_delete" ON user_ticker_requests;
CREATE POLICY "user_ticker_requests_own_delete" ON user_ticker_requests
  FOR DELETE
  USING ((select auth.uid()) = user_id);

-- ────────────────────────────────────────────────────────────────────────────
-- CLIENT ERRORS  (new table)
-- Written by API via service_role (backend inserts, no anon access).
-- ────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS client_errors (
  id         UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  message    TEXT,
  stack      TEXT,
  url        TEXT,
  request_id TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE client_errors ENABLE ROW LEVEL SECURITY;

-- No anon or user access; only service_role (bypasses RLS) reads/writes.
-- The deny-by-default with no permissive policy achieves this.
