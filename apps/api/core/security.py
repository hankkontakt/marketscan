"""
JWT validation — validates Supabase-issued tokens.

Primary:  local HS256 check against SUPABASE_JWT_SECRET (no network roundtrip).
Fallback: if SUPABASE_JWT_SECRET is not configured, validate via Supabase API.

Admin check reads role from profiles table (not from JWT, where it is
always "authenticated"). Requires a supabase-admin client to bypass RLS.
"""
import logging
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


def _decode_via_supabase_api(token: str) -> dict:
    """Fallback: validate token by calling Supabase auth.getUser().
    Used when SUPABASE_JWT_SECRET is not configured.
    Adds ~100 ms network latency per request but is always correct.
    """
    try:
        from supabase import create_client
        sb = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
        resp = sb.auth.get_user(token)
        user = resp.user
        if not user:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Ogiltig token")
        return {"sub": user.id, "email": user.email}
    except HTTPException:
        raise
    except Exception as exc:
        logger.debug("Supabase API token validation failed: %s", exc)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Ogiltig token")


def _decode(token: str) -> dict:
    secret = settings.SUPABASE_JWT_SECRET
    if not secret:
        # JWT secret not configured — fall back to Supabase API validation
        logger.warning(
            "SUPABASE_JWT_SECRET is not set; falling back to Supabase API token "
            "validation (slower). Set the env var for fast local validation."
        )
        return _decode_via_supabase_api(token)
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
        # Local decode failed — could be a wrong secret; try Supabase API as last resort
        logger.debug("Local JWT decode failed, trying Supabase API fallback")
        return _decode_via_supabase_api(token)


async def get_current_user(
    cred: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> User:
    if not cred:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Autentisering krävs")
    payload = _decode(cred.credentials)
    uid = payload.get("sub")
    if not uid:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token saknar sub")
    return User(id=uid, email=payload.get("email"), role=payload.get("role", "user"))


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
    """Verify that the authenticated user has the 'admin' role in profiles table.

    Reads from profiles (via service-role client) so the check is against the
    database value — not the JWT claim, which is always 'authenticated'.
    """
    from apps.api.dependencies import get_supabase_admin
    sb_admin = get_supabase_admin()
    try:
        profile = (
            sb_admin.table("profiles")
            .select("role")
            .eq("id", user.id)
            .single()
            .execute()
        )
        if not profile.data or profile.data.get("role") != "admin":
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin-behörighet krävs")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin-behörighet krävs")
    return user
