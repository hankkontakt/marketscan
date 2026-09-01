-- Security Master v2 Schema (Phase 1)
-- Permanent identity hierarchy: issuers -> securities -> listings + temporal ticker_history + corporate_actions

-- 1. Issuers (permanent economic company identity)
CREATE TABLE IF NOT EXISTS public.issuers (
  issuer_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  legal_name      TEXT NOT NULL,
  country         TEXT NOT NULL,
  sector          TEXT,
  industry        TEXT,
  lei             TEXT,
  cik             TEXT,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2. Securities (share/instrument identity)
CREATE TABLE IF NOT EXISTS public.securities (
  security_id     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  issuer_id       UUID NOT NULL REFERENCES public.issuers(issuer_id) ON DELETE CASCADE,
  isin            TEXT,
  figi            TEXT,
  share_class     TEXT DEFAULT 'Common',
  is_primary      BOOLEAN NOT NULL DEFAULT TRUE,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_securities_issuer_id ON public.securities(issuer_id);
CREATE INDEX IF NOT EXISTS idx_securities_isin ON public.securities(isin);

-- 3. Listings (exchange-specific trading venue listing)
CREATE TABLE IF NOT EXISTS public.listings (
  listing_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  security_id     UUID NOT NULL REFERENCES public.securities(security_id) ON DELETE CASCADE,
  mic             TEXT NOT NULL,               -- Exchange MIC code (e.g. XSTO, XNYS, XNAS, XETR)
  ticker          TEXT NOT NULL,               -- Current trading ticker symbol
  currency        TEXT NOT NULL,               -- Trading currency (SEK, USD, EUR, etc.)
  state           TEXT NOT NULL DEFAULT 'ACTIVE' CHECK (
    state IN ('ACTIVE', 'HALTED', 'SUSPENDED', 'ACQUISITION_PENDING', 'DELISTING_PENDING', 'MERGED', 'DELISTED', 'BANKRUPT', 'UNKNOWN')
  ),
  is_primary_listing BOOLEAN NOT NULL DEFAULT TRUE,
  valid_from      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  valid_to        TIMESTAMPTZ,
  verified_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(mic, ticker, valid_from)
);

CREATE INDEX IF NOT EXISTS idx_listings_security_id ON public.listings(security_id);
CREATE INDEX IF NOT EXISTS idx_listings_ticker ON public.listings(ticker);
CREATE INDEX IF NOT EXISTS idx_listings_state ON public.listings(state);

-- 4. Ticker History (temporal ticker renames/changes)
CREATE TABLE IF NOT EXISTS public.ticker_history (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  listing_id      UUID NOT NULL REFERENCES public.listings(listing_id) ON DELETE CASCADE,
  old_ticker      TEXT NOT NULL,
  new_ticker      TEXT NOT NULL,
  effective_date  DATE NOT NULL,
  valid_from      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  valid_to        TIMESTAMPTZ,
  notes           TEXT
);

CREATE INDEX IF NOT EXISTS idx_ticker_history_listing_id ON public.ticker_history(listing_id);

-- 5. Corporate Actions (M&A, delisting, bankruptcy, spin-offs, stock splits)
CREATE TABLE IF NOT EXISTS public.corporate_actions (
  id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  security_id           UUID NOT NULL REFERENCES public.securities(security_id) ON DELETE CASCADE,
  listing_id            UUID REFERENCES public.listings(listing_id) ON DELETE SET NULL,
  action_type           TEXT NOT NULL CHECK (
    action_type IN ('MERGER_ACQUISITION', 'DELISTING', 'BANKRUPTCY', 'SPINOFF', 'SPLIT', 'REVERSE_SPLIT', 'TICKER_CHANGE', 'OTHER')
  ),
  effective_date        DATE NOT NULL,
  deal_terms            JSONB DEFAULT '{}'::jsonb,
  successor_security_id UUID REFERENCES public.securities(security_id) ON DELETE SET NULL,
  source                TEXT,
  verified_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_corporate_actions_security ON public.corporate_actions(security_id);
CREATE INDEX IF NOT EXISTS idx_corporate_actions_date ON public.corporate_actions(effective_date);

-- RLS for Security Master
ALTER TABLE public.issuers ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.securities ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.listings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ticker_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.corporate_actions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "issuers_read" ON public.issuers FOR SELECT TO anon, authenticated USING (true);
CREATE POLICY "securities_read" ON public.securities FOR SELECT TO anon, authenticated USING (true);
CREATE POLICY "listings_read" ON public.listings FOR SELECT TO anon, authenticated USING (true);
CREATE POLICY "ticker_history_read" ON public.ticker_history FOR SELECT TO anon, authenticated USING (true);
CREATE POLICY "corporate_actions_read" ON public.corporate_actions FOR SELECT TO anon, authenticated USING (true);

CREATE POLICY "issuers_service" ON public.issuers FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "securities_service" ON public.securities FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "listings_service" ON public.listings FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "ticker_history_service" ON public.ticker_history FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "corporate_actions_service" ON public.corporate_actions FOR ALL TO service_role USING (true) WITH CHECK (true);
