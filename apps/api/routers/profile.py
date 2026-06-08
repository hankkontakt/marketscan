"""
Profile endpoints — user settings, display name, experience level, etc.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from apps.api.dependencies import get_user_supabase, get_supabase_admin
from apps.api.core.security import get_current_user, User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/profile", tags=["profile"])


class ProfileUpdate(BaseModel):
    display_name: str | None = None
    experience_level: str | None = Field(None, pattern="^(beginner|expert)$")
    onboarding_completed: bool | None = None
    theme: str | None = Field(None, pattern="^(light|dark|auto)$")
    email_opt_in: bool | None = None


class ProfileOut(BaseModel):
    id: str
    email: str | None = None
    display_name: str | None = None
    experience_level: str = "beginner"
    onboarding_completed: bool = False
    theme: str = "light"
    email_opt_in: bool = False


@router.put("", response_model=ProfileOut)
def update_profile(
    body: ProfileUpdate,
    user: User = Depends(get_current_user),
    sb=Depends(get_user_supabase),
):
    """Update the current user's profile."""
    updates: dict = {}
    if body.display_name is not None:
        if not body.display_name.strip():
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Visningsnamn kan inte vara tomt")
        updates["display_name"] = body.display_name.strip()
    if body.experience_level is not None:
        updates["experience_level"] = body.experience_level
    if body.onboarding_completed is not None:
        updates["onboarding_completed"] = body.onboarding_completed
    if body.theme is not None:
        updates["theme"] = body.theme
    if body.email_opt_in is not None:
        updates["email_opt_in"] = body.email_opt_in

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

    return _build_profile_out(profile, user.email)


@router.get("", response_model=ProfileOut)
def get_profile(
    user: User = Depends(get_current_user),
    sb=Depends(get_user_supabase),
):
    """Get the current user's profile."""
    res = sb.table("profiles").select("*").eq("id", user.id).limit(1).execute()
    profile = res.data[0] if res.data else {"id": user.id}
    return _build_profile_out(profile, user.email)


def _build_profile_out(profile: dict, email: str | None) -> ProfileOut:
    return ProfileOut(
        id=profile["id"],
        email=email,
        display_name=profile.get("display_name"),
        experience_level=profile.get("experience_level", "beginner"),
        onboarding_completed=profile.get("onboarding_completed", False),
        theme=profile.get("theme", "light"),
        email_opt_in=profile.get("email_opt_in", False),
    )


@router.delete("/account", status_code=204)
def delete_account(
    user: User = Depends(get_current_user),
    sb=Depends(get_user_supabase),
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
        sb.table("notification_preferences").delete().eq("user_id", uid).execute()
        sb.table("notifications").delete().eq("user_id", uid).execute()
        sb.table("transactions").delete().eq("user_id", uid).execute()

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
