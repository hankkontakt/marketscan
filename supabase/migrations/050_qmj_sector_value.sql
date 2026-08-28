-- MarketScan — Migration 050: Sektorrelativ värdefaktor (qmj_scores)
-- sector_value_z = percentil av värdekomponenter INOM sektor (kräver ≥5 bolag i
-- sektorn), annars global. value_mode = 'sector' | 'global' | NULL(gammal data).
-- Komposit-fråga: value_z (global) behålls som poängställning; sector_value_z
-- visas i radarn + möjlig QMJ-justering framöver (metodföljd dokumenterad).
-- Kör manuellt i Supabase SQL Editor.

ALTER TABLE qmj_scores
    ADD COLUMN IF NOT EXISTS sector_value_z  NUMERIC,
    ADD COLUMN IF NOT EXISTS value_mode      TEXT;

ALTER TABLE qmj_scores
    DROP CONSTRAINT IF EXISTS qmj_scores_value_mode_check;
ALTER TABLE qmj_scores
    ADD CONSTRAINT qmj_scores_value_mode_check
    CHECK (value_mode IS NULL OR value_mode IN ('sector', 'global'));

COMMENT ON TABLE qmj_scores IS
    'QMJ scores per ticker per scan. Migration 050 adds sector-relative value
    percentile (sector_value_z) + value_mode; rows from before 050 have NULL
    sector_value_z (global value_z remains the composite input).';
