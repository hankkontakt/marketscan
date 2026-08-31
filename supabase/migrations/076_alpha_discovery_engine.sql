-- 076_alpha_discovery_engine.sql
-- Tabell för Guldkorns-radarn (Alpha Candidates & Inflection Points)

CREATE TABLE IF NOT EXISTS alpha_candidates (
    ticker TEXT PRIMARY KEY,
    company_name TEXT NOT NULL,
    country TEXT NOT NULL DEFAULT 'SE',
    sector TEXT,
    alpha_score NUMERIC(5, 2) NOT NULL,
    alpha_tier TEXT NOT NULL, -- 'TIER_1_ALPHA', 'TIER_2_ALPHA', 'WATCHLIST', 'NEUTRAL'
    verdict TEXT NOT NULL,
    badges JSONB DEFAULT '[]'::jsonb,
    thesis_memo TEXT,
    fcf_inflection_score NUMERIC(5, 2) DEFAULT 50.0,
    smart_money_score NUMERIC(5, 2) DEFAULT 50.0,
    catalyst_score NUMERIC(5, 2) DEFAULT 50.0,
    analyst_surge_score NUMERIC(5, 2) DEFAULT 50.0,
    wyckoff_score NUMERIC(5, 2) DEFAULT 50.0,
    dilution_penalty NUMERIC(5, 2) DEFAULT 0.0,
    warrant_overhang_flag BOOLEAN DEFAULT FALSE,
    is_illiquid BOOLEAN DEFAULT FALSE,
    subscores JSONB DEFAULT '{}'::jsonb,
    discovered_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_alpha_candidates_tier_score ON alpha_candidates(alpha_tier, alpha_score DESC);
CREATE INDEX IF NOT EXISTS idx_alpha_candidates_score ON alpha_candidates(alpha_score DESC);
