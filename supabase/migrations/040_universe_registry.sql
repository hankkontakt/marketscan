-- MarketScan — Migration 040: Universe Registry (leverantörsagnostiskt nordiskt universum)
-- Sanning: FI-emittentlista (marknadssök). Yahoo-tickern är en derivat-nyckel.
-- Delisting-detektor: FI-lista vs Yahoo-presence. Skrivs av backend_worker/universe_mapping.py.
-- Kör manuellt i Supabase SQL Editor.

-- ─── Tabell ──────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS universe_registry (
    isin          TEXT        PRIMARY KEY,
    ticker        TEXT,                            -- NULL = ännu ej mappad till Yahoo
    orgnr         TEXT,
    lei           TEXT,
    name          TEXT        NOT NULL,
    market        TEXT,                             -- t.ex. 'Nasdaq Stockholm', 'First North', 'NGM'
    status        TEXT        NOT NULL DEFAULT 'listed',  -- listed | verify | delisted | unmapped
    listed_date   DATE,
    delisted_date DATE,
    source        TEXT        NOT NULL DEFAULT 'fi',
    updated_at    TIMESTAMPTZ DEFAULT NOW()
);

-- ─── Index ───────────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_universe_registry_ticker ON universe_registry (ticker);
CREATE INDEX IF NOT EXISTS idx_universe_registry_status ON universe_registry (status);
CREATE INDEX IF NOT EXISTS idx_universe_registry_lei ON universe_registry (lei);

-- ─── RLS ─────────────────────────────────────────────────────────────────────
ALTER TABLE universe_registry ENABLE ROW LEVEL SECURITY;
CREATE POLICY "universe_registry_public_read" ON universe_registry
    FOR SELECT USING (true);
GRANT SELECT ON universe_registry TO anon, authenticated;

-- ─── Diagnostics marker ──────────────────────────────────────────────────────
COMMENT ON TABLE universe_registry IS
    'Authoritative Nordic universe registry (FI emittent list = truth, Yahoo ticker = derived key).
    Written by backend_worker/universe_mapping.py (service_role).
    Migration 040. Diagnostic marker: migration_040_universe_registry.';
