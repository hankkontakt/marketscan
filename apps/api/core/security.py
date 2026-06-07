"""
Local JWT validation — no network roundtrip per request.
Validates Supabase-issued HS256 tokens against SUPABASE_JWT_SECRET.

Admin check reads role from profiles table (not from JWT, where it is
always "authenticated"). Requires a supabase-admin client to bypass RLS.
"""
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from apps.api.core.config import settings

_bearer = HTTPBearer(auto_error=False)


class User(BaseModel):
    id: str
    email: str | None = None
    role: str = "user"


def _decode(token: str) -> dict:
    try:
        return jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            audience="authenticated",
            algorithms=["HS256"],
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token har gått ut")
    except jwt.PyJWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Ogiltig token")


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
