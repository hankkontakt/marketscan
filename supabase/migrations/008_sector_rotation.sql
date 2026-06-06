CREATE TABLE IF NOT EXISTS sector_rotation (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  sector TEXT NOT NULL,
  momentum_rank INTEGER,
  strength_score FLOAT,
  trend_direction TEXT,
  avg_score FLOAT,
  top_tickers TEXT[],
  scan_date DATE DEFAULT CURRENT_DATE,
  UNIQUE(sector, scan_date)
);

ALTER TABLE sector_rotation ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Everyone can view sector_rotation" ON sector_rotation FOR SELECT USING (true);
