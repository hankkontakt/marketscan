-- MarketScan Ultimate Rebuild v3 — FX rates with as-of dates.
--
-- Phase 4: FX normalization must come from a real source with explicit dates,
-- never from a static conversion table (the bug class behind the market-cap
-- disasters, migrations 059-061). This table is the single source for
-- currency -> SEK conversions. Seed = ECB eurofxref reference rates
-- (https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml) published
-- 2026-09-01; the seed is a snapshot, not a live feed — a scheduled refresh
-- job must append new rate dates.

CREATE TABLE IF NOT EXISTS public.fx_rates (
    base_currency char(3) NOT NULL DEFAULT 'SEK' CHECK (base_currency = 'SEK'),
    quote_currency char(3) NOT NULL,
    rate numeric NOT NULL CHECK (rate > 0),
    rate_date date NOT NULL,
    source text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (base_currency, quote_currency, rate_date)
);
CREATE INDEX IF NOT EXISTS fx_rates_lookup_idx
    ON public.fx_rates (base_currency, quote_currency, rate_date DESC);

-- ECB reference rates 2026-09-01, converted to SEK per 1 unit of quote
-- currency (EUR/SEK 11.1145 divided by each EUR cross).
INSERT INTO public.fx_rates (base_currency, quote_currency, rate, rate_date, source) VALUES
    ('SEK', 'SEK', 1.00000,   '2026-09-01', 'ecb-eurofxref-2026-09-01'),
    ('SEK', 'USD', 9.58973,   '2026-09-01', 'ecb-eurofxref-2026-09-01'),
    ('SEK', 'EUR', 11.11450,  '2026-09-01', 'ecb-eurofxref-2026-09-01'),
    ('SEK', 'NOK', 1.02736,   '2026-09-01', 'ecb-eurofxref-2026-09-01'),
    ('SEK', 'DKK', 1.48693,   '2026-09-01', 'ecb-eurofxref-2026-09-01'),
    ('SEK', 'GBP', 12.97609,  '2026-09-01', 'ecb-eurofxref-2026-09-01'),
    ('SEK', 'JPY', 0.0598741, '2026-09-01', 'ecb-eurofxref-2026-09-01'),
    ('SEK', 'PLN', 2.56614,   '2026-09-01', 'ecb-eurofxref-2026-09-01'),
    ('SEK', 'CAD', 6.90501,   '2026-09-01', 'ecb-eurofxref-2026-09-01'),
    ('SEK', 'AUD', 6.84812,   '2026-09-01', 'ecb-eurofxref-2026-09-01')
ON CONFLICT (base_currency, quote_currency, rate_date) DO NOTHING;

ALTER TABLE public.fx_rates ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.fx_rates FROM anon, authenticated;
GRANT ALL ON public.fx_rates TO service_role;
GRANT SELECT ON public.fx_rates TO anon, authenticated;
DROP POLICY IF EXISTS "fx rates are readable" ON public.fx_rates;
CREATE POLICY "fx rates are readable" ON public.fx_rates
    FOR SELECT TO anon, authenticated USING (true);