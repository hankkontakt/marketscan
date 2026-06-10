"""Tracking endpoints — self-hosted analytics events."""
from __future__ import annotations
import logging
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from supabase import Client
from apps.api.dependencies import get_supabase

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["tracking"])


class TrackEvent(BaseModel):
    name: str
    props: dict = Field(default_factory=dict)


class TrackBatchRequest(BaseModel):
    events: list[TrackEvent]


@router.post("/tracking/events")
def track_events(
    body: TrackBatchRequest,
    request: Request,
    sb: Client = Depends(get_supabase),
):
    """Accept a batch of tracking events and store them."""
    for event in body.events:
        try:
            sb.table("tracking_events").insert({
                "event_name": event.name,
                "props": event.props,
            }).execute()
        except Exception as e:
            logger.debug("Failed to track event %s: %s", event.name, e)
    return {"ok": True, "count": len(body.events)}
