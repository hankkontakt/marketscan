-- Migration 039: Robust handle_new_user-trigger.
-- Ersätter trigger-funktionen med felavskärmning per INSERT (try/catch),
-- så att GoTrue signup ALDRIG kraschar av en rad som faller.
-- Göra det: varje INSERT isoleras med EXCEPTION + NOTICE (loggas i Postgres).
CREATE OR REPLACE FUNCTION public.handle_new_user() RETURNS trigger
  LANGUAGE plpgsql SECURITY DEFINER
  SET search_path = public AS $$
BEGIN
  BEGIN
    INSERT INTO profiles (id, display_name) VALUES (NEW.id, NEW.email)
      ON CONFLICT (id) DO NOTHING;
  EXCEPTION WHEN others THEN
    RAISE NOTICE 'handle_new_user: profiles insert failed: %', SQLERRM;
  END;
  BEGIN
    INSERT INTO portfolios (user_id, name) VALUES (NEW.id, 'Min portfölj')
      ON CONFLICT DO NOTHING;
  EXCEPTION WHEN others THEN
    RAISE NOTICE 'handle_new_user: portfolios insert failed: %', SQLERRM;
  END;
  BEGIN
    INSERT INTO notification_preferences (user_id) VALUES (NEW.id)
      ON CONFLICT (user_id) DO NOTHING;
  EXCEPTION WHEN others THEN
    RAISE NOTICE 'handle_new_user: notification_preferences insert failed: %', SQLERRM;
  END;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();
