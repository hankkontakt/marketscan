-- MarketScan Security Hardening Migration (Phase 0.3)
-- P0 fixes for Supabase security advisor, RLS policies, function search_path pinning

-- 1. Enable RLS on scan_results (public read-only, service-role write)
ALTER TABLE IF EXISTS public.scan_results ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "scan_results_public_read" ON public.scan_results;
CREATE POLICY "scan_results_public_read" ON public.scan_results
  FOR SELECT
  TO anon, authenticated
  USING (true);

DROP POLICY IF EXISTS "scan_results_service_write" ON public.scan_results;
CREATE POLICY "scan_results_service_write" ON public.scan_results
  FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

-- 2. Enable RLS on pipeline_runs (service/admin only, isolate from public anon)
ALTER TABLE IF EXISTS public.pipeline_runs ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "pipeline_runs_admin_read" ON public.pipeline_runs;
CREATE POLICY "pipeline_runs_admin_read" ON public.pipeline_runs
  FOR SELECT
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM public.profiles
      WHERE profiles.id = auth.uid() AND profiles.role = 'admin'
    )
  );

DROP POLICY IF EXISTS "pipeline_runs_service_all" ON public.pipeline_runs;
CREATE POLICY "pipeline_runs_service_all" ON public.pipeline_runs
  FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

-- 3. Pin function search_path and restrict SECURITY DEFINER execute grants
CREATE OR REPLACE FUNCTION public.clean_ai_cache()
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
BEGIN
  DELETE FROM public.ai_cache
  WHERE created_at < NOW() - INTERVAL '7 days';
END;
$$;

-- Revoke default public execution and grant only to service_role / authenticated
REVOKE EXECUTE ON FUNCTION public.clean_ai_cache() FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION public.clean_ai_cache() FROM anon;
GRANT EXECUTE ON FUNCTION public.clean_ai_cache() TO service_role;

-- 4. Foreign key performance index audits
CREATE INDEX IF NOT EXISTS idx_holdings_portfolio_id ON public.holdings (portfolio_id);
CREATE INDEX IF NOT EXISTS idx_watchlist_user_id ON public.watchlist (user_id);
CREATE INDEX IF NOT EXISTS idx_portfolios_user_id ON public.portfolios (user_id);
