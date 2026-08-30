-- MarketScan — Migration 071: analyst_estimates-berikning (ROND 9)
-- Lägger till analyst_flags (FEW_ANALYSTS/STALE_TARGET/DEAD_TARGET),
-- currency (lokala valutan) och target_dispersion i analyst_estimates.
-- Kör manuellt i Supabase SQL Editor.

ALTER TABLE analyst_estimates ADD COLUMN IF NOT EXISTS analyst_flags JSONB NOT NULL DEFAULT '[]'::jsonb;
ALTER TABLE analyst_estimates ADD COLUMN IF NOT EXISTS currency TEXT;
ALTER TABLE analyst_estimates ADD COLUMN IF NOT EXISTS target_dispersion NUMERIC;

COMMENT ON COLUMN analyst_estimates.analyst_flags IS
    'Varningsflaggor: FEW_ANALYSTS (<3), STALE_TARGET (target/price ej i (0.1, 2.0)),
    DEAD_TARGET (upside > 200%). ROND 9. Migration 071.
    Diagnostic marker: migration_071_analyst_estimates_enrichment.';
