"""
Profile endpoints — user settings, display name, etc.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from apps.api.dependencies import get_supabase, get_supabase_admin
from apps.api.core.security import get_current_user, User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/profile", tags=["profile"])


class ProfileUpdate(BaseModel):
    display_name: str | None = None


class ProfileOut(BaseModel):
    id: str
    email: str | None = None
    display_name: str | None = None


@router.put("", response_model=ProfileOut)
async def update_profile(
    body: ProfileUpdate,
    user: User = Depends(get_current_user),
    sb=Depends(get_supabase),
):
    """Update the current user's profile (display name)."""
    updates: dict = {}
    if body.display_name is not None:
        if not body.display_name.strip():
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Visningsnamn kan inte vara tomt")
        updates["display_name"] = body.display_name.strip()

    try:
        if updates:
            sb.table("profiles").update(updates).eq("id", user.id).execute()
        else:
            sb.table("profiles").upsert({"id": user.id}, ignore_duplicates="id").execute()
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Kunde inte uppdatera profil: {str(e)}")

    # Fetch the updated profile
    res = sb.table("profiles").select("*").eq("id", user.id).limit(1).execute()
    profile = res.data[0] if res.data else {"id": user.id}

    return ProfileOut(
        id=profile["id"],
        email=user.email,
        display_name=profile.get("display_name"),
    )


@router.get("", response_model=ProfileOut)
async def get_profile(
    user: User = Depends(get_current_user),
    sb=Depends(get_supabase),
):
    """Get the current user's profile."""
    res = sb.table("profiles").select("*").eq("id", user.id).limit(1).execute()
    profile = res.data[0] if res.data else {"id": user.id}
    return ProfileOut(
        id=profile["id"],
        email=user.email,
        display_name=profile.get("display_name"),
    )


@router.delete("/account", status_code=204)
async def delete_account(
    user: User = Depends(get_current_user),
    sb=Depends(get_supabase),
    sb_admin=Depends(get_supabase_admin),
):
    """Delete the user's account and all associated data (GDPR)."""
    uid = user.id
    logger.info("Deleting account %s", uid)

    try:
        # Delete in order (foreign keys)
        sb.table("price_alerts").delete().eq("user_id", uid).execute()
        sb.table("watchlist").delete().eq("user_id", uid).execute()
        sb.table("portfolio_snapshots").delete().eq("user_id", uid).execute()

        # Delete holdings then portfolio
        port = sb.table("portfolios").select("id").eq("user_id", uid).limit(1).execute()
        if port.data:
            pid = port.data[0]["id"]
            sb.table("holdings").delete().eq("portfolio_id", pid).execute()
            sb.table("portfolios").delete().eq("id", pid).execute()

        # Delete saved screens, profile
        sb.table("saved_screens").delete().eq("user_id", uid).execute()
        sb.table("profiles").delete().eq("id", uid).execute()

        # Delete the auth user (admin client required)
        sb_admin.auth.admin.delete_user(uid)
    except Exception as e:
        logger.error("Failed to delete account %s: %s", uid, str(e))
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Kunde inte ta bort kontot. Försök igen eller kontakta support.",
        )
