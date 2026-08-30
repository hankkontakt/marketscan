-- MarketScan — Migration 069: score_history-masterkolumner (evidensloop)
-- Loggar master_rank + block-delscores per ticker/dag så att signal_analytics
-- kan beräkna Rank-IC per master-block (den mekanism som driver viktjusteringen).
-- Kör manuellt i Supabase SQL Editor.

ALTER TABLE score_history ADD COLUMN IF NOT EXISTS master_rank    FLOAT;
ALTER TABLE score_history ADD COLUMN IF NOT EXISTS master_tier    TEXT;
ALTER TABLE score_history ADD COLUMN IF NOT EXISTS analyst_z      FLOAT;
ALTER TABLE score_history ADD COLUMN IF NOT EXISTS tech_z         FLOAT;
ALTER TABLE score_history ADD COLUMN IF NOT EXISTS val_hist_z     FLOAT;
ALTER TABLE score_history ADD COLUMN IF NOT EXISTS catalyst_z     FLOAT;
ALTER TABLE score_history ADD COLUMN IF NOT EXISTS pit_status     TEXT;

CREATE INDEX IF NOT EXISTS idx_score_history_master
    ON score_history (scan_date DESC, master_rank DESC) WHERE master_rank IS NOT NULL;

COMMENT ON COLUMN score_history.master_rank IS
    'MasterRank composite at snapshot time (ROND 8). Powers factor_metrics IC
    evaluation for master blocks. Migration 069.
    Diagnostic marker: migration_069_score_history_master_cols.';
