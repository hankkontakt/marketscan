"""
Notifications API — in-app notification center.
RLS-protected: users can only see their own notifications.
"""
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from apps.api.dependencies import get_user_supabase
from apps.api.core.security import get_current_user, User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


class NotificationOut(BaseModel):
    id: str
    type: str
    title: str
    body: str | None = None
    link: str | None = None
    read_at: str | None = None
    created_at: str


class UnreadCountOut(BaseModel):
    count: int


@router.get("", response_model=list[NotificationOut])
def get_notifications(
    user: User = Depends(get_current_user),
    sb=Depends(get_user_supabase),
):
    """Get latest 50 notifications for current user."""
    res = (
        sb.table("notifications")
        .select("*")
        .eq("user_id", user.id)
        .order("created_at", desc=True)
        .limit(50)
        .execute()
    )
    return [_format_notification(n) for n in (res.data or [])]


@router.get("/unread", response_model=UnreadCountOut)
def get_unread_count(
    user: User = Depends(get_current_user),
    sb=Depends(get_user_supabase),
):
    """Get count of unread notifications."""
    res = (
        sb.table("notifications")
        .select("id", count="exact")
        .eq("user_id", user.id)
        .is_("read_at", "null")
        .execute()
    )
    return UnreadCountOut(count=res.count or 0)


@router.post("/{notification_id}/read", status_code=204)
def mark_read(
    notification_id: str,
    user: User = Depends(get_current_user),
    sb=Depends(get_user_supabase),
):
    """Mark a single notification as read."""
    now = datetime.now(timezone.utc).isoformat()
    res = (
        sb.table("notifications")
        .update({"read_at": now})
        .eq("id", notification_id)
        .eq("user_id", user.id)
        .execute()
    )
    if not res.data:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Notisen hittades inte")


@router.post("/read-all", status_code=204)
def mark_all_read(
    user: User = Depends(get_current_user),
    sb=Depends(get_user_supabase),
):
    """Mark all unread notifications as read."""
    now = datetime.now(timezone.utc).isoformat()
    sb.table("notifications").update({"read_at": now}).eq("user_id", user.id).is_("read_at", "null").execute()


def _format_notification(n: dict) -> NotificationOut:
    return NotificationOut(
        id=n["id"],
        type=n["type"],
        title=n["title"],
        body=n.get("body"),
        link=n.get("link"),
        read_at=n.get("read_at"),
        created_at=n.get("created_at", ""),
    )


# ─── Notisinställningar (Spec 09) ─────────────────────────────────────────────

class NotificationPrefs(BaseModel):
    on_new_stark: bool = True
    on_score_move: bool = True
    on_insider_cluster: bool = True
    on_mews_flag: bool = True
    on_earnings_memo: bool = True
    score_move_threshold: int = 15
    email_enabled: bool = False


@router.get("/prefs", response_model=NotificationPrefs)
def get_prefs(user: User = Depends(get_current_user), sb=Depends(get_user_supabase)):
    """Hämta egna notisinställningar (default om ingen rad finns)."""
    res = sb.table("notification_prefs").select("*").eq("user_id", user.id).limit(1).execute()
    if res.data:
        return NotificationPrefs(**{k: v for k, v in res.data[0].items() if k in NotificationPrefs.model_fields})
    return NotificationPrefs()


@router.put("/prefs", response_model=NotificationPrefs)
def update_prefs(
    prefs: NotificationPrefs,
    user: User = Depends(get_current_user),
    sb=Depends(get_user_supabase),
):
    """Spara egna notisinställningar (upsert, RLS-skyddat)."""
    payload = {"user_id": user.id, **prefs.model_dump()}
    sb.table("notification_prefs").upsert(payload, on_conflict="user_id").execute()
    return prefs
