-- Migration 032: Risk Profile for #19
-- Tabell för användares riskprofil (Black-Litterman-portföljkonstruktion).
-- Körs MANUELLT i Supabase SQL Editor.

CREATE TABLE IF NOT EXISTS user_risk_profiles (
  user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  profile TEXT NOT NULL,            -- 'trygg'|'balanserad'|'tillvaxt'|'aggressiv'|'maxrisk'
  risk_score INTEGER,               -- 0-100 från frågeformuläret
  time_horizon_years INTEGER,
  max_position_pct FLOAT,           -- t.ex. 0.10 för trygg, 0.30 för maxrisk
  target_volatility FLOAT,          -- årlig målvolatilitet
  answers JSONB,                    -- råa svar för spårbarhet
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE user_risk_profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "own_profile_rw" ON user_risk_profiles
  USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

GRANT SELECT, INSERT, UPDATE ON user_risk_profiles TO authenticated;

COMMENT ON TABLE user_risk_profiles IS 'User risk profiles for Black-Litterman. Migration 032. Diagnostic marker: migration_032_risk_profile.';
