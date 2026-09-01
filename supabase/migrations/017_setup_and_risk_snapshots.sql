-- SetupState and Risk Snapshots Schema (Phase 5)
-- Shadow logging and deterministic timing & risk states

-- 1. Setup Snapshots
CREATE TABLE IF NOT EXISTS public.setup_snapshots (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  listing_id          UUID NOT NULL REFERENCES public.listings(listing_id) ON DELETE CASCADE,
  snapshot_date       DATE NOT NULL,
  setup_state         TEXT NOT NULL CHECK (
    setup_state IN ('CONFIRMED', 'PULLBACK', 'NEUTRAL', 'EXTENDED', 'DAMAGED', 'EVENT_RISK', 'INSUFFICIENT')
  ),
  atr_extension_ma20  NUMERIC(8,4),
  dist_ma50_pct       NUMERIC(8,4),
  dist_ma200_pct      NUMERIC(8,4),
  rsi_14              NUMERIC(6,2),
  rel_strength_6m     NUMERIC(8,4),
  is_event_window     BOOLEAN NOT NULL DEFAULT FALSE,
  reason_codes        JSONB DEFAULT '[]'::jsonb,
  shadow_score        NUMERIC(5,2),
  created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(listing_id, snapshot_date)
);

CREATE INDEX IF NOT EXISTS idx_setup_snapshots_listing ON public.setup_snapshots(listing_id, snapshot_date DESC);

-- 2. Risk Snapshots
CREATE TABLE IF NOT EXISTS public.risk_snapshots (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  listing_id          UUID NOT NULL REFERENCES public.listings(listing_id) ON DELETE CASCADE,
  snapshot_date       DATE NOT NULL,
  risk_state          TEXT NOT NULL CHECK (
    risk_state IN ('LOW', 'MEDIUM', 'HIGH', 'VERY_HIGH', 'EVENT', 'INSUFFICIENT')
  ),
  fundamental_uncertainty TEXT DEFAULT 'LOW',
  balance_sheet_risk  TEXT DEFAULT 'LOW',
  volatility_grade    TEXT DEFAULT 'MEDIUM',
  liquidity_grade     TEXT NOT NULL CHECK (liquidity_grade IN ('A', 'B', 'C', 'D', 'E', 'F')),
  event_risk          TEXT DEFAULT 'LOW',
  data_grade          TEXT NOT NULL CHECK (data_grade IN ('A', 'B', 'C', 'D', 'E', 'F')),
  dominant_risk       TEXT,
  risk_flags          JSONB DEFAULT '[]'::jsonb,
  created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(listing_id, snapshot_date)
);

CREATE INDEX IF NOT EXISTS idx_risk_snapshots_listing ON public.risk_snapshots(listing_id, snapshot_date DESC);

-- RLS
ALTER TABLE public.setup_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.risk_snapshots ENABLE ROW LEVEL SECURITY;

CREATE POLICY "setup_snapshots_read" ON public.setup_snapshots FOR SELECT TO anon, authenticated USING (true);
CREATE POLICY "risk_snapshots_read" ON public.risk_snapshots FOR SELECT TO anon, authenticated USING (true);

CREATE POLICY "setup_snapshots_service" ON public.setup_snapshots FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "risk_snapshots_service" ON public.risk_snapshots FOR ALL TO service_role USING (true) WITH CHECK (true);
