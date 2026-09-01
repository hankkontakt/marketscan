-- MarketScan — Migration 081: Liquidity grade & 20-day median turnover columns
-- Implementerar D5: Likviditetsgrader A–F baserat på segmentens omsättningsgolv.
-- low_liquidity omdefinieras som grade IN ('D', 'E', 'F').

ALTER TABLE scan_results
    ADD COLUMN IF NOT EXISTS liquidity_grade text,
    ADD COLUMN IF NOT EXISTS turnover_20d_median numeric;

-- Grant select to public/authenticated roles
GRANT SELECT ON scan_results TO anon, authenticated;

COMMENT ON COLUMN scan_results.liquidity_grade IS
    'Likviditetsgrad A–F (A >= 20x golv, B >= 5x, C >= 1x, D < 1x, E < 0.5x, F penny/illikvid). D5 (ROND 14).';

COMMENT ON COLUMN scan_results.turnover_20d_median IS
    '20-dagars medianomsättning omräknad till SEK (Migration 081).';