-- MarketScan — Migration 048: QMJ-faktorregim (factor_regime)
-- AQR QMJ Monthly (landskolumner SE/DK/FI/NO) → nordisk komposit → R12 →
-- OOS-percentil → Stark/Normal/Svag. Månadsvis jobb; historisk kontext, ej prognos.
-- Kör manuellt i Supabase SQL Editor.

CREATE TABLE IF NOT EXISTS factor_regime (
    computed_date   DATE PRIMARY KEY,
    data_through    DATE,
    premium_12m     NUMERIC,
    percentile      NUMERIC,
    n_obs           INTEGER,
    regime          TEXT NOT NULL CHECK (regime IN ('stark', 'normal', 'svag', 'otillracklig')),
    reason          TEXT,
    countries       TEXT[] DEFAULT ARRAY['SWE','DNK','FIN','NOR'],
    europe_12m      NUMERIC,
    global_12m      NUMERIC,
    source          TEXT DEFAULT 'aqr-qmj',
    updated_at      TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE factor_regime ENABLE ROW LEVEL SECURITY;

GRANT SELECT ON factor_regime TO anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON factor_regime TO service_role;

CREATE POLICY "factor_regime_public_read" ON factor_regime
    FOR SELECT USING (true);

COMMENT ON TABLE factor_regime IS
    'QMJ-factor-regime: trailing 12m premium for Nordic composite (AQR QMJ Monthly,
    USD, long-short, NOT directly investable). Historical context only — never a
    forecast. Migration 048. Diagnostic marker: migration_048_factor_regime.';
