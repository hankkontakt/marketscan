"""Sector rotation analysis from the pipeline."""
import logging
from fastapi import APIRouter, Depends
from apps.api.dependencies import get_supabase

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/sector-rotation", tags=["sector-rotation"])


@router.get("")
def get_sector_rotation(sb=Depends(get_supabase)):
    """Latest sector rotation rankings."""
    res = sb.table("sector_rotation").select("*").order("scan_date", desc=True).limit(20).execute()
    return res.data or []
