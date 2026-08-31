"""
Macro regime endpoint — market regime detection & dynamic factor weights.
Connects to backend_worker.macro_regime.
"""
import logging
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from apps.api.dependencies import get_supabase
from apps.api.core.macro import derive_regime_from_scan, classify_macro_regime

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/markets", tags=["macro"])


class RegimeOut(BaseModel):
    regime: str = "NEUTRAL"
    label: str = "Neutral / Balanserad"
    description: str = "Balanserad marknadsregim utan extrema makroavvikelser."
    color: str = "slate"
    scores: dict[str, float] = {}
    weights: dict[str, float] = {}
    inputs: dict = {}


@router.get("/regime", response_model=RegimeOut)
def get_market_regime(sb=Depends(get_supabase)):
    """Get current market regime and dynamic factor weights.
    Derives regime from scan_results aggregate breadth and momentum."""
    try:
        res = sb.table("scan_results").select("trend_signal, entry_signal, change_pct").execute()
        rows = res.data or []

        if rows:
            regime, result = derive_regime_from_scan(rows)
            return RegimeOut(**result)

        # Fallback to default neutral
        _, default_res = classify_macro_regime()
        return RegimeOut(**default_res)

    except Exception as e:
        logger.warning("Failed to detect market regime: %s", e)
        _, default_res = classify_macro_regime()
        return RegimeOut(**default_res)
