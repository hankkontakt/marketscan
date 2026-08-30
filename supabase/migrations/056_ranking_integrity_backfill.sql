-- 056: Ranking-integritet 2 — sanera skräp som morning/evening skrev tillbaka
-- Bakgrund (ROND 5, 2026-08-30): 053/054/055 sanerade scan_results den 29:e,
-- MEN nästa morning-run (08-30 06:15) läste den RÅA scored_universe_2026-08-29
-- (committad av weekly'n 13:37 den 29:e, INNAN data_fetcher-sanity-fixarna
-- pushades 16:21 samma dag) och skrev tillbaka råvärden via UPSERT:
--   pe_trailing=-6.79 (NVDA), dividend_yield=0.44 (rå %, ska vara 0.0044),
--   debt_to_equity=-34.2, current_ratio<0, gross_margin i finansiella sektorer.
-- Denna migration applicerar samma regler som 054/055 + |v|>5-skydd, idempotent
-- (säkert att köra även om värdena redan är rena).
-- Skyddsnät: db_loader._apply_sanity (2026-08-30) sanerar ALLA framtida loads.
--
-- Semantisk datamigrering (ingen schemaändring). Granskad av migration-vakt.

BEGIN;

-- 1) P/E: omöjliga värden (negativa, <1, >200) -> NULL
UPDATE scan_results
   SET pe_trailing = NULL
 WHERE pe_trailing IS NOT NULL AND (pe_trailing <= 1 OR pe_trailing > 200);

UPDATE scan_results
   SET pe_forward = NULL
 WHERE pe_forward IS NOT NULL AND (pe_forward <= 1 OR pe_forward > 200);

-- 2) D/E: negativt -> 0 (nettokassa-bolag), >200 -> NULL
UPDATE scan_results SET debt_to_equity = 0
 WHERE debt_to_equity IS NOT NULL AND debt_to_equity < 0;
UPDATE scan_results SET debt_to_equity = NULL
 WHERE debt_to_equity IS NOT NULL AND debt_to_equity > 200;

-- 3) Current ratio: negativt -> 0, >20 -> NULL
UPDATE scan_results SET current_ratio = 0
 WHERE current_ratio IS NOT NULL AND current_ratio < 0;
UPDATE scan_results SET current_ratio = NULL
 WHERE current_ratio IS NOT NULL AND current_ratio > 20;

-- 4) dividend_yield: %-värden (>0.1) -> fraktion (/100), negativt -> NULL
UPDATE scan_results
   SET dividend_yield = dividend_yield / 100
 WHERE dividend_yield IS NOT NULL AND dividend_yield > 0.1;
UPDATE scan_results SET dividend_yield = NULL
 WHERE dividend_yield IS NOT NULL AND dividend_yield < 0;

-- 5) Avkastning/marginaler: |v| > 5 är orimligt -> NULL
UPDATE scan_results SET roe = NULL
 WHERE roe IS NOT NULL AND ABS(roe) > 5;
UPDATE scan_results SET roa = NULL
 WHERE roa IS NOT NULL AND ABS(roa) > 5;
UPDATE scan_results SET gross_margin = NULL
 WHERE gross_margin IS NOT NULL AND ABS(gross_margin) > 5;
UPDATE scan_results SET operating_margin = NULL
 WHERE operating_margin IS NOT NULL AND ABS(operating_margin) > 5;

-- 6) Finansiella/REIT/insurance: gross_margin & current_ratio -> NULL
UPDATE scan_results
   SET gross_margin = NULL, current_ratio = NULL
 WHERE sector IN ('Financial Services', 'Real Estate', 'Insurance')
   AND (gross_margin IS NOT NULL OR current_ratio IS NOT NULL);

-- Efterkoll: 0 anomalier kvar
DO $$
DECLARE
  n int;
BEGIN
  SELECT COUNT(*) INTO n FROM scan_results
   WHERE (pe_trailing IS NOT NULL AND (pe_trailing <= 1 OR pe_trailing > 200))
      OR (pe_forward  IS NOT NULL AND (pe_forward  <= 1 OR pe_forward > 200))
      OR (debt_to_equity IS NOT NULL AND (debt_to_equity < 0 OR debt_to_equity > 200))
      OR (dividend_yield IS NOT NULL AND (dividend_yield > 0.1 OR dividend_yield < 0))
      OR (current_ratio IS NOT NULL AND (current_ratio < 0 OR current_ratio > 20));
  IF n > 0 THEN
    RAISE NOTICE 'Varning: % rader kvar med anomalier — kontrollera källan', n;
  ELSE
    RAISE NOTICE 'OK: 0 anomalier kvar i scan_results';
  END IF;
END $$;

COMMIT;
