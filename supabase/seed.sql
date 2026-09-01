-- Seed data for development / demo
-- Run after migration: supabase db reset
--
-- ⚠️ VARNING (2026-08-29): kör ALDRIG denna fil mot produktion!
--   Dessa 8 rader är FASTA demovärden (hårdkodade heltalspoäng, ordinaL ml_rank).
--   Då de kördes 2026-08-28 topp-rankade de VOLV-B.ST (84)/SAND.ST (77)/ALFA.ST (75)
--   i produktion — och skrevs aldrig över av pipelinen (COALESCE-upsert + .ST-
--   fetch-rate-limiting). Se migration 054 som tar bort dem + ROND 5 i PLAN.md.
--   Om demodata behövs: använd i stället scripts/seed_demo.py (endast tom DB).

-- Insert a demo admin user profile (assumes auth user exists with this ID)
-- In production: users created via Supabase Auth trigger

-- Sample scan_results for UI development (remove in production)
INSERT INTO scan_results (
  ticker, name, segment, sector, country,
  score_total, score_value, score_quality, score_momentum, score_growth,
  score_risk, score_size, score_dividend, score_sentiment,
  entry_signal, confidence_label, trend_signal,
  predicted_return, ml_rank, piotroski_f,
  price, change_pct, market_cap, pe_trailing, roe, dividend_yield, beta,
  low_liquidity, scan_date
) VALUES
  ('VOLV-B.ST','Volvo AB ser. B','large_cap','Industri','SE',
   84,72,88,79,65,70,85,60,75,
   'STARK','Hög','Upptrend',0.032,3,7,
   287.40,0.018,580000000000,12.4,0.18,0.03,0.95,false,CURRENT_DATE),
  ('ERIC-B.ST','Telefonaktiebolaget LM Ericsson','large_cap','Teknik','SE',
   71,65,70,68,55,65,72,45,68,
   'OK','Medel','Upptrend',0.018,12,6,
   74.22,-0.005,240000000000,22.1,0.12,0.025,1.1,false,CURRENT_DATE),
  ('SAND.ST','Sandvik AB','large_cap','Industri','SE',
   77,74,80,73,62,68,78,55,70,
   'OK','Hög','Sidled',0.021,8,7,
   218.70,0.009,340000000000,14.2,0.19,0.028,0.88,false,CURRENT_DATE),
  ('INVE-B.ST','Investor AB ser. B','large_cap','Finans','SE',
   80,82,85,70,58,75,80,65,72,
   'STARK','Hög','Upptrend',0.025,5,8,
   312.60,0.012,890000000000,16.8,0.22,0.018,0.75,false,CURRENT_DATE),
  ('SEB-A.ST','Skandinaviska Enskilda Banken','large_cap','Finans','SE',
   68,70,72,62,50,60,70,70,62,
   'OK','Medel','Sidled',0.012,18,6,
   143.30,0.003,310000000000,10.2,0.14,0.06,0.82,false,CURRENT_DATE),
  ('ALFA.ST','Alfa Laval AB','mid_cap','Industri','SE',
   75,68,78,77,70,65,74,48,72,
   'OK','Hög','Upptrend',0.028,9,7,
   424.80,0.022,180000000000,18.5,0.21,0.022,0.92,false,CURRENT_DATE),
  ('NIBE-B.ST','NIBE Industrier AB','mid_cap','Industri','SE',
   62,55,65,58,60,55,62,35,60,
   'VÄNTA','Medel','Nedtrend',-0.008,35,5,
   52.40,-0.015,95000000000,32.1,0.10,0.012,1.15,false,CURRENT_DATE),
  ('BALD-B.ST','Fastighets AB Balder','mid_cap','Fastighet','SE',
   58,62,60,52,45,50,58,40,55,
   'VÄNTA','Låg','Nedtrend',-0.015,42,4,
   38.70,-0.022,45000000000,0,0.06,0,1.45,true,CURRENT_DATE)
ON CONFLICT (ticker) DO UPDATE SET
  score_total = EXCLUDED.score_total,
  price = EXCLUDED.price,
  scan_date = EXCLUDED.scan_date,
  updated_at = NOW();

-- CPRX — Catalyst Pharmaceuticals. Deliberately seeded with its LEGACY state
-- (strong-buy-looking row): the V3 Security Master must resolve it to a MERGED
-- listing via the 084 corporate action and exclude it from any published
-- decision. This row is the local regression proof for the CPRX gate.
INSERT INTO scan_results (
  ticker, name, segment, sector, country,
  score_total, score_value, score_quality, score_momentum, score_growth,
  score_risk, score_size, score_dividend, score_sentiment,
  entry_signal, confidence_label, trend_signal,
  predicted_return, ml_rank, piotroski_f,
  price, change_pct, market_cap, pe_trailing, roe, dividend_yield, beta,
  low_liquidity, scan_date
) VALUES (
  'CPRX','Catalyst Pharmaceuticals, Inc.','small_cap','Health Care','US',
   78,60,80,72,65,55,70,0,68,
   'STARK','Hög','Upptrend',0.031,2,7,
   31.49,-0.002,4100000000,9.8,0.30,0,0.62,false,CURRENT_DATE
) ON CONFLICT (ticker) DO UPDATE SET
  score_total = EXCLUDED.score_total,
  price = EXCLUDED.price,
  scan_date = EXCLUDED.scan_date,
  updated_at = NOW();

-- Same-day MasterRank rows for every seeded scan_results ticker. The V3
-- publication bridge requires same-day MasterRank for publishable rows.
INSERT INTO master_rank (
  ticker, scan_date, master_rank, master_rank_pctl, tier,
  quality_z, value_z, momentum_z, analyst_z, tech_z, insider_z, catalyst_z,
  growth_z, pit_status, trend_tech, warning_flags, data_missing,
  analyst_upside, analyst_count
) VALUES
  ('VOLV-B.ST', CURRENT_DATE, 84.0, 97.0, 'T1', 88, 72, 79, 60, 70, 55, 50, 65, 'READY', 'Upptrend', '[]', '[]', 0.08, 12),
  ('ERIC-B.ST', CURRENT_DATE, 71.0, 78.0, 'T2', 70, 65, 68, 55, 65, 50, 45, 55, 'READY', 'Upptrend', '[]', '[]', 0.06, 15),
  ('SAND.ST',   CURRENT_DATE, 77.0, 88.0, 'T2', 80, 74, 73, 62, 68, 55, 50, 62, 'READY', 'Sidled',  '[]', '[]', 0.05, 14),
  ('INVE-B.ST', CURRENT_DATE, 80.0, 91.0, 'T1', 85, 82, 70, 58, 75, 60, 55, 58, 'READY', 'Upptrend', '[]', '[]', 0.09, 10),
  ('SEB-A.ST',  CURRENT_DATE, 68.0, 72.0, 'T2', 72, 70, 62, 50, 60, 55, 40, 50, 'READY', 'Sidled',  '[]', '[]', 0.04, 16),
  ('ALFA.ST',   CURRENT_DATE, 75.0, 84.0, 'T2', 78, 68, 77, 70, 65, 50, 45, 70, 'READY', 'Upptrend', '[]', '[]', 0.07, 11),
  ('NIBE-B.ST', CURRENT_DATE, 62.0, 55.0, 'T3', 65, 55, 58, 60, 55, 45, 40, 60, 'READY', 'Nedtrend', '[]', '["tech"]', 0.03, 9),
  ('BALD-B.ST', CURRENT_DATE, 58.0, 42.0, 'T3', 60, 62, 52, 45, 50, 40, 35, 45, 'READY', 'Nedtrend', '["low_liquidity"]', '[]', -0.01, 8),
  ('CPRX',      CURRENT_DATE, 76.85, 92.0, 'T1', 75, 60, 70, 55, 65, 50, 55, 62, 'READY', 'Upptrend', '[]', '[]', 0.05, 6)
ON CONFLICT (ticker, scan_date) DO UPDATE SET
  master_rank = EXCLUDED.master_rank,
  master_rank_pctl = EXCLUDED.master_rank_pctl,
  tier = EXCLUDED.tier,
  pit_status = EXCLUDED.pit_status;
