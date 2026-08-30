-- MarketScan — Migration 068: master_rank (auktoritativ rankningsmotor, ROND 8)
-- Fuserar score_total (externt repo) + QMJ alpha_rank med fyra nya block:
--   A) värderingsgrind (mot egen historik + peers + absolut/PEG)
--   B) analytikeruppsida (analyst_estimates)
--   C) teknisk position (RSI14/MA50/MA200/52v-hög — beräknas nu, lagras aldrig)
--   D) katalysatorfönster (catalyst_events) + PIT soft-block
-- Vikter i backend_worker/resources/weights.json (data-drivna från factor_metrics).
-- Skrivs av backend_worker/master_rank.py. Kör manuellt i Supabase SQL Editor.

CREATE TABLE IF NOT EXISTS master_rank (
    ticker            TEXT         NOT NULL,
    scan_date         DATE         NOT NULL,
    master_rank       FLOAT,                    -- 0-100 viktad komposit (NULL = EXCLUDED)
    tier              TEXT,                     -- T1|T2|T3|T4|EXCLUDED
    quality_z         FLOAT,                    -- QMJ quality_z + score_quality-medel
    value_z           FLOAT,                    -- QMJ value_z + Block A-medel
    momentum_z        FLOAT,                    -- QMJ momentum_z + score_momentum + tech_z-medel
    analyst_z         FLOAT,                    -- Block B (0-100)
    tech_z            FLOAT,                    -- Block C (0-100, RSI/MA/52v-medel)
    insider_z         FLOAT,                    -- QMJ insider_z
    catalyst_z        FLOAT,                    -- Block D (0-100)
    payout_z          FLOAT,                    -- QMJ payout_z
    growth_z          FLOAT,                    -- score_growth (0-100)
    -- Block A (värdering)
    val_hist_z        FLOAT,                    -- P/E vs egen 5-yr historik (percentil)
    val_peers_z       FLOAT,                    -- P/E vs sektor-peers (≥15 peers)
    val_abs_z         FLOAT,                    -- PEG/EV-justerad absolut
    val_flags         JSONB        NOT NULL DEFAULT '[]'::jsonb,  -- ['EXTREME_OVERVAL','CHEAP']
    -- Block B (analytiker)
    analyst_upside    NUMERIC,                  -- % uppsida (target_median vs spot)
    analyst_count     INTEGER,
    analyst_flags     JSONB        NOT NULL DEFAULT '[]'::jsonb,  -- ['FEW_ANALYSTS','STALE_TARGET','DEAD_TARGET']
    -- Block C (teknisk)
    rsi_14            FLOAT,
    ma50_dist_pct     FLOAT,
    ma200_dist_pct    FLOAT,
    dist_52w_high_pct FLOAT,
    trend_tech        TEXT,                     -- 'Upptrend'|'Sidled'|'Nedtrend'
    tech_flags        JSONB        NOT NULL DEFAULT '[]'::jsonb,  -- ['OVERBOUGHT','OVERSOLD','TREND_DOWN','PULLBACK']
    -- Block D (katalysator)
    catalyst_next     TEXT,                     -- 'YYYY-MM-DD:earnings'
    catalyst_days     INTEGER,
    pit_status        TEXT         NOT NULL DEFAULT 'READY', -- READY|PENDING|STALE
    pit_reason        TEXT,                     -- 'fy_end+5mån ej passerat' etc.
    -- Exklusioner / flaggor
    exclusion_reason  TEXT,
    warning_flags     JSONB        NOT NULL DEFAULT '[]'::jsonb,
    data_missing      JSONB        NOT NULL DEFAULT '[]'::jsonb,  -- block utan data
    created_at        TIMESTAMPTZ  DEFAULT now(),
    PRIMARY KEY (ticker, scan_date)
);

CREATE INDEX IF NOT EXISTS idx_master_rank_tier
    ON master_rank (scan_date DESC, tier ASC, master_rank DESC);
CREATE INDEX IF NOT EXISTS idx_master_rank_ticker
    ON master_rank (ticker, scan_date DESC);

ALTER TABLE master_rank ENABLE ROW LEVEL SECURITY;

GRANT SELECT ON master_rank TO anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON master_rank TO service_role;

CREATE POLICY "master_rank_public_read" ON master_rank
    FOR SELECT USING (true);

COMMENT ON TABLE master_rank IS
    'Single authoritative ranking (ROND 8, MasterRank). Fuses score_total + QMJ
    alpha_rank + 4 new blocks (valuation-history, analyst, technical, catalyst).
    Anti-bubble gate: EXTREME_OVERVAL + OVERBOUGHT caps rank at 60 (BUBBLE_TRIAGE).
    Written by backend_worker/master_rank.py. Migration 068.
    Diagnostic marker: migration_068_master_rank.';
