-- Events & Analyst Revision Engines Schema (Phase 4)
-- Tables for historical analyst revisions and 3-layer event states

-- 1. Analyst Revision Snapshots
CREATE TABLE IF NOT EXISTS public.analyst_revision_snapshots (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  listing_id          UUID NOT NULL REFERENCES public.listings(listing_id) ON DELETE CASCADE,
  snapshot_date       DATE NOT NULL,
  target_mean         NUMERIC(12,4),
  target_high         NUMERIC(12,4),
  target_low          NUMERIC(12,4),
  target_median       NUMERIC(12,4),
  target_std_dev      NUMERIC(12,4),
  target_revision_30d NUMERIC(8,4),
  eps_fy1             NUMERIC(10,4),
  eps_revision_30d    NUMERIC(8,4),
  revenue_fy1         NUMERIC(16,2),
  revenue_revision_30d NUMERIC(8,4),
  up_revisions_count  INTEGER DEFAULT 0,
  down_revisions_count INTEGER DEFAULT 0,
  revision_breadth    NUMERIC(6,4),
  analyst_count       INTEGER DEFAULT 0,
  dispersion_ratio    NUMERIC(6,4),
  source_tier         TEXT DEFAULT 'B',
  created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(listing_id, snapshot_date)
);

CREATE INDEX IF NOT EXISTS idx_analyst_rev_listing ON public.analyst_revision_snapshots(listing_id, snapshot_date DESC);

-- 2. Event States (EventRisk, EventOutcome, MarketResponse)
CREATE TABLE IF NOT EXISTS public.event_states (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  listing_id          UUID NOT NULL REFERENCES public.listings(listing_id) ON DELETE CASCADE,
  event_type          TEXT NOT NULL CHECK (
    event_type IN ('EARNINGS', 'GUIDANCE', 'FDA_REGULATORY', 'DIVIDEND_EX', 'AGM', 'M_AND_A', 'CAPITAL_INCREASE')
  ),
  event_date          DATE NOT NULL,
  is_confirmed        BOOLEAN NOT NULL DEFAULT FALSE,
  days_to_event       INTEGER,
  event_risk_level    TEXT NOT NULL DEFAULT 'LOW' CHECK (event_risk_level IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
  
  -- Outcome (actual vs estimate)
  actual_eps          NUMERIC(10,4),
  estimated_eps       NUMERIC(10,4),
  eps_surprise_pct    NUMERIC(8,4),
  actual_revenue      NUMERIC(16,2),
  estimated_revenue   NUMERIC(16,2),
  revenue_surprise_pct NUMERIC(8,4),
  guidance_summary    TEXT,

  -- Market Response
  gap_pct             NUMERIC(8,4),
  volume_multiple_1d  NUMERIC(8,4),
  excess_return_1d    NUMERIC(8,4),
  excess_return_5d    NUMERIC(8,4),
  market_verdict      TEXT CHECK (market_verdict IN ('POSITIVE', 'NEUTRAL', 'NEGATIVE', 'PENDING')),

  source              TEXT,
  created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(listing_id, event_type, event_date)
);

CREATE INDEX IF NOT EXISTS idx_event_states_listing ON public.event_states(listing_id, event_date DESC);
CREATE INDEX IF NOT EXISTS idx_event_states_date ON public.event_states(event_date);

-- RLS
ALTER TABLE public.analyst_revision_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.event_states ENABLE ROW LEVEL SECURITY;

CREATE POLICY "analyst_rev_read" ON public.analyst_revision_snapshots FOR SELECT TO anon, authenticated USING (true);
CREATE POLICY "event_states_read" ON public.event_states FOR SELECT TO anon, authenticated USING (true);

CREATE POLICY "analyst_rev_service" ON public.analyst_revision_snapshots FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "event_states_service" ON public.event_states FOR ALL TO service_role USING (true) WITH CHECK (true);
