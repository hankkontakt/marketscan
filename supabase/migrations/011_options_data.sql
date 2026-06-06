CREATE TABLE IF NOT EXISTS options_data (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  ticker TEXT NOT NULL,
  expiration DATE,
  strike FLOAT,
  option_type TEXT CHECK (option_type IN ('call', 'put')),
  last_price FLOAT,
  bid FLOAT,
  ask FLOAT,
  implied_volatility FLOAT,
  delta FLOAT,
  gamma FLOAT,
  theta FLOAT,
  vega FLOAT,
  open_interest INTEGER,
  volume INTEGER,
  snapshot_date DATE DEFAULT CURRENT_DATE,
  UNIQUE(ticker, expiration, strike, option_type, snapshot_date)
);

ALTER TABLE options_data ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Everyone can view options_data" ON options_data FOR SELECT USING (true);
