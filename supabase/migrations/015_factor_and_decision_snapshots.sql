-- MasterRank v2 Factor & Decision Snapshots Schema (Phase 3)
-- Versioned models, immutable factor snapshots and canonical decision snapshots

-- 1. Model Versions Registry
CREATE TABLE IF NOT EXISTS public.model_versions (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  model_name          TEXT NOT NULL,
  version             TEXT NOT NULL,
  status              TEXT NOT NULL CHECK (status IN ('shadow', 'challenger', 'champion', 'retired')),
  code_sha            TEXT NOT NULL,
  feature_schema_hash TEXT NOT NULL,
  training_cutoff     TIMESTAMPTZ,
  description         TEXT,
  created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(model_name, version)
);

-- Seed initial champion and challenger models
INSERT INTO public.model_versions (id, model_name, version, status, code_sha, feature_schema_hash, description)
VALUES
  ('11111111-1111-1111-1111-111111111111', 'MasterRank', 'master_v1.0', 'champion', 'legacy_v1_head', 'hash_v1_8blocks', 'Legacy MasterRank 8-block factor model'),
  ('22222222-2222-2222-2222-222222222222', 'MasterRank', 'master_v2.0', 'challenger', 'v2_structural_priors', 'hash_v2_7blocks', 'MasterRank v2 7-block reliability-weighted model'),
  ('33333333-3333-3333-3333-333333333333', 'SetupEngine', 'setup_v1.0', 'shadow', 'setup_state_machine_v1', 'hash_setup_v1', 'Deterministic SetupState machine'),
  ('44444444-4444-4444-4444-444444444444', 'RiskEngine', 'risk_v1.0', 'champion', 'risk_state_v1', 'hash_risk_v1', 'Multidimensional Risk & Liquidity Engine')
ON CONFLICT (model_name, version) DO NOTHING;

-- 2. Factor Snapshots (immutable per-factor scores, reliabilities, and provenance)
CREATE TABLE IF NOT EXISTS public.factor_snapshots (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  listing_id          UUID NOT NULL REFERENCES public.listings(listing_id) ON DELETE CASCADE,
  snapshot_at         TIMESTAMPTZ NOT NULL,
  model_version_id    UUID NOT NULL REFERENCES public.model_versions(id),
  quality_score       NUMERIC(5,2),
  quality_rel         NUMERIC(4,3),
  growth_score        NUMERIC(5,2),
  growth_rel          NUMERIC(4,3),
  valuation_score     NUMERIC(5,2),
  valuation_rel       NUMERIC(4,3),
  momentum_score      NUMERIC(5,2),
  momentum_rel        NUMERIC(4,3),
  revisions_score     NUMERIC(5,2),
  revisions_rel       NUMERIC(4,3),
  capital_alloc_score NUMERIC(5,2),
  capital_alloc_rel   NUMERIC(4,3),
  catalyst_score      NUMERIC(5,2),
  catalyst_rel        NUMERIC(4,3),
  raw_factors         JSONB DEFAULT '{}'::jsonb,
  created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(listing_id, snapshot_at, model_version_id)
);

CREATE INDEX IF NOT EXISTS idx_factor_snapshots_listing ON public.factor_snapshots(listing_id, snapshot_at DESC);

-- 3. Canonical Decision Snapshots (single server source of truth for all surfaces)
CREATE TABLE IF NOT EXISTS public.decision_snapshots (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  listing_id          UUID NOT NULL REFERENCES public.listings(listing_id) ON DELETE CASCADE,
  snapshot_at         TIMESTAMPTZ NOT NULL,
  master_rank         NUMERIC(5,2),
  thesis_band         TEXT CHECK (thesis_band IN ('EXCEPTIONAL', 'STRONG', 'POSITIVE', 'MIXED', 'WEAK', 'INSUFFICIENT')),
  segment_percentile  NUMERIC(5,2),
  setup_state         TEXT CHECK (setup_state IN ('CONFIRMED', 'PULLBACK', 'NEUTRAL', 'EXTENDED', 'DAMAGED', 'EVENT_RISK', 'INSUFFICIENT')),
  risk_state          TEXT CHECK (risk_state IN ('LOW', 'MEDIUM', 'HIGH', 'VERY_HIGH', 'EVENT', 'INSUFFICIENT')),
  data_grade          TEXT CHECK (data_grade IN ('A', 'B', 'C', 'D', 'E', 'F')),
  weighted_coverage   NUMERIC(4,3),
  master_model_version UUID NOT NULL REFERENCES public.model_versions(id),
  setup_model_version  UUID REFERENCES public.model_versions(id),
  risk_model_version   UUID REFERENCES public.model_versions(id),
  positive_drivers    JSONB DEFAULT '[]'::jsonb,
  negative_drivers    JSONB DEFAULT '[]'::jsonb,
  warnings            JSONB DEFAULT '[]'::jsonb,
  created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(listing_id, snapshot_at, master_model_version)
);

CREATE INDEX IF NOT EXISTS idx_decision_snapshots_lookup ON public.decision_snapshots(listing_id, snapshot_at DESC);

-- RLS
ALTER TABLE public.model_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.factor_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.decision_snapshots ENABLE ROW LEVEL SECURITY;

CREATE POLICY "model_versions_read" ON public.model_versions FOR SELECT TO anon, authenticated USING (true);
CREATE POLICY "factor_snapshots_read" ON public.factor_snapshots FOR SELECT TO anon, authenticated USING (true);
CREATE POLICY "decision_snapshots_read" ON public.decision_snapshots FOR SELECT TO anon, authenticated USING (true);

CREATE POLICY "model_versions_service" ON public.model_versions FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "factor_snapshots_service" ON public.factor_snapshots FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "decision_snapshots_service" ON public.decision_snapshots FOR ALL TO service_role USING (true) WITH CHECK (true);
