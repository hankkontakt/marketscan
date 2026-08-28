-- MarketScan — Migration 051: Kvartalsöverraskningar (earnings_surprises)
-- Källa: yfinance earnings_dates (konsensus-uppskattning + utfallet + surprise %,
-- med annonseringstidpunkt = PIT-nyckel). SUE = surprise / std(tidigare ≤8 kvartal),
-- kräv ≥4 tidigare observationer, clip ±3.
-- Kör manuellt i Supabase SQL Editor.

CREATE TABLE IF NOT EXISTS earnings_surprises (
    ticker          TEXT NOT NULL,
    announced_on    DATE NOT NULL,
    announce_at     TIMESTAMPTZ,
    eps_estimate    NUMERIC,
    eps_actual      NUMERIC,
    surprise_pct    NUMERIC,
    sue             NUMERIC,
    estimate_source TEXT NOT NULL DEFAULT 'retro',
    captured_at     TIMESTAMPTZ,
    computed_at     TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (ticker, announced_on)
);

CREATE INDEX IF NOT EXISTS idx_earnings_surprises_announce
    ON earnings_surprises (announce_at DESC);

ALTER TABLE earnings_surprises ENABLE ROW LEVEL SECURITY;

GRANT SELECT ON earnings_surprises TO anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON earnings_surprises TO service_role;

CREATE POLICY "earnings_surprises_public_read" ON earnings_surprises
    FOR SELECT USING (true);

COMMENT ON TABLE earnings_surprises IS
    'Standardized unexpected earnings per quarter (TS-SUE proxy): estimate vs
    actual from Yahoo Finance, announcement time = PIT. NOT a prediction — a
    measured surprise. Migration 051. Diagnostic marker: migration_051_earnings_surprises.';
