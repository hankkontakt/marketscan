"""
JWT validation — validates Supabase-issued tokens.

Primary:  local HS256 check against SUPABASE_JWT_SECRET (no network roundtrip).
Fallback: if the secret is missing or wrong, validate via async httpx call to
          Supabase REST API.  This path is ~100 ms slower but never blocks the
          event loop (unlike the old synchronous supabase-python SDK approach).

Admin role resolution (two sources, first match wins):
  1. JWT fast path — app_metadata.role == "admin" extracted directly from the
     token payload. Set this via SQL (service_role only, user cannot forge it):
       UPDATE auth.users
       SET raw_app_meta_data = raw_app_meta_data || '{"role":"admin"}'
       WHERE email = 'your@email.com';
     User must re-login after this SQL for the new JWT to carry the claim.
  2. DB slow path — profiles.role == "admin" column.  Wrapped in asyncio.to_thread
     so the synchronous Supabase SDK never blocks the event loop.
"""
import logging
import httpx
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from apps.api.core.config import settings

logger = logging.getLogger(__name__)

_bearer = HTTPBearer(auto_error=False)


class User(BaseModel):
    id: str
    email: str | None = None
    role: str = "user"


async def _validate_via_supabase_api(token: str) -> dict:
    """Async fallback: call Supabase /auth/v1/user to validate the token.

    Uses httpx so the event loop is never blocked.  Only called when the
    local HS256 decode fails (wrong/missing SUPABASE_JWT_SECRET).
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{settings.SUPABASE_URL}/auth/v1/user",
                headers={
                    "Authorization": f"Bearer {token}",
                    "apikey": settings.SUPABASE_ANON_KEY,
                },
            )
        if resp.status_code != 200:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Ogiltig token")
        data = resp.json()
        uid = data.get("id")
        if not uid:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Ogiltig token")
        # Include app_metadata so require_admin can use the JWT fast path
        return {
            "sub": uid,
            "email": data.get("email"),
            "app_metadata": data.get("app_metadata") or {},
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.debug("Supabase API token validation failed: %s", exc)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Ogiltig token")


async def _decode(token: str) -> dict:
    """Decode and validate a Supabase JWT.  Async to support the API fallback."""
    secret = settings.SUPABASE_JWT_SECRET
    if not secret:
        logger.warning(
            "SUPABASE_JWT_SECRET is not set; using Supabase API fallback. "
            "Set the env var for fast local validation."
        )
        return await _validate_via_supabase_api(token)
    try:
        return jwt.decode(
            token,
            secret,
            audience="authenticated",
            algorithms=["HS256"],
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token har gått ut")
    except jwt.PyJWTError:
        # Wrong secret or malformed token — try the API as a last resort.
        logger.debug("Local JWT decode failed, trying Supabase API fallback")
        return await _validate_via_supabase_api(token)


async def get_current_user(
    cred: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> User:
    if not cred:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Autentisering krävs")
    payload = await _decode(cred.credentials)
    uid = payload.get("sub")
    if not uid:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token saknar sub")
    # Extract the app-level role from app_metadata (can only be set via service_role,
    # not by the user themselves — safe to trust). Falls back to "user".
    # Note: payload.get("role") is always "authenticated" (PostgREST role) — not the app role.
    app_metadata = payload.get("app_metadata") or {}
    app_role = app_metadata.get("role") or "user"
    return User(id=uid, email=payload.get("email"), role=app_role)


async def get_optional_user(
    cred: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> User | None:
    if not cred:
        return None
    try:
        return await get_current_user(cred)
    except HTTPException:
        return None


async def require_admin(user: User = Depends(get_current_user)) -> User:
    """Verify that the authenticated user has admin role.

    Fast path: role already extracted from app_metadata in the JWT (set via
    Supabase SQL: UPDATE auth.users SET raw_app_meta_data = raw_app_meta_data ||
    '{"role":"admin"}' WHERE email = '...').  This is the preferred method —
    no extra DB roundtrip needed.

    Slow path (fallback): check profiles.role column.  Wrapped in
    asyncio.to_thread so the sync Supabase SDK never blocks the event loop.
    """
    # ── Fast path: role in JWT app_metadata ──────────────────────────────
    if user.role == "admin":
        return user

    # ── Slow path: check profiles table ──────────────────────────────────
    import asyncio
    from apps.api.dependencies import get_supabase_admin
    sb_admin = get_supabase_admin()
    try:
        profile = await asyncio.to_thread(
            lambda: (
                sb_admin.table("profiles")
                .select("role")
                .eq("id", user.id)
                .single()
                .execute()
            )
        )
        if not profile.data or profile.data.get("role") != "admin":
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin-behörighet krävs")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin-behörighet krävs")
    return user
