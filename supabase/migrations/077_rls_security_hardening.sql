-- MarketScan — Migration 077: RLS Security Hardening & portfolio_holdings
-- Kör manuellt i Supabase SQL Editor.

-- 1. Enable RLS on company_profiles & public read policy
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'company_profiles') THEN
    ALTER TABLE company_profiles ENABLE ROW LEVEL SECURITY;
    DROP POLICY IF EXISTS "company_profiles_public_read" ON company_profiles;
    CREATE POLICY "company_profiles_public_read" ON company_profiles FOR SELECT USING (true);
  END IF;
END $$;

-- 2. Enable RLS on alpha_candidates & public read policy
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'alpha_candidates') THEN
    ALTER TABLE alpha_candidates ENABLE ROW LEVEL SECURITY;
    DROP POLICY IF EXISTS "alpha_candidates_public_read" ON alpha_candidates;
    CREATE POLICY "alpha_candidates_public_read" ON alpha_candidates FOR SELECT USING (true);
  END IF;
END $$;

-- 3. client_errors anon INSERT policy & grant
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'client_errors') THEN
    ALTER TABLE client_errors ENABLE ROW LEVEL SECURITY;
    DROP POLICY IF EXISTS "client_errors_anon_insert" ON client_errors;
    CREATE POLICY "client_errors_anon_insert" ON client_errors FOR INSERT TO anon WITH CHECK (char_length(message::text) <= 4000);
    GRANT INSERT ON client_errors TO anon;
  END IF;
END $$;

-- 4. ai_cache RLS & authenticated grants/policies
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'ai_cache') THEN
    ALTER TABLE ai_cache ENABLE ROW LEVEL SECURITY;
    DROP POLICY IF EXISTS "ai_cache_authenticated_select" ON ai_cache;
    CREATE POLICY "ai_cache_authenticated_select" ON ai_cache FOR SELECT TO authenticated USING (true);
    DROP POLICY IF EXISTS "ai_cache_authenticated_insert" ON ai_cache;
    CREATE POLICY "ai_cache_authenticated_insert" ON ai_cache FOR INSERT TO authenticated WITH CHECK (true);
    DROP POLICY IF EXISTS "ai_cache_authenticated_delete" ON ai_cache;
    CREATE POLICY "ai_cache_authenticated_delete" ON ai_cache FOR DELETE TO authenticated USING (true);
    GRANT SELECT, INSERT, DELETE ON ai_cache TO authenticated;
  END IF;
END $$;

-- 5. portfolio_holdings table creation + RLS + user CRUD
CREATE TABLE IF NOT EXISTS portfolio_holdings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  portfolio_id UUID REFERENCES portfolios(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  ticker TEXT,
  isin TEXT,
  name TEXT,
  shares NUMERIC(14,4) NOT NULL DEFAULT 0,
  price NUMERIC(14,4) DEFAULT 0,
  cost_basis NUMERIC(14,4) DEFAULT 0,
  current_price NUMERIC(14,4) DEFAULT 0,
  purchase_date DATE,
  sector TEXT,
  added_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_portfolio_holdings_user_id ON portfolio_holdings(user_id);
CREATE INDEX IF NOT EXISTS idx_portfolio_holdings_portfolio_id ON portfolio_holdings(portfolio_id);

ALTER TABLE portfolio_holdings ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "portfolio_holdings_user_all" ON portfolio_holdings;
CREATE POLICY "portfolio_holdings_user_all" ON portfolio_holdings
  FOR ALL TO authenticated
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

GRANT SELECT, INSERT, UPDATE, DELETE ON portfolio_holdings TO authenticated;

-- 6. user_feedback admin policy update
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'user_feedback') THEN
    DROP POLICY IF EXISTS "feedback_admin_all" ON user_feedback;
    CREATE POLICY "feedback_admin_all" ON user_feedback
      FOR ALL USING (
        EXISTS (SELECT 1 FROM profiles p WHERE p.id = auth.uid() AND p.role = 'admin')
      );
  END IF;
END $$;

COMMENT ON TABLE portfolio_holdings IS 'Direct user stock holdings for rebalancer and portfolio tracking. Migration 077. Diagnostic marker: migration_077_rls_security_hardening.';
