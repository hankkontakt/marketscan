-- MarketScan — Migration 079: Fix segment classification & check constraint
-- 1. Tillåt 'unknown' i scan_results.segment (CHECK constraint)
-- 2. Korrigera eventuella miljon-enheter (market_cap mellan 1 och 999 999)
-- 3. Återberäkna segment deterministiskt från normaliserat market_cap (USD)

ALTER TABLE scan_results DROP CONSTRAINT IF EXISTS scan_results_segment_check;

ALTER TABLE scan_results
    ADD CONSTRAINT scan_results_segment_check
    CHECK (segment IN ('large_cap', 'mid_cap', 'small_cap', 'micro_cap', 'unknown'));

-- Korrigera eventuella miljon-enheter i DB (0 < mc < 1M)
UPDATE scan_results
SET market_cap = market_cap * 1000000
WHERE market_cap > 0 AND market_cap < 1000000;

-- Återberäkna segment baserat på absoluta USD-trösklar:
-- large_cap >= 10B, mid_cap >= 2B, small_cap >= 300M, micro_cap < 300M, unknown för NULL/<=0
UPDATE scan_results
SET segment = CASE
    WHEN market_cap IS NULL OR market_cap <= 0 THEN 'unknown'
    WHEN market_cap >= 10000000000 THEN 'large_cap'
    WHEN market_cap >= 2000000000 THEN 'mid_cap'
    WHEN market_cap >= 300000000 THEN 'small_cap'
    ELSE 'micro_cap'
END;

COMMENT ON COLUMN scan_results.segment IS
    'Segment: large_cap (>=10B USD), mid_cap (>=2B USD), small_cap (>=300M USD), micro_cap (<300M USD), unknown (market_cap NULL/<=0). Migration 079.';
