CREATE TABLE IF NOT EXISTS smallcap_results (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  ticker TEXT NOT NULL,
  name TEXT,
  sector TEXT,
  score_total FLOAT,
  score_insider FLOAT,
  score_fcf FLOAT,
  score_piotroski FLOAT,
  score_growth FLOAT,
  score_balance FLOAT,
  score_valuation FLOAT,
  score_momentum FLOAT,
  score_liquidity FLOAT,
  market_cap FLOAT,
  price FLOAT,
  cash_runway_months FLOAT,
  insider_buying BOOLEAN DEFAULT false,
  entry_signal TEXT,
  scan_date DATE DEFAULT CURRENT_DATE,
  UNIQUE(ticker, scan_date)
);

ALTER TABLE smallcap_results ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Everyone can view smallcap_results" ON smallcap_results FOR SELECT USING (true);
