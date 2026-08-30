-- 063: Ranking-integritet 9 — korrigera nativa mcap >1e12 till USD
-- Bakgrund (ROND 6, 2026-08-30): 061/062 hanterade 47 JPY/KRW/TWD/HK-bolag,
-- men 23 rader med nativ-valutara mcap? > 1e12 kvar (6758.T 3082T, 005930.KS
-- 1481T, 2330.TW 62.7T, TSCO.L 47.5T) — dessa AR nativa JPY/TWD/KRW (aldrig
-- USD-konverterade data). Korrekt USD = nativ x FX (df: data_fetcher-regeln).
-- Akta USD >1e12 (NVDA/AAPL/MSFT/AMZN/GOOGL) lamnas (ej suffix-matade).
--
-- Semantisk datamigrering (ingen schemaandring). Granskad av migration-vakt.

BEGIN;

-- JPY x0.0066
UPDATE scan_results SET market_cap = market_cap * 0.0066
 WHERE market_cap IS NOT NULL AND market_cap > 1e12 AND ticker LIKE '%.T';

-- KRW x0.00073
UPDATE scan_results SET market_cap = market_cap * 0.00073
 WHERE market_cap IS NOT NULL AND market_cap > 1e12 AND ticker LIKE '%.KS';

-- TWD x0.031
UPDATE scan_results SET market_cap = market_cap * 0.031
 WHERE market_cap IS NOT NULL AND market_cap > 1e12 AND ticker LIKE '%.TW';

-- HKD x0.128
UPDATE scan_results SET market_cap = market_cap * 0.128
 WHERE market_cap IS NOT NULL AND market_cap > 1e12 AND ticker LIKE '%.HK';

-- GBP (GBp) x0.0127
UPDATE scan_results SET market_cap = market_cap * 0.0127
 WHERE market_cap IS NOT NULL AND market_cap > 1e12 AND ticker LIKE '%.L';

-- Efterkoll
DO $$
DECLARE
  n int;
BEGIN
  SELECT COUNT(*) INTO n FROM scan_results
   WHERE market_cap IS NOT NULL AND market_cap > 1e12
     AND (ticker LIKE '%.T' OR ticker LIKE '%.KS' OR ticker LIKE '%.TW'
          OR ticker LIKE '%.HK' OR ticker LIKE '%.L');
  IF n > 0 THEN
    RAISE NOTICE 'Varning: % native mcap > 1e12 kvar', n;
  ELSE
    RAISE NOTICE 'OK: inga native mcap > 1e12 (bara ev. USD-mega-bolag)';
  END IF;
END $$;

COMMIT;
