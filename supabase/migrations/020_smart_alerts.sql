-- MarketScan — Migration 020: Smart Alerts & Market Intelligence
-- Enables compound alert rules, score history tracking, signal transitions,
-- and weekly digest subscriptions.

-- ─── Score History ────────────────────────────────────────────────────────────
-- Daily snapshot of every ticker's scores. Populated by backend_worker/score_tracker.py
-- after each pipeline run. Enables: signal persistence analysis, score trend charts,
-- and compound alert evaluation against historical data.
CREATE TABLE IF NOT EXISTS score_history (
  id              UUID    PRIMARY KEY DEFAULT gen_random_uuid(),
  ticker          TEXT    NOT NULL,
  scan_date       DATE    NOT NULL,

  -- Scores
  score_total     NUMERIC(6,2),
  score_value     NUMERIC(6,2),
  score_quality   NUMERIC(6,2),
  score_momentum  NUMERIC(6,2),
  score_growth    NUMERIC(6,2),
  score_risk      NUMERIC(6,2),
  score_dividend  NUMERIC(6,2),
  score_sentiment NUMERIC(6,2),

  -- Signals
  entry_signal    TEXT,
  confidence_label TEXT,
  trend_signal    TEXT,

  -- Price snapshot
  price           NUMERIC(14,4),
  change_pct      NUMERIC(8,4),
  vol_20d         NUMERIC(10,6),

  -- Piotroski
  piotroski_f     INT,

  UNIQUE (ticker, scan_date)
);

CREATE INDEX IF NOT EXISTS idx_score_history_ticker_date
  ON score_history (ticker, scan_date DESC);

CREATE INDEX IF NOT EXISTS idx_score_history_date
  ON score_history (scan_date DESC);

-- Public read (market data, no user data)
ALTER TABLE score_history ENABLE ROW LEVEL SECURITY;

CREATE POLICY "score_history_public_read" ON score_history
  FOR SELECT USING (true);


-- ─── Signal Transitions ──────────────────────────────────────────────────────
-- Logs every time a ticker's entry_signal or trend_signal changes.
-- Used for: signal persistence analytics, signal_change alert type.
CREATE TABLE IF NOT EXISTS signal_transitions (
  id              UUID    PRIMARY KEY DEFAULT gen_random_uuid(),
  ticker          TEXT    NOT NULL,
  transition_date DATE    NOT NULL,
  field           TEXT    NOT NULL CHECK (field IN ('entry_signal', 'trend_signal')),
  from_value      TEXT,
  to_value        TEXT,
  score_total_at  NUMERIC(6,2),
  price_at        NUMERIC(14,4),
  created_at      TIMESTAMPTZ DEFAULT NOW(),

  UNIQUE (ticker, transition_date, field)
);

CREATE INDEX IF NOT EXISTS idx_signal_transitions_ticker
  ON signal_transitions (ticker, transition_date DESC);

CREATE INDEX IF NOT EXISTS idx_signal_transitions_date
  ON signal_transitions (transition_date DESC);

-- Public read
ALTER TABLE signal_transitions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "signal_transitions_public_read" ON signal_transitions
  FOR SELECT USING (true);


-- ─── Alert Rules (compound) ──────────────────────────────────────────────────
-- Replaces the simplistic price_alerts with a multi-condition rule engine.
-- Conditions are evaluated nightly by backend_worker/smart_alert_engine.py.
CREATE TABLE IF NOT EXISTS alert_rules (
  id            UUID    PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id       UUID    NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  name          TEXT    NOT NULL,
  rule_type     TEXT    NOT NULL
                CHECK (rule_type IN (
                  'price_cross',       -- price crosses a threshold
                  'score_change',      -- score_total changes by N points
                  'signal_change',     -- entry_signal or trend_signal changes
                  'screen_match',      -- compound filter match (new entry only)
                  'insider_cluster',   -- multiple insiders buy same stock
                  'volatility_spike'   -- vol_20d spikes > 50%
                )),

  -- Ticker-specific rules (price_cross, signal_change) — null = all tickers
  ticker        TEXT,

  -- Compound condition rules (for screen_match, score_change, etc.)
  -- Format: [{field, op, value}, ...]
  conditions    JSONB   NOT NULL DEFAULT '[]',

  -- Notification thresholds
  score_change_min  NUMERIC(6,2) DEFAULT 10,   -- for score_change type
  insider_min_count INT          DEFAULT 2,    -- for insider_cluster type
  vol_spike_min_pct NUMERIC(6,2) DEFAULT 50,   -- for volatility_spike type

  active        BOOLEAN NOT NULL DEFAULT true,
  trigger_once  BOOLEAN NOT NULL DEFAULT false, -- deactivate after first trigger
  last_triggered TIMESTAMPTZ,
  trigger_count  INT     NOT NULL DEFAULT 0,
  created_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_alert_rules_user_active
  ON alert_rules (user_id, active, rule_type);

ALTER TABLE alert_rules ENABLE ROW LEVEL SECURITY;

CREATE POLICY "alert_rules_own" ON alert_rules
  FOR ALL
  USING     ((select auth.uid()) = user_id)
  WITH CHECK((select auth.uid()) = user_id);


-- ─── Triggered Alerts Log ────────────────────────────────────────────────────
-- History of triggered alerts (30-day rolling, for /alerts/historia).
CREATE TABLE IF NOT EXISTS triggered_alerts (
  id             UUID    PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id        UUID    NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  rule_id        UUID    REFERENCES alert_rules(id) ON DELETE SET NULL,
  rule_name      TEXT    NOT NULL,
  rule_type      TEXT    NOT NULL,
  ticker         TEXT,
  detail         TEXT,         -- human-readable description of what triggered
  score_at       NUMERIC(6,2),
  price_at       NUMERIC(14,4),
  triggered_at   TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_triggered_alerts_user
  ON triggered_alerts (user_id, triggered_at DESC);

ALTER TABLE triggered_alerts ENABLE ROW LEVEL SECURITY;

CREATE POLICY "triggered_alerts_own" ON triggered_alerts
  FOR ALL
  USING     ((select auth.uid()) = user_id)
  WITH CHECK((select auth.uid()) = user_id);


-- ─── Digest Log ──────────────────────────────────────────────────────────────
-- Tracks which weekly digests have been sent to prevent duplicates.
CREATE TABLE IF NOT EXISTS digest_log (
  id          UUID    PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     UUID    NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  digest_type TEXT    NOT NULL DEFAULT 'weekly',
  week_start  DATE    NOT NULL,
  sent_at     TIMESTAMPTZ DEFAULT NOW(),
  email_to    TEXT    NOT NULL,

  UNIQUE (user_id, digest_type, week_start)
);

ALTER TABLE digest_log ENABLE ROW LEVEL SECURITY;
-- No user access needed (service_role only)


-- ─── Extend profiles with digest preferences ─────────────────────────────────
-- Add weekly_digest column to profiles if not already present.
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'profiles' AND column_name = 'weekly_digest'
  ) THEN
    ALTER TABLE profiles ADD COLUMN weekly_digest BOOLEAN DEFAULT true;
  END IF;
END $$;
