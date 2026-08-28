-- MarketScan — Migration 044: Säljkluster-kolumner (insider_cluster_signals)
-- Evidens (Lund 2015, svensk data 2005-2014): säljkluster har större förklaringskraft
-- än köpkluster. Beräknas av backend_worker/insider_cluster.py (calculate_sell_clusters).
-- Semantik: varningsflagga i UI — ändrar INTE alpha_rank (säljare kan vara ombalansering/skatt).
-- Kör manuellt i Supabase SQL Editor.

ALTER TABLE insider_cluster_signals
  ADD COLUMN IF NOT EXISTS unique_sellers_30d INTEGER NOT NULL DEFAULT 0;

ALTER TABLE insider_cluster_signals
  ADD COLUMN IF NOT EXISTS total_sell_amount_30d NUMERIC(16,2) DEFAULT 0;

CREATE INDEX IF NOT EXISTS idx_insider_cluster_sellers
  ON insider_cluster_signals (unique_sellers_30d DESC);

COMMENT ON TABLE insider_cluster_signals IS
  'Insider cluster signals (buy + sell). Migration 044 adds sell-cluster columns.
   Diagnostic marker: migration_044_sell_cluster_columns.';
