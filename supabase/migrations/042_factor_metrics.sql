-- MarketScan — Migration 042: Factor Metrics (forward-validering per faktor)
-- Mäter om varje faktor (kvalitet, momentum, total, growth, value) faktiskt predikterar
-- framtida avkastning: Rank-IC + decil-spread (brutto netto 1 %/sida), win-rate.
-- Skrivs av backend_worker/signal_analytics.py (läggs till i weekly-körningen).
-- Kör manuellt i Supabase SQL Editor.

-- ─── Tabell ──────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS factor_metrics (
    factor             TEXT         NOT NULL,   -- score_quality | score_momentum | score_total | ...
    horizon_days       INTEGER      NOT NULL,   -- 90 | 180 | 365
    computed_date      DATE         NOT NULL DEFAULT CURRENT_DATE,
    n                  INTEGER      NOT NULL DEFAULT 0,          -- antal observationer
    rank_ic            FLOAT,                                    -- Spearman-korrelation faktor→avkastning
    decile_spread      FLOAT,                                    -- decil10-medel − decil1-medel (brutto, decimal)
    decile_spread_net  FLOAT,                                    -- brutto − 2×0.01 (round-trip 1 %/sida)
    win_rate           FLOAT,                                    -- andel decil10 > 0 (decimal)
    computed_at        TIMESTAMPTZ  DEFAULT NOW(),
    PRIMARY KEY (factor, horizon_days, computed_date)
);

-- ─── Index ───────────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_factor_metrics_factor ON factor_metrics (factor, horizon_days);

-- ─── RLS ─────────────────────────────────────────────────────────────────────
ALTER TABLE factor_metrics ENABLE ROW LEVEL SECURITY;
CREATE POLICY "factor_metrics_public_read" ON factor_metrics
    FOR SELECT USING (true);
GRANT SELECT ON factor_metrics TO anon, authenticated;

-- ─── Diagnostics marker ──────────────────────────────────────────────────────
COMMENT ON TABLE factor_metrics IS
    'Forward factor validation: Rank-IC and decile spreads per factor/horizon.
    Written by signal_analytics.py (weekly). Migration 042.
    Diagnostic marker: migration_042_factor_metrics.';
