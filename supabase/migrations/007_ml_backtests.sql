CREATE TABLE IF NOT EXISTS backtest_results (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  strategy_name TEXT NOT NULL,
  tickers TEXT[],
  total_return FLOAT,
  cagr FLOAT,
  sharpe FLOAT,
  max_drawdown FLOAT,
  volatility FLOAT,
  win_rate FLOAT,
  num_trades INTEGER,
  start_date DATE,
  end_date DATE,
  equity_curve JSONB,
  created_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE backtest_results ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Everyone can view backtest_results" ON backtest_results FOR SELECT USING (true);
