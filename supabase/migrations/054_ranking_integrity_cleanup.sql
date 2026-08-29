-- 054: Ranking-integritet — städa datamigreringar + ta bort seed-demo-raderna
-- Bakgrund (ROND 5, 2026-08-29): scan_results innehåller (a) omöjliga rådata-värden
-- från yfinance .info (negativ P/E, negativ D/E, negativ current_ratio,
-- dividend_yield i % som nu normaliseras till fraktion i pipelinen) och
-- (b) 8 seed.sql-demo-tickers med hårdkodade heltalspoäng som aldrig skrivits över
-- av pipelinen (COALESCE-upsert + .ST-rate-limiting) — de topp-rankade VOLV-B.ST
-- (84.0), SAND.ST (77.0), ALFA.ST (75.0) m.fl. är DEMO, inte pipeline-data.
-- Gäller BARA befintliga rader: framtida loads normaliseras i data_fetcher.
--
-- Semantisk datamigrering (ingen schemaändring). Granskad av migration-vakt.

BEGIN;

-- 1) P/E: omöjliga värden → NULL (fångar negativa OCH < 1 samt > 200; APP 0.39)
UPDATE scan_results
   SET pe_trailing = NULL
 WHERE pe_trailing IS NOT NULL AND (pe_trailing <= 1 OR pe_trailing > 200);

UPDATE scan_results
   SET pe_forward = NULL
 WHERE pe_forward IS NOT NULL AND (pe_forward <= 1 OR pe_forward > 200);

-- 2) D/E: negativt → 0 (nettokassa-bolag bevaras), >200 → NULL
UPDATE scan_results SET debt_to_equity = 0
 WHERE debt_to_equity IS NOT NULL AND debt_to_equity < 0;
UPDATE scan_results SET debt_to_equity = NULL
 WHERE debt_to_equity IS NOT NULL AND debt_to_equity > 200;

-- 3) Current ratio: negativt → 0, >20 → NULL
UPDATE scan_results SET current_ratio = 0
 WHERE current_ratio IS NOT NULL AND current_ratio < 0;
UPDATE scan_results SET current_ratio = NULL
 WHERE current_ratio IS NOT NULL AND current_ratio > 20;

-- 4) dividend_yield: raffla lagrade %-värden (2.19 = 2.19 %) → fraktion (0.0219).
--    Ny pipeline skriver redan fraktion; denna backfill konverterar historiska.
UPDATE scan_results
   SET dividend_yield = dividend_yield / 100
 WHERE dividend_yield IS NOT NULL AND dividend_yield > 1;

-- 5) Finansiella/REIT/insurance: gross_margin & current_ratio är meningslösa
--    (ingen COGS, bank-CR ≠ industriell likviditet) → NULL.
UPDATE scan_results
   SET gross_margin = NULL, current_ratio = NULL
 WHERE sector IN ('Financial Services', 'Real Estate', 'Insurance')
   AND (gross_margin IS NOT NULL OR current_ratio IS NOT NULL);

-- 6) Seed-demo-tickers (supabase/seed.sql, hårdkodade heltalspoäng):
--    ta bort rader som fortfarande MATCHAR seed-värdena exakt — dvs inte blivit
--    överskrivna av pipelinen. Värden från seed.sql (score_total + price + ml_rank):
--    VOLV-B.ST 84+287.40+3 | ERIC-B.ST 71+74.22+12 | SAND.ST 77+218.70+8 |
--    INVE-B.ST 80+312.60+5 | SEB-A.ST 68+143.30+18 | ALFA.ST 75+424.80+9 |
--    NIBE-B.ST 62+52.40+35 | BALD-B.ST 58+38.70+42
--    ml_rank-koppling: pipeline-ml_rank är percentil×100 (0-100 med 1 decimal,
--    round(1) i ml_predictor) och kan teoretiskt bli t.ex. 3.0 — kombinationen
--    tre exakta värden gör false-positive ≈ 0.001 % (migration-vakt 2026-08-29).
DELETE FROM scan_results
 WHERE (ticker = 'VOLV-B.ST' AND score_total = 84 AND price = 287.40 AND ml_rank = 3)
    OR (ticker = 'ERIC-B.ST' AND score_total = 71 AND price = 74.22  AND ml_rank = 12)
    OR (ticker = 'SAND.ST'   AND score_total = 77 AND price = 218.70 AND ml_rank = 8)
    OR (ticker = 'INVE-B.ST' AND score_total = 80 AND price = 312.60 AND ml_rank = 5)
    OR (ticker = 'SEB-A.ST'  AND score_total = 68 AND price = 143.30 AND ml_rank = 18)
    OR (ticker = 'ALFA.ST'   AND score_total = 75 AND price = 424.80 AND ml_rank = 9)
    OR (ticker = 'NIBE-B.ST' AND score_total = 62 AND price = 52.40  AND ml_rank = 35)
    OR (ticker = 'BALD-B.ST' AND score_total = 58 AND price = 38.70  AND ml_rank = 42);

COMMIT;
