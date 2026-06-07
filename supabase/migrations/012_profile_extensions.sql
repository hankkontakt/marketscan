-- MarketScan 2.0 — Migration 012: Profile extensions
-- Adds experience level, onboarding, theme preference, email opt-in to profiles
-- Run: Supabase Dashboard → SQL Editor

ALTER TABLE profiles
  ADD COLUMN IF NOT EXISTS experience_level TEXT DEFAULT 'beginner'
    CHECK (experience_level IN ('beginner', 'expert')),
  ADD COLUMN IF NOT EXISTS onboarding_completed BOOLEAN DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS theme TEXT DEFAULT 'light'
    CHECK (theme IN ('light', 'dark', 'auto')),
  ADD COLUMN IF NOT EXISTS email_opt_in BOOLEAN DEFAULT FALSE;

-- Notification preferences table (per user)
CREATE TABLE IF NOT EXISTS notification_preferences (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  price_alerts BOOLEAN DEFAULT TRUE,
  earnings BOOLEAN DEFAULT TRUE,
  score_changes BOOLEAN DEFAULT TRUE,
  email_digest_freq TEXT DEFAULT 'never'
    CHECK (email_digest_freq IN ('never', 'daily', 'weekly')),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (user_id)
);

ALTER TABLE notification_preferences ENABLE ROW LEVEL SECURITY;

CREATE POLICY "notification_preferences_own"
  ON notification_preferences
  USING (auth.uid() = user_id);

-- Auto-create notification_preferences on signup
CREATE OR REPLACE FUNCTION handle_new_user() RETURNS trigger
  LANGUAGE plpgsql SECURITY DEFINER AS $$
BEGIN
  INSERT INTO profiles (id, display_name) VALUES (NEW.id, NEW.email)
    ON CONFLICT (id) DO NOTHING;
  INSERT INTO portfolios (user_id, name) VALUES (NEW.id, 'Min portfölj')
    ON CONFLICT DO NOTHING;
  INSERT INTO notification_preferences (user_id) VALUES (NEW.id)
    ON CONFLICT (user_id) DO NOTHING;
  RETURN NEW;
END;
$$;
