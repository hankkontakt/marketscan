-- 061: Ranking-integritet 7 — REVERSERA migration 059 dubbelkonvertering
-- Bakgrund (ROND 6, 2026-08-30): migration 059 antog att market_cap var i
-- NATIV valuta och multiplicerade med FX. MEN parqueten levererar REDAN USD
-- (data_fetcher._sanity_check konverterar currency != USD -> _FX_TO_USD).
-- Resultat: JPY/KRW/TWD/HKD-bolag dubbelkonverterades:
--   6098.T   163B USD (parquet) x 0.0066 = 1.1B USD (skal vara 163B)
--   2914.T    84B USD  x 0.0066 = 0.55B USD (skal vara 84B)
--   6857.T   173B USD  x 0.0066 = 1.1B  USD (skal vara 173B)
--   005930.KS 1081B USD x 0.00073 = 0.79B USD (skal vara 1081B)
-- 059 ORSADE : 61 rader felaktigt sma. Denna migration REVERSERAR 059.
--
-- Reversering: DB = parquet_usd x rate. Korrekt = DB / rate^2? Nej:
-- DB = P x rate (059), P = DBNu / rate. Korrekt = P = DBNu / rate.
-- Alltsa: korrekt = DB / rate = DB x (1/rate).
--
-- Semantisk datamigrering (ingen schemaandring). Granskad av migration-vakt.

BEGIN;

-- JPY (Tokyo .T) x0.0066 -> korrekt = /0.0066 = x151.5151...
UPDATE scan_results SET market_cap = market_cap * 151.51515
 WHERE market_cap IS NOT NULL AND market_cap < 200e9 AND ticker LIKE '%.T';

-- KRW (Seoul .KS) x0.00073 -> korrekt = x1369.863
UPDATE scan_results SET market_cap = market_cap * 1369.863
 WHERE market_cap IS NOT NULL AND market_cap < 200e9 AND ticker LIKE '%.KS';

-- TWD (Taiwan .TW) x0.031 -> korrekt = x32.2581
UPDATE scan_results SET market_cap = market_cap * 32.2581
 WHERE market_cap IS NOT NULL AND market_cap < 200e9 AND ticker LIKE '%.TW';

-- HKD (Hong Kong .HK) x0.128 -> korrekt = x7.8125
UPDATE scan_results SET market_cap = market_cap * 7.8125
 WHERE market_cap IS NOT NULL AND market_cap < 200e9 AND ticker LIKE '%.HK';

-- Efterkoll
DO $$
DECLARE
  n int;
BEGIN
  SELECT COUNT(*) INTO n FROM scan_results
   WHERE market_cap IS NOT NULL AND market_cap < 2e9
     AND (ticker LIKE '%.T' OR ticker LIKE '%.KS' OR ticker LIKE '%.TW' OR ticker LIKE '%.HK');
  IF n > 0 THEN
    RAISE NOTICE 'Varning: % JPY/KRW/TWD/HK-bolag kvar med mcap < 2B', n;
  ELSE
    RAISE NOTICE 'OK: inga JPY/KRW/TWD/HK-bolag under 2B USD';
  END IF;
END $$;

COMMIT;
