-- 065: ROND 7 — ny kolumn mews_candidate (tidig MEWS-kandidatflagg)
-- Bakgrund (ROND 7, 2026-08-30): MEWS-kvalitetsgaten (coverage>=4 -> 3) och nytt
-- kandidat-lager (mews_score >= 0.85 x tröskel) i smallcap/mews.py (65663fe).
-- mews_candidate = "värd att följa" (score 59.5-70) utan att lova full flagg.
-- Schemaändring (ADD COLUMN, nullable, default false).
-- Granskad av migration-vakt.

BEGIN;

ALTER TABLE scan_results ADD COLUMN IF NOT EXISTS mews_candidate BOOLEAN NOT NULL DEFAULT false;

COMMIT;
