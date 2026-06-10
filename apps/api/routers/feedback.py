"""
Feedback endpoints — user feedback on UI components.
Spec 13 — M0 Analytics + Feedback.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from apps.api.core.security import get_current_user, User
from apps.api.dependencies import get_user_supabase

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["feedback"])


class FeedbackRequest(BaseModel):
    component: str
    context: str | None = None
    rating: int = Field(..., ge=-1, le=1)
    comment: str | None = None


@router.post("/feedback")
def submit_feedback(
    body: FeedbackRequest,
    user: User = Depends(get_current_user),
    sb_user=Depends(get_user_supabase),
):
    try:
        res = sb_user.table("user_feedback").insert({
            "user_id": user.id,
            "component": body.component,
            "context": body.context,
            "rating": body.rating,
            "comment": body.comment,
        }).execute()
        row = res.data[0] if res.data else {}
        return {"id": row.get("id"), "created_at": row.get("created_at")}
    except Exception as e:
        logger.warning("Failed to save feedback: %s", e)
        raise HTTPException(status_code=500, detail="Kunde inte spara feedback")
