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
    """Service-role client (bypasses RLS — ADMIN USE ONLY).

    WARNING: Bypasses ALL Row Level Security. Provides full read/write
    access to all tables. ALWAYS pair with Depends(require_admin) or
    Depends(get_current_user) in your endpoint signature.
    Never use in public/unauthenticated endpoints.
    """
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
