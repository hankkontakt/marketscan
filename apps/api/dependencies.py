"""
FastAPI dependency injection — Supabase client per request (stateless).
Vercel spins up/down: no module-level state.

Three client tiers:
  get_supabase()           — anon key; for fully public endpoints (screener, stocks)
  get_user_supabase()      — anon key + JWT forwarded to PostgREST; enables auth.uid() in RLS
  get_supabase_admin()     — service-role key; bypasses RLS; ADMIN/cron only
"""
from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import create_client, Client
from apps.api.core.config import settings

_bearer = HTTPBearer(auto_error=False)


def get_supabase() -> Client:
    """Public Supabase client (anon key, RLS enforced).
    Use only for fully public endpoints that need no user context.
    """
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)


def get_user_supabase(
    cred: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> Client:
    """Supabase client with user JWT forwarded to PostgREST.

    This makes auth.uid() return the real user ID in Postgres, so RLS
    policies can enforce per-user isolation. Use in ALL user-data endpoints
    (portfolio, watchlist, alerts, saved_screens, profile, snapshots).
    """
    client = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
    if cred and cred.credentials:
        client.postgrest.auth(cred.credentials)
    return client


def get_supabase_admin() -> Client:
    """Service-role client (bypasses RLS — ADMIN/cron USE ONLY).

    WARNING: Bypasses ALL Row Level Security. Provides full read/write
    access to all tables. ALWAYS pair with Depends(require_admin) or
    Depends(get_current_user) in your endpoint signature.
    Never use in public/unauthenticated endpoints.
    """
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
