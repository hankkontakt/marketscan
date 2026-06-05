-- Seed data for development / demo
-- Run after migration: supabase db reset

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
