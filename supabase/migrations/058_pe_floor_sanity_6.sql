-- 058: Ranking-integritet 4 — sanera misstankt-lag P/E (pe < 6)
-- Bakgrund (ROND 5, 2026-08-30, efter korning 33301752810 + 33303998193 + lokalt):
-- yfinance .info ger ibland trailingPE ~ 1-5 istallet for 20-40 (META 1.15,
-- KO 2.41, AAPL 3.03, CME 3.66, APP 3.68, LIN 5.18, LLY 5.59, SIEMENS 3.66,
-- DEERE 4.97, ATLAS COPCO 5.74, BAE 5.55). Akta pe < 6 for seriost bolag är
-- mycket ovanligt; varden i [1,6) är i praktiken alltid felaktiga yfinance-data
-- som far "billigt"-signaler. Alla pe < 6 noddas -> NULL.
-- Skyddsnat: db_loader._apply_sanity + stock-scanner _apply_sanity har nu
-- samma pe < 6-regel (2026-08-30).
-- Ersatter 057 (pe < 3) — brettar gransen till 6.
--
-- Semantisk datamigrering (ingen schemaandring). Granskad av migration-vakt.

BEGIN;

UPDATE scan_results
   SET pe_trailing = NULL
 WHERE pe_trailing IS NOT NULL AND pe_trailing < 6;

UPDATE scan_results
   SET pe_forward = NULL
 WHERE pe_forward IS NOT NULL AND pe_forward < 6;

-- Efterkoll: 0 rader med pe i [1,6)
DO $$
DECLARE
  n int;
BEGIN
  SELECT COUNT(*) INTO n FROM scan_results
   WHERE (pe_trailing IS NOT NULL AND pe_trailing < 6)
      OR (pe_forward IS NOT NULL AND pe_forward < 6);
  IF n > 0 THEN
    RAISE NOTICE 'Varning: % rader med pe < 6 kvar — kontrollera kallan', n;
  ELSE
    RAISE NOTICE 'OK: 0 rader med pe < 6';
  END IF;
END $$;

COMMIT;
