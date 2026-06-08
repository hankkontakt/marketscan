-- ============================================================================
-- 023_grant_table_privileges.sql
-- ----------------------------------------------------------------------------
-- ROTORSAK: Tabeller skapade via SQL-migrationer fick ALDRIG table-privilegier
-- (GRANT) till Supabase-rollerna `authenticated`/`anon`. RLS var aktiverat,
-- men GRANT-lagret UNDER RLS saknades. Resultat:
--
--   permission denied for table portfolios  (Postgres-fel 42501)
--
-- för varje user-data-endpoint som använder `get_user_supabase` (authenticated
-- + JWT). Importen var bara det första stället det syntes — watchlist, alerts,
-- saved_screens, portfolio osv. drabbas av exakt samma fel.
--
-- SÄKERHET: GRANT är den grova grinden; RLS är den fina per-rad-filtreringen.
-- Att ge `authenticated` CRUD på en RLS-skyddad tabell är säkert — utan en
-- tillåtande policy nekar RLS ändå åtkomsten (default-deny). De 3 tabeller som
-- SAKNAR RLS (scan_results, ai_cache, pipeline_runs) får därför ENBART läsrätt;
-- skrivning sker via service_role (som kringgår GRANT) i pipelinen.
--
-- Kör i Supabase SQL Editor. Idempotent — säker att köra om.
-- ============================================================================

-- Schemat måste vara åtkomligt för båda rollerna.
GRANT USAGE ON SCHEMA public TO anon, authenticated;

-- ── Bred baslinje ───────────────────────────────────────────────────────────
-- authenticated: full CRUD på alla tabeller. RLS begränsar till egna rader.
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO authenticated;

-- anon: endast läsning (RLS gäller fortfarande; publika tabeller utan RLS,
-- t.ex. scan_results, är avsedda att vara läsbara).
GRANT SELECT ON ALL TABLES IN SCHEMA public TO anon;

-- Sekvenser (för ev. SERIAL/identity-PK:er).
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO anon, authenticated;

-- ── Härda de 3 tabellerna UTAN RLS ──────────────────────────────────────────
-- Dessa har ingen RLS, så GRANT är enda skyddet. Användare får ALDRIG skriva
-- till dem — det görs av pipelinen via service_role.
REVOKE INSERT, UPDATE, DELETE ON public.scan_results  FROM anon, authenticated;
REVOKE INSERT, UPDATE, DELETE ON public.ai_cache       FROM anon, authenticated;
REVOKE INSERT, UPDATE, DELETE ON public.pipeline_runs  FROM anon, authenticated;

-- ── Framtida tabeller ärver vettiga defaults ────────────────────────────────
-- Så att nästa migration inte återskapar 42501-problemet.
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO authenticated;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT SELECT ON TABLES TO anon;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO anon, authenticated;

-- ── Verifiering (kör manuellt vid behov) ────────────────────────────────────
-- SELECT grantee, table_name, privilege_type
-- FROM information_schema.role_table_grants
-- WHERE table_schema = 'public' AND table_name = 'portfolios'
-- ORDER BY grantee, privilege_type;
