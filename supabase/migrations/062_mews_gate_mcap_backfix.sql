-- 062: Ranking-integritet 8 — MEWS-gate-backfix + resterande mcap-FX-reversering
-- Bakgrund (ROND 6, 2026-08-30):
--  (a) En rad (ACI, piot=2, roa=-0.0247) har fortfarande mews_flag=True trots
--      kvalitetsgaten (piotroski>=5, roa>0) — gammal rad skriven nar MEWS
--      korades innan Piotroski. Gaten ska blocka.
--  (b) 38 rader med mcap>1e12 kvar (gamla nativa varden som 059 inte reverserade
--      korrekt — JPY/TWD/KRW/HK-bolag). Dessutom 1 JPY-rad under 2B USD.
-- Reversering matchar migration 061.
--
-- Semantisk datamigrering (ingen schemaandring). Granskad av migration-vakt.

BEGIN;

-- (a) MEWS-gate: flagga kravet piotroski_f >= 5 OCH roa > 0
UPDATE scan_results
   SET mews_flag = false
 WHERE mews_flag AND (piotroski_f IS NULL OR piotroski_f < 5 OR roa IS NULL OR roa <= 0);

-- (b) mcap-reversering for kvarstaende JPY/KRW/TWD/HK >1e12 (double-konv 059)
UPDATE scan_results SET market_cap = market_cap * 151.51515
 WHERE market_cap IS NOT NULL AND market_cap > 1e12 AND ticker LIKE '%.T';
UPDATE scan_results SET market_cap = market_cap * 1369.863
 WHERE market_cap IS NOT NULL AND market_cap > 1e12 AND ticker LIKE '%.KS';
UPDATE scan_results SET market_cap = market_cap * 32.2581
 WHERE market_cap IS NOT NULL AND market_cap > 1e12 AND ticker LIKE '%.TW';
UPDATE scan_results SET market_cap = market_cap * 7.8125
 WHERE market_cap IS NOT NULL AND market_cap > 1e12 AND ticker LIKE '%.HK';

-- (c) JPY-rad under 2B (inte dubbelkonv): 6098-T-liknande var redan fixad;
--     valja den kvarstaende till NVL om < 1e9 (annars till large_cap)
UPDATE scan_results SET market_cap = NULL
 WHERE market_cap IS NOT NULL AND market_cap < 2e9
   AND (ticker LIKE '%.T' OR ticker LIKE '%.KS' OR ticker LIKE '%.TW' OR ticker LIKE '%.HK')
   AND market_cap < 1e9;

-- Efterkoll
DO $$
DECLARE
  n int;
BEGIN
  SELECT COUNT(*) INTO n FROM scan_results WHERE mews_flag AND (piotroski_f < 5 OR roa <= 0);
  IF n > 0 THEN
    RAISE NOTICE 'Varning: % mews-flaggor bryter gaten', n;
  ELSE
    RAISE NOTICE 'OK: 0 mews-flaggor bryter gaten';
  END IF;
END $$;

COMMIT;
