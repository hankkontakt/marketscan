-- MarketScan 2.0 — Initial schema
-- Migration: 001_initial_schema
-- Run: supabase db push

-- ============================================================
-- MARKET DATA (no RLS — public read, pipeline writes via service key)
-- ============================================================

CREATE TABLE IF NOT EXISTS scan_results (
  ticker          TEXT        PRIMARY KEY,
  name            TEXT        NOT NULL,
  segment         TEXT        NOT NULL CHECK (segment IN ('large_cap','mid_cap','small_cap','micro_cap')),
  sector          TEXT,
  country         TEXT        DEFAULT 'SE',

  -- Scores (0-100)
  score_total     NUMERIC(5,2),
  score_value     NUMERIC(5,2),
  score_quality   NUMERIC(5,2),
  score_momentum  NUMERIC(5,2),
  score_growth    NUMERIC(5,2),
  score_risk      NUMERIC(5,2),
  score_size      NUMERIC(5,2),
  score_dividend  NUMERIC(5,2),
  score_sentiment NUMERIC(5,2),

  -- Signals
  entry_signal     TEXT CHECK (entry_signal IN ('STARK','OK','VÄNTA','EJ_AKTUELL')),
  confidence_label TEXT CHECK (confidence_label IN ('Hög','Medel','Låg')),
  trend_signal     TEXT CHECK (trend_signal IN ('Upptrend','Sidled','Nedtrend')),
  predicted_return NUMERIC(8,4),
  ml_rank          INTEGER,

  -- Fundamentals
  piotroski_f     INTEGER CHECK (piotroski_f BETWEEN 0 AND 9),
  price           NUMERIC(12,4),
  change_pct      NUMERIC(8,4),
  market_cap      NUMERIC(20,2),
  pe_trailing     NUMERIC(10,2),
  pe_forward      NUMERIC(10,2),
  roe             NUMERIC(8,4),
  roa             NUMERIC(8,4),
  revenue_growth  NUMERIC(8,4),
  earnings_growth NUMERIC(8,4),
  debt_to_equity  NUMERIC(10,4),
  current_ratio   NUMERIC(8,4),
  gross_margin    NUMERIC(8,4),
  operating_margin NUMERIC(8,4),
  dividend_yield  NUMERIC(8,4),
  beta            NUMERIC(6,4),
  vol_20d         NUMERIC(8,4),

  -- Flags
  low_liquidity   BOOLEAN     DEFAULT FALSE,
  has_holding     BOOLEAN     DEFAULT FALSE,

  -- Meta
  scan_date       DATE        NOT NULL DEFAULT CURRENT_DATE,
  updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_scan_segment_score  ON scan_results (segment, score_total DESC);
CREATE INDEX IF NOT EXISTS idx_scan_sector_score   ON scan_results (sector, score_total DESC);
CREATE INDEX IF NOT EXISTS idx_scan_entry          ON scan_results (entry_signal, score_total DESC);
CREATE INDEX IF NOT EXISTS idx_scan_date           ON scan_results (scan_date);

-- ============================================================
-- USER DATA (RLS enforced)
-- ============================================================

CREATE TABLE IF NOT EXISTS profiles (
  id           UUID        PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  display_name TEXT,
  role         TEXT        DEFAULT 'user' CHECK (role IN ('user','admin')),
  created_at   TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS portfolios (
  id         UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id    UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  name       TEXT        NOT NULL DEFAULT 'Min portfölj',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS holdings (
  id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  portfolio_id UUID        NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
  ticker       TEXT        NOT NULL,
  shares       NUMERIC(14,4) NOT NULL CHECK (shares > 0),
  cost_basis   NUMERIC(12,4),
  added_at     TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS watchlist (
  id         UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id    UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  ticker     TEXT        NOT NULL,
  added_at   TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (user_id, ticker)
);

CREATE TABLE IF NOT EXISTS price_alerts (
  id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id      UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  ticker       TEXT        NOT NULL,
  condition    TEXT        NOT NULL CHECK (condition IN ('above','below')),
  target_price NUMERIC(12,4) NOT NULL,
  note         TEXT,
  active       BOOLEAN     DEFAULT TRUE,
  triggered_at TIMESTAMPTZ,
  created_at   TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS saved_screens (
  id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  name        TEXT        NOT NULL,
  filter_json JSONB       NOT NULL DEFAULT '{}',
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- PIPELINE LOG (admin/monitoring)
-- ============================================================

CREATE TABLE IF NOT EXISTS pipeline_runs (
  id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  run_type    TEXT        NOT NULL CHECK (run_type IN ('morning','evening','weekly','manual','smallcap','targeted','refresh_missing','retry_rate_limited')),
  status      TEXT        NOT NULL CHECK (status IN ('running','success','failed')),
  tickers_ok  INTEGER,
  tickers_err INTEGER,
  duration_s  NUMERIC(8,1),
  error_msg   TEXT,
  started_at  TIMESTAMPTZ DEFAULT NOW(),
  finished_at TIMESTAMPTZ
);

-- ============================================================
-- ROW LEVEL SECURITY
-- ============================================================

ALTER TABLE profiles      ENABLE ROW LEVEL SECURITY;
ALTER TABLE portfolios    ENABLE ROW LEVEL SECURITY;
ALTER TABLE holdings      ENABLE ROW LEVEL SECURITY;
ALTER TABLE watchlist     ENABLE ROW LEVEL SECURITY;
ALTER TABLE price_alerts  ENABLE ROW LEVEL SECURITY;
ALTER TABLE saved_screens ENABLE ROW LEVEL SECURITY;

-- Profiles: own row only
CREATE POLICY "profiles_own" ON profiles USING (auth.uid() = id);

-- Portfolios: own rows
CREATE POLICY "portfolios_own" ON portfolios USING (auth.uid() = user_id);

-- Holdings: via portfolio ownership
CREATE POLICY "holdings_own" ON holdings
  USING (portfolio_id IN (SELECT id FROM portfolios WHERE user_id = auth.uid()));

-- Watchlist, alerts, screens: own rows
CREATE POLICY "watchlist_own"      ON watchlist     USING (auth.uid() = user_id);
CREATE POLICY "price_alerts_own"   ON price_alerts  USING (auth.uid() = user_id);
CREATE POLICY "saved_screens_own"  ON saved_screens USING (auth.uid() = user_id);

-- Auto-create profile on signup
CREATE OR REPLACE FUNCTION handle_new_user() RETURNS trigger
  LANGUAGE plpgsql SECURITY DEFINER AS $$
BEGIN
  INSERT INTO profiles (id, display_name) VALUES (NEW.id, NEW.email);
  INSERT INTO portfolios (user_id, name) VALUES (NEW.id, 'Min portfölj');
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION handle_new_user();
