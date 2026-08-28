-- MarketScan — Migration 045: News Events (nyhetskedjan)
-- Källa: Nasdaq Nordics officiella API (query.action) + Google News RSS + DDGS.
-- Bäring/riktning/förtroende fylls av news_classifier.py (DeepSeek, thinking OFF).
-- Skrivs av backend_worker/news_events.py / news_discovery.py / news_classifier.py.
-- Kör manuellt i Supabase SQL Editor.

CREATE TABLE IF NOT EXISTS news_events (
    event_id         TEXT         PRIMARY KEY,       -- hash: källa+url (stabil identitet)
    source           TEXT         NOT NULL,          -- nasdaq | gnews | ddgs
    source_category  TEXT,                           -- cnsCategory (nasdaq) / tema (gnews)
    headline         TEXT         NOT NULL,
    company_raw      TEXT,                           -- från källan (Nasdaq: 'company')
    ticker           TEXT,                           -- mappad via registret
    published_at     TIMESTAMPTZ  NOT NULL,
    message_url      TEXT,
    bearing          TEXT,                           -- positive | negative | neutral | conditional
    confidence       FLOAT,                          -- 0-1 (LLM) eller 1.0 (regelbaserad)
    direction        TEXT,                           -- kortfakta: t.ex. 'rights_issue', 'buyback', null
    is_candidate     BOOLEAN      NOT NULL DEFAULT FALSE,  -- rör radar-kandidat
    mention_surge    FLOAT,                           -- omnämnande-z (24-48h vs 30d-baslinje)
    classified_at    TIMESTAMPTZ,
    created_at       TIMESTAMPTZ  DEFAULT NOW(),
    UNIQUE (source, message_url)
);

CREATE INDEX IF NOT EXISTS idx_news_events_published ON news_events (published_at DESC);
CREATE INDEX IF NOT EXISTS idx_news_events_ticker ON news_events (ticker, published_at DESC);
CREATE INDEX IF NOT EXISTS idx_news_events_classified ON news_events (bearing, classified_at);

ALTER TABLE news_events ENABLE ROW LEVEL SECURITY;
CREATE POLICY "news_events_public_read" ON news_events
    FOR SELECT USING (true);
GRANT SELECT ON news_events TO anon, authenticated;

COMMENT ON TABLE news_events IS
    'Unified news event stream (Nasdaq official + Google News + DDGS) with LLM bearings.
    Written by news_events.py/news_discovery.py/news_classifier.py. Migration 045.
    Diagnostic marker: migration_045_news_events.';
