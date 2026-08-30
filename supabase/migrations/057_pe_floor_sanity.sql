-- 057: Ranking-integritet 3 — sanera misstankt-lag P/E (pe < 3)
-- Bakgrund (ROND 5, 2026-08-30, efter kordning 33301752810 + 33303998193):
-- yfinance .info ger ibland trailingPE ~ 1-2 istallet for 20-30 (META 1.15,
-- KO 2.41, SAND 2.17, ALFA 2.01, WM 1.14, ADYEN 1.98, BHP 2.02, MMM 2.13,
-- ROST 2.53). Akta pe < 3 ar extremt sallsynt for seriosa bolag (banker har
-- pe 8-15, REITs 10-25), sa alla pe i [1,3) noddas -> NULL.
-- Skyddsnat: db_loader._apply_sanity + stock-scanner _apply_sanity har nu
-- samma pe < 3-regel (2026-08-30, adc60bc + 3abb43a).
--
-- Semantisk datamigrering (ingen schemaandring). Granskad av migration-vakt.

BEGIN;

UPDATE scan_results
   SET pe_trailing = NULL
 WHERE pe_trailing IS NOT NULL AND pe_trailing < 3;

UPDATE scan_results
   SET pe_forward = NULL
 WHERE pe_forward IS NOT NULL AND pe_forward < 3;

-- Efterkoll: 0 rader med pe i [1,3)
DO $$
DECLARE
  n int;
BEGIN
  SELECT COUNT(*) INTO n FROM scan_results
   WHERE (pe_trailing IS NOT NULL AND pe_trailing < 3)
      OR (pe_forward IS NOT NULL AND pe_forward < 3);
  IF n > 0 THEN
    RAISE NOTICE 'Varning: % rader med pe < 3 kvar — kontrollera kallan', n;
  ELSE
    RAISE NOTICE 'OK: 0 rader med pe < 3';
  END IF;
END $$;

COMMIT;
