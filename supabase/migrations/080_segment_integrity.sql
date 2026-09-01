-- MarketScan — Migration 080: Segment Integrity Backfill & Constraints
-- Säkerställer att saknat eller icke-positivt börsvärde aldrig klassas som micro_cap.
-- Kända storbolag mappas till large_cap; övriga okända blir 'unknown'.

-- 1. Tillåt 'unknown' i scan_results.segment (CHECK constraint)
ALTER TABLE scan_results DROP CONSTRAINT IF EXISTS scan_results_segment_check;

ALTER TABLE scan_results
    ADD CONSTRAINT scan_results_segment_check
    CHECK (segment IN ('large_cap', 'mid_cap', 'small_cap', 'micro_cap', 'unknown'));

-- 2. Korrigera eventuella miljon-enheter i DB (0 < mc < 1 000 000)
UPDATE scan_results
SET market_cap = market_cap * 1000000
WHERE market_cap > 0 AND market_cap < 1000000;

-- 3. Kända globala storbolag: tvinga large_cap även vid saknat/avvikande market_cap
UPDATE scan_results
SET segment = 'large_cap'
WHERE ticker IN (
    'SAP.DE', 'SAP', 'GSK.L', 'GSK', 'EQNR.OL', 'EQNR', 'INVE-B.ST', 'INVE.B',
    'DOL.TO', 'DOL', 'EDP.LS', 'GFNORTEO.MX', '2330.TW', 'TSM', 'PETR4.SA', 'PETR4',
    '2914.T', 'AZN.ST', 'AZN', 'VOLV-B.ST', 'ATCO-A.ST', 'GMG.AX', 'PHIA.AS', 'MSFT', 'MU'
);

-- 4. Återberäkna segment baserat på absoluta USD-trösklar:
-- large_cap >= 10B, mid_cap >= 2B, small_cap >= 300M, micro_cap < 300M, unknown för NULL/<=0
UPDATE scan_results
SET segment = CASE
    WHEN ticker IN (
        'SAP.DE', 'SAP', 'GSK.L', 'GSK', 'EQNR.OL', 'EQNR', 'INVE-B.ST', 'INVE.B',
        'DOL.TO', 'DOL', 'EDP.LS', 'GFNORTEO.MX', '2330.TW', 'TSM', 'PETR4.SA', 'PETR4',
        '2914.T', 'AZN.ST', 'AZN', 'VOLV-B.ST', 'ATCO-A.ST', 'GMG.AX', 'PHIA.AS', 'MSFT', 'MU'
    ) THEN 'large_cap'
    WHEN market_cap IS NULL OR market_cap <= 0 THEN 'unknown'
    WHEN market_cap >= 10000000000 THEN 'large_cap'
    WHEN market_cap >= 2000000000 THEN 'mid_cap'
    WHEN market_cap >= 300000000 THEN 'small_cap'
    ELSE 'micro_cap'
END;

-- 5. Explicit SELECT privileges for anon and authenticated roles
GRANT SELECT ON scan_results TO anon, authenticated;

COMMENT ON COLUMN scan_results.segment IS
    'Segment: large_cap (>=10B USD), mid_cap (>=2B USD), small_cap (>=300M USD), micro_cap (<300M USD), unknown (market_cap NULL/<=0). Migration 080.';