-- MarketScan Ultimate Rebuild v3 — canonical decision-data foundation.
--
-- This migration is intentionally append-only: legacy scan_results remains a
-- compatibility source until a published V3 snapshot has been verified.
-- Run against staging first. Do not apply to production until its migration
-- ledger has been checked and the numeric prefix is still the next one.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Phase 1 governance: these two existing public tables were the production
-- Security Advisor's ERROR-level findings. Keep market rows publicly readable,
-- but make all writes service-only; pipeline telemetry is admin/service-only.
ALTER TABLE IF EXISTS public.scan_results ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "scan_results_public_read" ON public.scan_results;
CREATE POLICY "scan_results_public_read" ON public.scan_results
    FOR SELECT TO anon, authenticated USING (true);
DROP POLICY IF EXISTS "scan_results_service_write" ON public.scan_results;
CREATE POLICY "scan_results_service_write" ON public.scan_results
    FOR ALL TO service_role USING (true) WITH CHECK (true);
GRANT SELECT ON public.scan_results TO anon, authenticated;

ALTER TABLE IF EXISTS public.pipeline_runs ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "pipeline_runs_admin_read" ON public.pipeline_runs;
CREATE POLICY "pipeline_runs_admin_read" ON public.pipeline_runs
    FOR SELECT TO authenticated
    USING (EXISTS (
        SELECT 1 FROM public.profiles
        WHERE profiles.id = (select auth.uid()) AND profiles.role = 'admin'
    ));
DROP POLICY IF EXISTS "pipeline_runs_service_all" ON public.pipeline_runs;
CREATE POLICY "pipeline_runs_service_all" ON public.pipeline_runs
    FOR ALL TO service_role USING (true) WITH CHECK (true);

CREATE OR REPLACE FUNCTION public.clean_ai_cache()
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
BEGIN
    DELETE FROM public.ai_cache WHERE created_at < now() - interval '7 days';
END;
$$;
REVOKE ALL ON FUNCTION public.clean_ai_cache() FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.clean_ai_cache() TO service_role;

CREATE TABLE IF NOT EXISTS public.issuers (
    issuer_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    legal_name text NOT NULL,
    domicile_country char(2),
    lei text UNIQUE,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.securities (
    security_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    issuer_id uuid NOT NULL REFERENCES public.issuers(issuer_id),
    isin text UNIQUE,
    figi text,
    share_class text NOT NULL DEFAULT 'COMMON',
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.listings (
    listing_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    security_id uuid NOT NULL REFERENCES public.securities(security_id),
    mic text NOT NULL,
    ticker text NOT NULL,
    currency char(3) NOT NULL,
    state text NOT NULL DEFAULT 'UNKNOWN'
        CHECK (state IN ('ACTIVE', 'ACQUISITION_PENDING', 'MERGED', 'DELISTING_PENDING', 'DELISTED', 'HALTED', 'SUSPENDED', 'BANKRUPT', 'UNKNOWN')),
    valid_from timestamptz NOT NULL DEFAULT now(),
    valid_to timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    CHECK (valid_to IS NULL OR valid_to > valid_from)
);

CREATE UNIQUE INDEX IF NOT EXISTS listings_active_mic_ticker_idx
    ON public.listings (mic, upper(ticker)) WHERE valid_to IS NULL;

CREATE TABLE IF NOT EXISTS public.ticker_aliases (
    alias_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    listing_id uuid NOT NULL REFERENCES public.listings(listing_id),
    ticker text NOT NULL,
    mic text NOT NULL,
    valid_from timestamptz NOT NULL,
    valid_to timestamptz,
    source_id text NOT NULL,
    CHECK (valid_to IS NULL OR valid_to > valid_from)
);

CREATE TABLE IF NOT EXISTS public.metric_catalog (
    metric_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    metric_code text NOT NULL UNIQUE,
    canonical_unit text NOT NULL,
    value_kind text NOT NULL CHECK (value_kind IN ('numeric', 'text', 'boolean')),
    definition text NOT NULL,
    period_basis text,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.raw_payloads (
    raw_payload_hash text PRIMARY KEY,
    source_id text NOT NULL,
    fetched_at timestamptz NOT NULL,
    payload_location text NOT NULL,
    vendor_schema_version text,
    request_metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.observations_v3 (
    observation_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    listing_id uuid NOT NULL REFERENCES public.listings(listing_id),
    metric_id uuid NOT NULL REFERENCES public.metric_catalog(metric_id),
    value_numeric numeric,
    value_text text,
    value_boolean boolean,
    canonical_unit text NOT NULL,
    source_value text,
    source_unit text,
    currency char(3),
    period_start date,
    period_end date,
    valid_from timestamptz,
    valid_to timestamptz,
    available_at timestamptz NOT NULL,
    fetched_at timestamptz NOT NULL,
    known_to timestamptz,
    source_id text NOT NULL,
    source_tier text NOT NULL CHECK (source_tier IN ('A', 'B', 'C', 'D')),
    raw_payload_hash text REFERENCES public.raw_payloads(raw_payload_hash),
    transform_version text NOT NULL,
    quality_flags text[] NOT NULL DEFAULT '{}',
    supersedes_observation_id uuid REFERENCES public.observations_v3(observation_id),
    created_at timestamptz NOT NULL DEFAULT now(),
    CHECK (available_at <= fetched_at),
    CHECK (num_nonnulls(value_numeric, value_text, value_boolean) = 1)
);
CREATE INDEX IF NOT EXISTS observations_v3_pit_idx
    ON public.observations_v3 (listing_id, metric_id, available_at DESC);

CREATE TABLE IF NOT EXISTS public.observation_quarantine (
    quarantine_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    observation_id uuid REFERENCES public.observations_v3(observation_id),
    pipeline_run_id uuid,
    reason_code text NOT NULL,
    detail text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    resolved_at timestamptz
);

CREATE TABLE IF NOT EXISTS public.decision_snapshots (
    decision_snapshot_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    publication_run_id uuid NOT NULL,
    data_snapshot_id uuid NOT NULL,
    master_model_version text NOT NULL,
    code_sha text NOT NULL,
    external_dependency_shas jsonb NOT NULL DEFAULT '{}'::jsonb,
    status text NOT NULL DEFAULT 'STAGED' CHECK (status IN ('STAGED', 'PUBLISHED', 'FAILED', 'SUPERSEDED')),
    quality_report jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    published_at timestamptz
);

CREATE TABLE IF NOT EXISTS public.decision_manifests (
    decision_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    decision_snapshot_id uuid NOT NULL REFERENCES public.decision_snapshots(decision_snapshot_id),
    listing_id uuid NOT NULL REFERENCES public.listings(listing_id),
    decision_time timestamptz NOT NULL,
    master_rank_score numeric,
    thesis_band text NOT NULL,
    segment_percentile numeric,
    setup_vector jsonb NOT NULL DEFAULT '{}'::jsonb,
    setup_state text NOT NULL,
    risk_vector jsonb NOT NULL DEFAULT '{}'::jsonb,
    risk_state text NOT NULL,
    is_actionable boolean NOT NULL DEFAULT false,
    data_grade text NOT NULL,
    coverage numeric NOT NULL CHECK (coverage >= 0 AND coverage <= 1),
    stale_critical_count integer NOT NULL DEFAULT 0 CHECK (stale_critical_count >= 0),
    street_context jsonb NOT NULL DEFAULT '{}'::jsonb,
    positive_drivers jsonb NOT NULL DEFAULT '[]'::jsonb,
    negative_drivers jsonb NOT NULL DEFAULT '[]'::jsonb,
    warnings jsonb NOT NULL DEFAULT '[]'::jsonb,
    factor_snapshot_ids uuid[] NOT NULL DEFAULT '{}',
    model_versions jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (decision_snapshot_id, listing_id),
    CHECK (NOT is_actionable OR setup_state <> 'INSUFFICIENT')
);
CREATE INDEX IF NOT EXISTS decision_manifests_snapshot_rank_idx
    ON public.decision_manifests (decision_snapshot_id, master_rank_score DESC NULLS LAST);

CREATE TABLE IF NOT EXISTS public.decision_evidence (
    decision_id uuid NOT NULL REFERENCES public.decision_manifests(decision_id),
    observation_id uuid NOT NULL REFERENCES public.observations_v3(observation_id),
    role text NOT NULL CHECK (role IN ('INPUT', 'DRIVER', 'WARNING', 'CONTRADICTION')),
    PRIMARY KEY (decision_id, observation_id)
);

CREATE TABLE IF NOT EXISTS public.publication_state (
    singleton boolean PRIMARY KEY DEFAULT true CHECK (singleton),
    current_decision_snapshot_id uuid REFERENCES public.decision_snapshots(decision_snapshot_id),
    updated_at timestamptz NOT NULL DEFAULT now()
);
INSERT INTO public.publication_state (singleton) VALUES (true) ON CONFLICT (singleton) DO NOTHING;

-- The single state transition is transactional. Only service_role retains EXECUTE.
CREATE OR REPLACE FUNCTION public.publish_decision_snapshot(p_snapshot_id uuid)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
DECLARE
    staged_count integer;
BEGIN
    SELECT count(*) INTO staged_count
    FROM public.decision_manifests
    WHERE decision_snapshot_id = p_snapshot_id;
    IF staged_count = 0 THEN
        RAISE EXCEPTION 'Cannot publish empty decision snapshot %', p_snapshot_id;
    END IF;

    IF EXISTS (
        SELECT 1 FROM public.decision_manifests d
        JOIN public.listings l ON l.listing_id = d.listing_id
        WHERE d.decision_snapshot_id = p_snapshot_id
          AND d.is_actionable
          AND l.state <> 'ACTIVE'
    ) THEN
        RAISE EXCEPTION 'Cannot publish actionable decisions for inactive listings';
    END IF;

    UPDATE public.decision_snapshots
       SET status = 'SUPERSEDED'
     WHERE status = 'PUBLISHED' AND decision_snapshot_id <> p_snapshot_id;
    UPDATE public.decision_snapshots
       SET status = 'PUBLISHED', published_at = now()
     WHERE decision_snapshot_id = p_snapshot_id AND status = 'STAGED';
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Snapshot % is not staged', p_snapshot_id;
    END IF;
    UPDATE public.publication_state
       SET current_decision_snapshot_id = p_snapshot_id, updated_at = now()
     WHERE singleton;
END;
$$;

REVOKE ALL ON FUNCTION public.publish_decision_snapshot(uuid) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.publish_decision_snapshot(uuid) TO service_role;

-- All writes remain service-only. Public consumers can only read published data.
ALTER TABLE public.issuers ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.securities ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.listings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ticker_aliases ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.metric_catalog ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.raw_payloads ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.observations_v3 ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.observation_quarantine ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.decision_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.decision_manifests ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.decision_evidence ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.publication_state ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON public.issuers, public.securities, public.listings, public.ticker_aliases,
    public.metric_catalog, public.raw_payloads, public.observations_v3,
    public.observation_quarantine, public.decision_snapshots, public.decision_manifests,
    public.decision_evidence, public.publication_state FROM anon, authenticated;
GRANT ALL ON public.issuers, public.securities, public.listings, public.ticker_aliases,
    public.metric_catalog, public.raw_payloads, public.observations_v3,
    public.observation_quarantine, public.decision_snapshots, public.decision_manifests,
    public.decision_evidence, public.publication_state TO service_role;
GRANT SELECT ON public.listings, public.decision_snapshots, public.decision_manifests,
    public.decision_evidence, public.observations_v3, public.metric_catalog,
    public.publication_state TO anon, authenticated;

CREATE POLICY "published listings are readable" ON public.listings FOR SELECT TO anon, authenticated USING (true);
CREATE POLICY "published snapshots are readable" ON public.decision_snapshots FOR SELECT TO anon, authenticated USING (status = 'PUBLISHED');
CREATE POLICY "published manifests are readable" ON public.decision_manifests FOR SELECT TO anon, authenticated USING (
    EXISTS (SELECT 1 FROM public.decision_snapshots s WHERE s.decision_snapshot_id = decision_manifests.decision_snapshot_id AND s.status = 'PUBLISHED')
);
CREATE POLICY "published evidence is readable" ON public.decision_evidence FOR SELECT TO anon, authenticated USING (
    EXISTS (SELECT 1 FROM public.decision_manifests d JOIN public.decision_snapshots s ON s.decision_snapshot_id = d.decision_snapshot_id WHERE d.decision_id = decision_evidence.decision_id AND s.status = 'PUBLISHED')
);
CREATE POLICY "evidence observations are readable" ON public.observations_v3 FOR SELECT TO anon, authenticated USING (
    EXISTS (SELECT 1 FROM public.decision_evidence e JOIN public.decision_manifests d ON d.decision_id = e.decision_id JOIN public.decision_snapshots s ON s.decision_snapshot_id = d.decision_snapshot_id WHERE e.observation_id = observations_v3.observation_id AND s.status = 'PUBLISHED')
);
CREATE POLICY "metric definitions are readable" ON public.metric_catalog FOR SELECT TO anon, authenticated USING (true);
CREATE POLICY "publication pointer is readable" ON public.publication_state FOR SELECT TO anon, authenticated USING (true);

CREATE OR REPLACE VIEW public.current_decisions_v3 WITH (security_invoker = true) AS
SELECT d.decision_id, d.decision_snapshot_id, d.listing_id, l.ticker, l.mic,
       l.currency, l.state AS tradability_state, d.decision_time,
       d.master_rank_score, d.thesis_band, d.segment_percentile, d.setup_vector,
       d.setup_state, d.risk_vector, d.risk_state, d.is_actionable, d.data_grade,
       d.coverage, d.stale_critical_count, d.street_context, d.positive_drivers,
       d.negative_drivers, d.warnings, d.model_versions, s.published_at
FROM public.decision_manifests d
JOIN public.listings l ON l.listing_id = d.listing_id
JOIN public.decision_snapshots s ON s.decision_snapshot_id = d.decision_snapshot_id
JOIN public.publication_state p ON p.current_decision_snapshot_id = d.decision_snapshot_id
WHERE s.status = 'PUBLISHED';
GRANT SELECT ON public.current_decisions_v3 TO anon, authenticated;
