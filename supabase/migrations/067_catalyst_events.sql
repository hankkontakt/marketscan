-- MarketScan — Migration 067: catalyst_events (kommande händelser per ticker)
-- Källa: earnings_surprises (announce_at från yfinance earnings_dates, PIT-snapshot
-- rader med estimate_source='snapshot' — redan skrivna av earnings_surprise.py varje
-- måndag) + dividend-yield från scan_results. INGEN Finnhub — US-only.
-- Byggs av backend_worker/catalyst_fetcher.py. Kör manuellt i Supabase SQL Editor.

CREATE TABLE IF NOT EXISTS catalyst_events (
    ticker          TEXT        NOT NULL,
    event_type      TEXT        NOT NULL,   -- 'earnings'|'dividend_ex'|'dividend_pay'|'ipo'
    event_date      DATE        NOT NULL,
    days_until      INTEGER,                -- (event_date - today) i dagar
    confidence      TEXT        NOT NULL DEFAULT 'medium',  -- 'high'|'medium'|'low'
    created_at      TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (ticker, event_type, event_date)
);

CREATE INDEX IF NOT EXISTS idx_catalyst_events_date
    ON catalyst_events (event_date ASC);

ALTER TABLE catalyst_events ENABLE ROW LEVEL SECURITY;

GRANT SELECT ON catalyst_events TO anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON catalyst_events TO service_role;

CREATE POLICY "catalyst_events_public_read" ON catalyst_events
    FOR SELECT USING (true);

COMMENT ON TABLE catalyst_events IS
    'Upcoming corporate events per ticker, built from earnings_surprises PIT
    snapshots (yfinance) + scan_results dividends. Boost for days_until <= 45.
    Migration 067. Diagnostic marker: migration_067_catalyst_events.';
