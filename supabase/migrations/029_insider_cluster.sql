-- Migration 029: Insider Cluster Signals
-- Tabell för klusterscoring av insiderköp.
-- Körs MANUELLT i Supabase SQL Editor.

CREATE TABLE IF NOT EXISTS insider_cluster_signals (
  ticker TEXT PRIMARY KEY,
  unique_buyers_30d INTEGER NOT NULL DEFAULT 0,
  total_buy_amount_30d NUMERIC(16,2) DEFAULT 0,
  cluster_score FLOAT DEFAULT 0,
  is_cluster BOOLEAN DEFAULT FALSE,
  exec_buy_90d BOOLEAN DEFAULT FALSE,
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE insider_cluster_signals ENABLE ROW LEVEL SECURITY;
GRANT SELECT ON insider_cluster_signals TO anon, authenticated;

CREATE POLICY "insider_cluster_public_read"
  ON insider_cluster_signals FOR SELECT
  USING (true);

-- Lägg även till ISIN-kolumn i company_profiles om den saknas
ALTER TABLE company_profiles
  ADD COLUMN IF NOT EXISTS isin TEXT;

CREATE INDEX IF NOT EXISTS idx_company_profiles_isin ON company_profiles (isin);

COMMENT ON TABLE insider_cluster_signals IS 'Insider cluster signals. Migration 029. Diagnostic marker: migration_029_insider_cluster.';
COMMENT ON TABLE company_profiles IS 'Company profiles with ISIN. Migration 029. Diagnostic marker: migration_029_isin.';
