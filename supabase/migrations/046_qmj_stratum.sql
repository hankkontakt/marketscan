-- MarketScan — Migration 046: QMJ-stratum (jämförbarhetsskikt ny vs gammal)
-- Skikt: established | growth_early | new_small | turnaround. Percentiler beräknas
-- inom skikt när n>=20 (annars globalt) — se qmj_scores.py stratum_of().
-- Kör manuellt i Supabase SQL Editor.

ALTER TABLE qmj_scores
    ADD COLUMN IF NOT EXISTS stratum TEXT;

ALTER TABLE qmj_scores
    ADD COLUMN IF NOT EXISTS rank_mode TEXT DEFAULT 'global';  -- within_stratum | global

CREATE INDEX IF NOT EXISTS idx_qmj_scores_stratum ON qmj_scores (scan_date DESC, stratum);

COMMENT ON TABLE qmj_scores IS
    'QMJ composite (+stratum for fairness new vs old). Migration 046 adds stratum/rank_mode.
    Diagnostic marker: migration_046_qmj_stratum.';
