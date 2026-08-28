-- MarketScan — Migration 041: Short Positions (FI:s blankningsregister)
-- Daglig snapshot av netto-korta positioner (regel: >0.1 % rapporteras, >0.5 % publiceras
-- med innehavare). Källa: https://www.fi.se/en/our-registers/net-short-positions/
-- Skrivs av backend_worker/fi_short_positions.py. Riskfilter + ny-disclosure-varning.
-- Kör manuellt i Supabase SQL Editor.

-- ─── Tabell ──────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS short_positions (
    scan_date            DATE         NOT NULL,
    lei                  TEXT         NOT NULL,
    ticker               TEXT,                          -- via universe_registry.lei
    issuer_name          TEXT,
    total_short_pct      NUMERIC(8,3) NOT NULL,         -- summa rapporterade (>0.1 %) positioner
    latest_position_date DATE,
    holders_json         JSONB        NOT NULL DEFAULT '[]'::jsonb,  -- per-emittentdetaljer (>0.5 %)
    is_new_discovery     BOOLEAN      NOT NULL DEFAULT FALSE,  -- första förekomst >0.5 % eller Δ≥+0.5 pp/90 d
    delta_pp             NUMERIC(8,3),                  -- förändring vs senast kända snapshot
    created_at           TIMESTAMPTZ  DEFAULT NOW(),
    PRIMARY KEY (scan_date, lei)
);

-- ─── Index ───────────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_short_positions_ticker_date
    ON short_positions (ticker, scan_date DESC);
CREATE INDEX IF NOT EXISTS idx_short_positions_lei_date
    ON short_positions (lei, scan_date DESC);
CREATE INDEX IF NOT EXISTS idx_short_positions_new_discovery
    ON short_positions (scan_date) WHERE is_new_discovery = TRUE;

-- ─── RLS ─────────────────────────────────────────────────────────────────────
ALTER TABLE short_positions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "short_positions_public_read" ON short_positions
    FOR SELECT USING (true);
GRANT SELECT ON short_positions TO anon, authenticated;

-- ─── Diagnostics marker ──────────────────────────────────────────────────────
COMMENT ON TABLE short_positions IS
    'Daily net short position snapshots (FI register). Written by fi_short_positions.py.
    Migration 041. Diagnostic marker: migration_041_short_positions.';
