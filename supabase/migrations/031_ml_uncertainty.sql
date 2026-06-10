-- Migration 031: ML Uncertainty + Regime columns for #15
-- Lägg kolumner på scan_results för ensemble-osäkerhet och regim-snapshot.
-- Körs MANUELLT i Supabase SQL Editor.

ALTER TABLE scan_results
  ADD COLUMN IF NOT EXISTS ml_uncertainty FLOAT,
  ADD COLUMN IF NOT EXISTS ml_flag_uncertain BOOLEAN DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS regime_at_scan TEXT;

COMMENT ON TABLE scan_results IS 'Scan results with ML uncertainty and regime. Migration 031. Diagnostic marker: migration_031_ml_uncertainty.';
