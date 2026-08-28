-- Migration 038: TEMP - isolate signup bug.
-- Drop the on_auth_user_created trigger (Supabase: signup 500 often = broken trigger).
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
