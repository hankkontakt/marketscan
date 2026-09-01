-- MarketScan — Migration 082: MasterRank segment percentile column
-- Persisterar inom-segment-percentilen (0-100) för att möjliggöra direkt
-- jämförelse mellan mikro- och storbolag i Screener och API.

ALTER TABLE master_rank
    ADD COLUMN IF NOT EXISTS master_rank_pctl numeric;

-- Explicit SELECT privileges for anon and authenticated roles (Regel 4.3)
GRANT SELECT ON master_rank TO anon, authenticated;

COMMENT ON COLUMN master_rank.master_rank_pctl IS
    'Segment-normaliserad MasterRank-percentil (0-100) inom bolagets segment (Migration 082, R15).';
