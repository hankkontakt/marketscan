-- MarketScan — Migration 043: QMJ-scores (evidensbaserad kvalitet-komposit)
-- Källa: yfinance RÅ-bokslut ("financials/cashflow/balance_sheet" — ALDRIG .info-derivativ).
-- Punkt-i-tid-regel: annual data giltig först från (fy_end + 5 månader).
-- Komposit: quality 40 / momentum 25 / insider 15 / value 10 / payout 10.
-- Hårda filter: short ≥8 % eller ny-disclosure <90 d → alpha_rank = NULL.
-- Skrivs av backend_worker/qmj_scores.py. Kör manuellt i Supabase SQL Editor.

-- ─── Tabell ──────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS qmj_scores (
    ticker           TEXT         NOT NULL,
    scan_date        DATE         NOT NULL,
    as_of_date       DATE,                    -- datum från vilket annual-data är giltig (fy_end + 5m)
    rebalance_flag   BOOLEAN      NOT NULL DEFAULT FALSE,   -- årlig ledviktning (april)
    quality_z        FLOAT,                   -- 0-100 (rank-percentil inom storleksgrupp)
    momentum_z       FLOAT,
    value_z          FLOAT,
    payout_z         FLOAT,
    insider_z        FLOAT,
    alpha_rank       FLOAT,                   -- komposit 0-100, NULL om hard filter
    exclusion_reason TEXT,
    warning_flags    JSONB        NOT NULL DEFAULT '[]'::jsonb,   -- ['sell_cluster','illiquid',...]
    data_quality     TEXT         NOT NULL DEFAULT 'ok',          -- ok | suspect | partial
    metrics_json     JSONB        NOT NULL DEFAULT '{}'::jsonb,   -- råa inputs för audit
    created_at       TIMESTAMPTZ  DEFAULT NOW(),
    PRIMARY KEY (ticker, scan_date)
);

-- ─── Index ───────────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_qmj_scores_rank ON qmj_scores (scan_date DESC, alpha_rank DESC);

-- ─── RLS ─────────────────────────────────────────────────────────────────────
ALTER TABLE qmj_scores ENABLE ROW LEVEL SECURITY;
CREATE POLICY "qmj_scores_public_read" ON qmj_scores
    FOR SELECT USING (true);
GRANT SELECT ON qmj_scores TO anon, authenticated;

-- ─── Diagnostics marker ──────────────────────────────────────────────────────
COMMENT ON TABLE qmj_scores IS
    'QMJ evidence-based quality composite (point-in-time aware). Written by qmj_scores.py.
    Migration 043. Diagnostic marker: migration_043_qmj_scores.';
