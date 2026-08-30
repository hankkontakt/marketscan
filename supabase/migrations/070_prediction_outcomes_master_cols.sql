-- MarketScan — Migration 070: prediction_outcomes-masterkolumner (evidensloop)
-- Sparar matchande master_rank + block vid prediktionstillfället så att
-- T1-träffprocent och block-IC kan mätas på realiserade utfall.
-- Kör manuellt i Supabase SQL Editor.

ALTER TABLE prediction_outcomes ADD COLUMN IF NOT EXISTS master_rank FLOAT;
ALTER TABLE prediction_outcomes ADD COLUMN IF NOT EXISTS master_tier TEXT;
ALTER TABLE prediction_outcomes ADD COLUMN IF NOT EXISTS analyst_z  FLOAT;
ALTER TABLE prediction_outcomes ADD COLUMN IF NOT EXISTS tech_z     FLOAT;
ALTER TABLE prediction_outcomes ADD COLUMN IF NOT EXISTS val_hist_z FLOAT;
ALTER TABLE prediction_outcomes ADD COLUMN IF NOT EXISTS catalyst_z FLOAT;

COMMENT ON COLUMN prediction_outcomes.master_rank IS
    'MasterRank at prediction time (ROND 8) for outcome evaluation. Migration 070.
    Diagnostic marker: migration_070_prediction_outcomes_master_cols.';
