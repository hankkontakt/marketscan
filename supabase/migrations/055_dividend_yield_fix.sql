-- 055: Dividend-yield enhetsbackfill 2 — fångar %-värden i (0.1, 1]
-- Bakgrund: 054 delade dividend_yield > 1 med /100 (procent -> fraktion). MEN
-- yfinance-formatet är inkonsekvent: Visa har yield 0.73 % (lagrat 0.73), AAPL 0.35,
-- DIVISLAB 0.35, NVDA 0.44 — dessa är PROCENT men passerade 054:s > 1-regel.
-- En äkta fraktion > 0.1 (= 10 % yield) är orealistisk för seriösa aktier, så
-- enhetsgränsen ligger på 0.1. Data_fetcher-versionen (2026-08-29 18:30) använder
-- nu dividendRate/current_price vilket är enhetsfritt; denna bakfill konverterar
-- kvarvarande %-värden i DB.
-- Semantisk datamigrering (ingen schemaändring). Granskad av migration-vakt.

BEGIN;

UPDATE scan_results
   SET dividend_yield = dividend_yield / 100
 WHERE dividend_yield IS NOT NULL AND dividend_yield > 0.1 AND dividend_yield <= 1;

-- Efterkoll: 0 värden i (0.1, 1] ska finnas kvar
DO $$
DECLARE
  n int;
BEGIN
  SELECT COUNT(*) INTO n FROM scan_results
   WHERE dividend_yield IS NOT NULL AND dividend_yield > 0.1 AND dividend_yield <= 1;
  IF n > 0 THEN
    RAISE NOTICE 'Varning: % rader kvar i (0.1, 1] — kontrollera källan', n;
  END IF;
END $$;

COMMIT;
