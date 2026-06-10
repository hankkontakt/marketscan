-- Migration 028: MEWS (Multi-Bagger Early Warning Score) kolumner
-- Lägg kolumner på scan_results för MEWS-score + komponenter.
-- Körs MANUELLT i Supabase SQL Editor.

ALTER TABLE scan_results
  ADD COLUMN IF NOT EXISTS mews_score FLOAT,
  ADD COLUMN IF NOT EXISTS mews_flag BOOLEAN DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS mews_fcf_yield FLOAT,
  ADD COLUMN IF NOT EXISTS mews_small_size FLOAT,
  ADD COLUMN IF NOT EXISTS mews_low_ps FLOAT,
  ADD COLUMN IF NOT EXISTS mews_operating_leverage FLOAT,
  ADD COLUMN IF NOT EXISTS mews_revenue_accel FLOAT,
  ADD COLUMN IF NOT EXISTS mews_clean_accruals FLOAT;

CREATE INDEX IF NOT EXISTS idx_scan_mews ON scan_results (mews_score DESC) WHERE mews_flag;

COMMENT ON TABLE scan_results IS 'Scan results with MEWS columns. Migration 028. Diagnostic marker: migration_028_mews.';
