"""Saved screener views — per-user filter presets."""
from fastapi import APIRouter, Depends, HTTPException, status
from apps.api.dependencies import get_supabase
from apps.api.core.security import get_current_user, User
from apps.api.schemas.portfolio import SavedScreenIn, SavedScreenOut

router = APIRouter(prefix="/api/screens", tags=["saved_screens"])


@router.get("", response_model=list[SavedScreenOut])
async def get_saved_screens(user: User = Depends(get_current_user), sb=Depends(get_supabase)):
    res = sb.table("saved_screens").select("*").eq("user_id", user.id).order("created_at").execute()
    return res.data or []


@router.post("", response_model=SavedScreenOut, status_code=201)
async def save_screen(
    body: SavedScreenIn, user: User = Depends(get_current_user), sb=Depends(get_supabase)
):
    res = sb.table("saved_screens").insert({
        "user_id": user.id, "name": body.name, "filter_json": body.filter_json
    }).execute()
    return res.data[0]


@router.delete("/{screen_id}", status_code=204)
async def delete_screen(
    screen_id: str, user: User = Depends(get_current_user), sb=Depends(get_supabase)
):
    res = sb.table("saved_screens").delete().eq("id", screen_id).execute()
    if not res.data:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Vyn hittades inte")
