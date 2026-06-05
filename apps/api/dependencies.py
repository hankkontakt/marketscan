"""
FastAPI dependency injection — Supabase client per request (stateless).
Vercel spins up/down: no module-level state.
"""
from functools import lru_cache
from supabase import create_client, Client
from apps.api.core.config import settings


def get_supabase() -> Client:
    """Public Supabase client (anon key, RLS enforced)."""
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)


def get_supabase_admin() -> Client:
    """Service-role client (bypasses RLS — pipeline/admin use only)."""
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
