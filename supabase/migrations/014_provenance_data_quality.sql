-- Provenance & Data Quality Schema (Phase 2)
-- Tables for source tracking, data snapshots, factor provenance and quality monitoring

-- 1. Source Registry
CREATE TABLE IF NOT EXISTS public.source_registry (
  source_id       TEXT PRIMARY KEY,
  name            TEXT NOT NULL,
  source_tier     TEXT NOT NULL CHECK (source_tier IN ('A', 'B', 'C', 'D')),
  provider_type   TEXT NOT NULL,               -- 'official', 'licensed', 'aggregator', 'ai_extraction'
  update_cadence  TEXT NOT NULL,               -- 'realtime', 'eod', 'daily', 'quarterly', 'event_driven'
  sla_max_delay_h INTEGER DEFAULT 24,
  is_active       BOOLEAN NOT NULL DEFAULT TRUE,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Seed standard sources
INSERT INTO public.source_registry (source_id, name, source_tier, provider_type, update_cadence, sla_max_delay_h)
VALUES
  ('EXCHANGE_OFFICIAL', 'Exchange / Official Filings', 'A', 'official', 'event_driven', 1),
  ('BORSDATA_API', 'Börsdata Financial API', 'B', 'licensed', 'daily', 12),
  ('EODHD_API', 'EODHD Fundamentals API', 'B', 'licensed', 'daily', 12),
  ('FINNHUB_API', 'Finnhub Market Data', 'C', 'aggregator', 'eod', 6),
  ('YFINANCE_BACKUP', 'Yahoo Finance Aggregator', 'C', 'aggregator', 'eod', 24),
  ('AI_DOCUMENT_RAG', 'AI Document Extraction RAG', 'D', 'ai_extraction', 'event_driven', 48)
ON CONFLICT (source_id) DO NOTHING;

-- 2. Data Snapshots (immutable ingestion batch metadata)
CREATE TABLE IF NOT EXISTS public.data_snapshots (
  snapshot_id     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source_id       TEXT NOT NULL REFERENCES public.source_registry(source_id),
  batch_type      TEXT NOT NULL,               -- 'prices_eod', 'fundamentals', 'analysts', 'events'
  row_count       INTEGER NOT NULL DEFAULT 0,
  as_of_date      DATE NOT NULL,
  fetched_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  quality_summary JSONB DEFAULT '{}'::jsonb,
  storage_uri     TEXT
);

CREATE INDEX IF NOT EXISTS idx_data_snapshots_date ON public.data_snapshots(as_of_date);

-- 3. Data Quality Runs (coverage, freshness, anomaly monitoring)
CREATE TABLE IF NOT EXISTS public.data_quality_runs (
  run_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  snapshot_id     UUID REFERENCES public.data_snapshots(snapshot_id) ON DELETE SET NULL,
  evaluated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  total_listings  INTEGER NOT NULL,
  price_coverage_pct NUMERIC(5,2),
  fundamentals_coverage_pct NUMERIC(5,2),
  analyst_coverage_pct NUMERIC(5,2),
  liquidity_coverage_pct NUMERIC(5,2),
  stale_count     INTEGER DEFAULT 0,
  anomaly_count   INTEGER DEFAULT 0,
  details         JSONB DEFAULT '{}'::jsonb
);

-- RLS
ALTER TABLE public.source_registry ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.data_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.data_quality_runs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "source_registry_read" ON public.source_registry FOR SELECT TO anon, authenticated USING (true);
CREATE POLICY "data_snapshots_read" ON public.data_snapshots FOR SELECT TO anon, authenticated USING (true);
CREATE POLICY "data_quality_runs_read" ON public.data_quality_runs FOR SELECT TO anon, authenticated USING (true);

CREATE POLICY "source_registry_service" ON public.source_registry FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "data_snapshots_service" ON public.data_snapshots FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "data_quality_runs_service" ON public.data_quality_runs FOR ALL TO service_role USING (true) WITH CHECK (true);
