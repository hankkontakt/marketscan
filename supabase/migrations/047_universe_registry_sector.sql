-- MarketScan — Migration 047: Sektor-kolumn (universe_registry)
-- Sektor/bransch från yf.Lookup (industryName) + Finnhub profile2. Möjliggör
-- sektorjämförelse i värde-faktorn (QMJ) samt bättre radarfilter.
-- Kör manuellt i Supabase SQL Editor.

ALTER TABLE universe_registry
    ADD COLUMN IF NOT EXISTS sector TEXT;

CREATE INDEX IF NOT EXISTS idx_universe_registry_sector
    ON universe_registry (sector);

COMMENT ON TABLE universe_registry IS
    'Authoritative Nordic universe registry (+sector for comparability).
    Migration 047 adds sector for sector-relative valuation.
    Diagnostic marker: migration_047_universe_registry_sector.';
