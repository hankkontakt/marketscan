-- MarketScan — Migration 066: analyst_estimates (analytikeruppsida / target price)
-- Källa: yfinance .info (targetMeanPrice, numberOfAnalystOpinions, recommendationMean,
-- targetHighPrice, targetLowPrice, recommendationKey) — verifierad täckning i
-- .opencode/audit/datatest-yfinance.md (10/10 på targetMeanPrice, 10/10 på
-- numberOfAnalystOpinions, 6/10 på recommendationMean). Finnhub target-price är
-- US-only (datatest-nyckelberoende.md:97-98) — sparas endast som komplement.
-- Kör manuellt i Supabase SQL Editor.

CREATE TABLE IF NOT EXISTS analyst_estimates (
    ticker              TEXT         NOT NULL,
    fetched_at          DATE         NOT NULL,
    target_median       NUMERIC,                  -- targetMeanPrice (lokal valuta)
    target_high         NUMERIC,                  -- targetHighPrice
    target_low          NUMERIC,                  -- targetLowPrice
    target_count        INTEGER,                  -- numberOfAnalystOpinions
    upside_pct          NUMERIC,                  -- (target_median - price)/price
    recommendation_mean NUMERIC,                  -- 1 (stark sälj) - 5 (stark köp)
    recommendation_key  TEXT,                     -- 'strongBuy'|'buy'|'hold'|'sell'|'strongSell'
    source              TEXT         NOT NULL DEFAULT 'yfinance',  -- 'yfinance'|'finnhub'
    captured_at         TIMESTAMPTZ  DEFAULT now(),
    PRIMARY KEY (ticker, fetched_at)
);

CREATE INDEX IF NOT EXISTS idx_analyst_estimates_ticker
    ON analyst_estimates (ticker, fetched_at DESC);

ALTER TABLE analyst_estimates ENABLE ROW LEVEL SECURITY;

GRANT SELECT ON analyst_estimates TO anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON analyst_estimates TO service_role;

CREATE POLICY "analyst_estimates_public_read" ON analyst_estimates
    FOR SELECT USING (true);

COMMENT ON TABLE analyst_estimates IS
    'Analyst target price + recommendation per ticker (yfinance .info primary,
    Finnhub US-only complement). upside_pct is the key signal vs spot. Do NOT
    weight in before measuring Rank-IC in factor_metrics. Migration 066.
    Diagnostic marker: migration_066_analyst_estimates.';
