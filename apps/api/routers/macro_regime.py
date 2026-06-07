"""
Macro regime endpoint — market regime detection from scan results.
The actual regime detection runs in the pipeline (core/macro_regime.py in stock-scanner-fix).
This endpoint reads the stored regime from pipeline_runs metadata or a dedicated table.
"""
import logging
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from apps.api.dependencies import get_supabase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/markets", tags=["macro"])


class RegimeOut(BaseModel):
    regime: str = "neutral"
    label: str = "Neutral"
    description: str = "Ingen tydlig marknadsregim detekterad."
    color: str = "neutral"


REGIME_MAP = {
    "bull": {"label": "Tjurmarknad", "description": "Positiv marknadsregim med stark momentum. Riskaptiten är hög.", "color": "green"},
    "bear": {"label": "Björnmarknad", "description": "Negativ marknadsregim med svag momentum. Försiktighet rekommenderas.", "color": "red"},
    "uncertain": {"label": "Osäker", "description": "Motstridiga signaler på marknaden. Ingen tydlig riktning.", "color": "amber"},
}


@router.get("/regime", response_model=RegimeOut)
async def get_market_regime(sb=Depends(get_supabase)):
    """Get current market regime (bull/bear/uncertain/neutral).
    Based on the most recent pipeline run's macro analysis."""
    try:
        # Try to read from a pipeline_runs metadata
        # or calculate from aggregate scan data
        result = (
            sb.table("pipeline_runs")
            .select("started_at")
            .eq("run_type", "weekly")
            .eq("status", "success")
            .order("started_at", desc=True)
            .limit(1)
            .execute()
        )

        # Fallback: derive regime from aggregate market data
        # Use aggregate queries instead of fetching all rows
        uptrend_res = sb.table("scan_results").select("ticker", count="exact").eq("trend_signal", "Upptrend").execute()
        downtrend_res = sb.table("scan_results").select("ticker", count="exact").eq("trend_signal", "Nedtrend").execute()
        stark_res = sb.table("scan_results").select("ticker", count="exact").eq("entry_signal", "STARK").execute()
        total_res = sb.table("scan_results").select("ticker", count="exact").execute()

        uptrend = uptrend_res.count or 0
        downtrend = downtrend_res.count or 0
        stark = stark_res.count or 0
        total = total_res.count or 0

        uptrend_pct = uptrend / total if total > 0 else 0
        downtrend_pct = downtrend / total if total > 0 else 0

        if uptrend_pct > 0.35 and stark / total > 0.15:
            regime = "bull"
        elif downtrend_pct > 0.30:
            regime = "bear"
        elif abs(uptrend_pct - downtrend_pct) < 0.10:
            regime = "uncertain"
        else:
            return RegimeOut()

        info = REGIME_MAP[regime]
        return RegimeOut(regime=regime, **info)

    except Exception as e:
        logger.warning("Failed to detect market regime: %s", e)
        return RegimeOut()
