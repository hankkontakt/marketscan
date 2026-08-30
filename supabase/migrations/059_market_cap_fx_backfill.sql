-- 059: Ranking-integritet 5 — konvertera market_cap till USD (FX-backfill)
-- Bakgrund (ROND 5, 2026-08-30): DB lagrade market_cap i NATIV valuta for
-- icke-USD-borser (JPY/KRW/TWD/HKD/INR/SEK o.s.v.) — 005930.KS 1481T,
-- 2330.TW 62.7T, 6098.T 24.7T. db_loader._to_usd (rad 158) konverterar nu
-- vid last, men befintliga rader kvarstar i nativ valuta.
-- Baseras pa ticker-suffix (bors) -> FX-tabell i db_loader (statisk, USD).
--
-- Semantisk datamigrering (ingen schemaandring). Granskad av migration-vakt.

BEGIN;

-- JPY (Tokyo .T) x0.0066
UPDATE scan_results SET market_cap = market_cap * 0.0066
 WHERE market_cap IS NOT NULL AND market_cap > 1e12 AND ticker LIKE '%.T';

-- KRW (Seoul .KS) x0.00073
UPDATE scan_results SET market_cap = market_cap * 0.00073
 WHERE market_cap IS NOT NULL AND market_cap > 1e12 AND ticker LIKE '%.KS';

-- TWD (Taiwan .TW) x0.031
UPDATE scan_results SET market_cap = market_cap * 0.031
 WHERE market_cap IS NOT NULL AND market_cap > 1e12 AND ticker LIKE '%.TW';

-- HKD (Hong Kong .HK) x0.128
UPDATE scan_results SET market_cap = market_cap * 0.128
 WHERE market_cap IS NOT NULL AND market_cap > 1e12 AND ticker LIKE '%.HK';

-- INR (.NS) x0.0112
UPDATE scan_results SET market_cap = market_cap * 0.0112
 WHERE market_cap IS NOT NULL AND market_cap > 1e12 AND ticker LIKE '%.NS';

-- GBP (.L, GBp) x0.0127
UPDATE scan_results SET market_cap = market_cap * 0.0127
 WHERE market_cap IS NOT NULL AND market_cap > 1e12 AND ticker LIKE '%.L';

-- SGD (.SI) x0.765
UPDATE scan_results SET market_cap = market_cap * 0.765
 WHERE market_cap IS NOT NULL AND market_cap > 1e12 AND ticker LIKE '%.SI';

-- SEK (.ST) x0.093
UPDATE scan_results SET market_cap = market_cap * 0.093
 WHERE market_cap IS NOT NULL AND market_cap > 1e12 AND ticker LIKE '%.ST';

-- Norska ('.OL') x0.09
UPDATE scan_results SET market_cap = market_cap * 0.09
 WHERE market_cap IS NOT NULL AND market_cap > 1e12 AND ticker LIKE '%.OL';

-- Salu-Ret/fel-tickers + USD (ingen suffix) lamnas; fangar oversyn.
-- Ej suffix-matbar: AUD/CHF/CAD/DKK etc. — lamnas (markerade i efterkontroll).

-- Efterkoll: antal kvar >1e12 (borde vara 0)
DO $$
DECLARE
  n int;
BEGIN
  SELECT COUNT(*) INTO n FROM scan_results WHERE market_cap IS NOT NULL AND market_cap > 1e12;
  IF n > 0 THEN
    RAISE NOTICE 'Varning: % rader kvar med mcap > 1e12 — kontrollera kvarn', n;
  ELSE
    RAISE NOTICE 'OK: inga mcap > 1e12 kvar';
  END IF;
END $$;

COMMIT;
