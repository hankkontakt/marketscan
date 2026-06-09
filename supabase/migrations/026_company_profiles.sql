-- Migration 026: company_profiles table
--
-- Stores company description data fetched from yfinance (free, no API key).
-- Populated weekly by backend_worker/company_info_fetcher.py.
-- Surfaced in the Overview tab of each stock page.
--
-- Note on AI translation: longBusinessSummary is stored in English for now.
-- Future: run through DeepSeek/GPT to translate to Swedish during weekly refresh.
-- (TODO: backend_worker/ai_analysis.py + company_profiles.description_sv column)
--
-- Run in Supabase SQL Editor (Settings → SQL Editor → New query).

CREATE TABLE IF NOT EXISTS company_profiles (
  ticker          TEXT        PRIMARY KEY,
  description     TEXT,                         -- longBusinessSummary (English)
  employees       INTEGER,                      -- fullTimeEmployees
  website         TEXT,                         -- company website URL
  industry        TEXT,                         -- yfinance industry string
  country         TEXT,                         -- country of incorporation
  beta            NUMERIC(6,4),                 -- 5-year monthly beta vs S&P500
  week_52_high    NUMERIC(12,4),                -- 52-week high price
  week_52_low     NUMERIC(12,4),                -- 52-week low price
  updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Index for bulk joins from API
CREATE INDEX IF NOT EXISTS idx_company_profiles_updated
  ON company_profiles (updated_at DESC);

-- No RLS needed — same access model as scan_results (public read, pipeline write)
