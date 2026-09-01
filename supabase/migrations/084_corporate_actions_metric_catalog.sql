-- MarketScan Ultimate Rebuild v3 — corporate actions + canonical metric contracts.
--
-- Phase 2/3 foundation: an authoritative corporate-action layer feeds listing
-- tradability state, and the Metric Catalog pins every model input to one
-- canonical unit so "column name matches model input" is never a data contract.
--
-- Append-only and idempotent. Run against staging first; never apply to
-- production before its migration ledger has been rechecked.

-- ---------------------------------------------------------------------------
-- 1. Corporate actions (plan section 6 + entity contract in table 10)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.corporate_actions (
    action_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    listing_id uuid REFERENCES public.listings(listing_id),
    ticker text NOT NULL,
    mic text NOT NULL,
    action_type text NOT NULL CHECK (action_type IN (
        'ACQUISITION_PENDING', 'MERGED', 'DELISTING_PENDING', 'DELISTED',
        'HALTED', 'SUSPENDED', 'BANKRUPT', 'SYMBOL_CHANGE', 'SPLIT', 'SPINOFF'
    )),
    announced_at timestamptz,
    known_at timestamptz NOT NULL,
    effective_at timestamptz,
    status text NOT NULL DEFAULT 'ANNOUNCED' CHECK (status IN ('ANNOUNCED', 'EFFECTIVE', 'CANCELLED')),
    source_id text NOT NULL,
    source_url text,
    detail jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS corporate_actions_resolution_idx
    ON public.corporate_actions (mic, upper(ticker), status);
CREATE INDEX IF NOT EXISTS corporate_actions_listing_idx
    ON public.corporate_actions (listing_id);

-- CPRX — Catalyst Pharmaceuticals, acquired by Angelini Pharma.
-- Merger agreement dated 2026-05-06 (8-K filed 2026-05-07); merger closed
-- 2026-07-15 at USD 31.50 per share in cash; Nasdaq trading suspended
-- 2026-07-16 and Form 25 delisting requested. Sources: Angelini Pharma press
-- release (2026-07-16) and Catalyst 8-K (2026-07-15).
INSERT INTO public.corporate_actions (
    ticker, mic, action_type, announced_at, known_at, effective_at, status,
    source_id, source_url, detail
) VALUES (
    'CPRX', 'XNAS', 'MERGED',
    '2026-05-06T00:00:00Z', '2026-05-07T00:00:00Z', '2026-07-15T00:00:00Z',
    'EFFECTIVE',
    'angelini-press-release-2026-07-16',
    'https://www.angelinipharma.com/news-media/press-releases/angelini-pharma-completes-acquisition-of-catalyst-pharmaceuticals/',
    '{"acquirer": "Angelini Pharma (via Angelini Cielo Inc.)",
      "consideration_usd_per_share": 31.50,
      "total_equity_value_usd": 4100000000,
      "trading_suspension_date": "2026-07-16",
      "filing": "SEC Form 8-K 2026-07-15"}'
)
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- 2. Apply effective corporate actions to listing tradability state.
--    service_role-only; transactional; no-op when the listing is not active.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.apply_effective_corporate_actions()
RETURNS TABLE (ticker text, mic text, previous_state text, new_state text)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
DECLARE
    r RECORD;
BEGIN
    FOR r IN
        SELECT ca.ticker, ca.mic, ca.action_type, ca.effective_at,
               l.listing_id, l.state AS current_state
        FROM public.corporate_actions ca
        LEFT JOIN public.listings l
          ON upper(l.ticker) = upper(ca.ticker)
         AND l.mic = ca.mic
         AND l.valid_to IS NULL
        WHERE ca.status = 'EFFECTIVE'
          AND (ca.effective_at IS NULL OR ca.effective_at <= now())
    LOOP
        IF r.listing_id IS NULL OR r.current_state = r.action_type THEN
            CONTINUE;
        END IF;
        UPDATE public.listings
           SET state = r.action_type,
               valid_to = COALESCE(r.effective_at, valid_to)
         WHERE listing_id = r.listing_id;
        ticker := r.ticker;
        mic := r.mic;
        previous_state := r.current_state;
        new_state := r.action_type;
        RETURN NEXT;
    END LOOP;
END;
$$;

REVOKE ALL ON FUNCTION public.apply_effective_corporate_actions() FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.apply_effective_corporate_actions() TO service_role;

-- ---------------------------------------------------------------------------
-- 3. Metric Catalog — canonical unit contracts (plan section 8).
--    One canonical definition per metric, independent of provider formatting.
-- ---------------------------------------------------------------------------
INSERT INTO public.metric_catalog (metric_code, canonical_unit, value_kind, definition, period_basis) VALUES
    ('debt_to_equity_ratio', 'ratio', 'numeric',
     'Total debt / total shareholder equity as a ratio where 1.0 = 100%. NOT percentage points. Negative equity is representable and must be flagged, not silently zeroed.',
     'Latest reported balance sheet / LTM'),
    ('roe', 'ratio', 'numeric',
     'Net income / shareholders equity, ratio where 1.0 = 100%.',
     'Latest annual or LTM'),
    ('roa', 'ratio', 'numeric',
     'Net income / total assets, ratio where 1.0 = 100%.',
     'Latest annual or LTM'),
    ('gross_margin', 'ratio', 'numeric',
     'Gross profit / revenue, ratio where 1.0 = 100%.',
     'Latest annual or LTM'),
    ('operating_margin', 'ratio', 'numeric',
     'Operating income / revenue, ratio where 1.0 = 100%.',
     'Latest annual or LTM'),
    ('revenue_growth_rate', 'annualized_decimal', 'numeric',
     'Year-over-year revenue growth as an annualized decimal (0.12 = +12%).',
     'Latest fiscal year / TTM'),
    ('earnings_growth_rate', 'annualized_decimal', 'numeric',
     'Year-over-year earnings growth as an annualized decimal (0.12 = +12%).',
     'Latest fiscal year / TTM'),
    ('dividend_yield', 'annualized_decimal', 'numeric',
     'Trailing 12-month dividends per share / price, annualized decimal (0.03 = 3%).',
     'TTM / spot'),
    ('pe_trailing', 'ratio', 'numeric',
     'Price / trailing EPS (negative EPS must be flagged, never zeroed).',
     'TTM'),
    ('pe_forward', 'ratio', 'numeric',
     'Price / forward consensus EPS (dated consensus snapshot required).',
     'Next fiscal year consensus'),
    ('fcf_yield', 'annualized_decimal', 'numeric',
     'Free cash flow / market cap, annualized decimal (0.05 = 5%).',
     'TTM / spot'),
    ('price_close', 'native_currency_per_share', 'numeric',
     'Official closing price in listing native currency, split/dividend adjusted per contract.',
     'Market session close'),
    ('market_cap', 'currency', 'numeric',
     'Shares outstanding x price in a single stated currency with fx_rate_id recorded when converted.',
     'Spot'),
    ('volume_20d_avg_shares', 'shares', 'numeric',
     'Average daily traded shares over 20 market sessions (zero-volume sessions excluded per contract).',
     '20 market sessions')
ON CONFLICT (metric_code) DO NOTHING;

-- ---------------------------------------------------------------------------
-- 4. RLS — service-only writes; the public may read effective actions.
-- ---------------------------------------------------------------------------
ALTER TABLE public.corporate_actions ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.corporate_actions FROM anon, authenticated;
GRANT ALL ON public.corporate_actions TO service_role;
GRANT SELECT ON public.corporate_actions TO anon, authenticated;

DROP POLICY IF EXISTS "effective corporate actions are readable" ON public.corporate_actions;
CREATE POLICY "effective corporate actions are readable" ON public.corporate_actions
    FOR SELECT TO anon, authenticated
    USING (status = 'EFFECTIVE');