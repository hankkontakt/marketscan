CREATE TABLE IF NOT EXISTS ml_predictions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  ticker TEXT NOT NULL,
  predicted_return FLOAT,
  ml_rank INTEGER,
  model_version TEXT,
  feature_importance JSONB,
  sector TEXT,
  predicted_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(ticker, model_version)
);

ALTER TABLE ml_predictions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Everyone can view ml_predictions" ON ml_predictions FOR SELECT USING (true);
