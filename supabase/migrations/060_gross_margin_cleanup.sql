-- 060: Ranking-integritet 6 — sanera negativ gross_margin (icke-finansiella)
-- Bakgrund (ROND 6, 2026-08-30): DB har fortfarande negativ gross_margin for
-- icke-finansiella bolag (ROST -0.10, EG -0.34, SAND -0.04, AAPL -0.004,
-- BLK -0.02; 000270.KS -0.18, ACN -0.18, GE -0.13 tidigare). Live-yfinance ger
-- positiva varden (ROST +0.34, EG +0.20, SAND +0.40, AAPL +0.46, GE +0.31).
-- Negativ gm for icke-finansiella ar yfinance-skrap.
-- Skyddsnat: db_loader._apply_sanity + stock-scanner _apply_sanity gm<0-regel
-- (ROND 6, 2a421d3/35f23d8 + b61f6d0/753bfa8).
--
-- Semantisk datamigrering (ingen schemaandring). Granskad av migration-vakt.

BEGIN;

UPDATE scan_results
   SET gross_margin = NULL
 WHERE gross_margin IS NOT NULL AND gross_margin < 0
   AND sector NOT IN ('Financial Services', 'Real Estate', 'Insurance');

-- Efterkoll: 0 negativ gm for icke-finansiella
DO $$
DECLARE
  n int;
BEGIN
  SELECT COUNT(*) INTO n FROM scan_results
   WHERE gross_margin IS NOT NULL AND gross_margin < 0
     AND sector NOT IN ('Financial Services', 'Real Estate', 'Insurance');
  IF n > 0 THEN
    RAISE NOTICE 'Varning: % rader kvar med negativ gm (icke-fin) — kontrollera', n;
  ELSE
    RAISE NOTICE 'OK: 0 negativ gm (icke-fin)';
  END IF;
END $$;

COMMIT;
