"""ML predictions from the XGBoost model pipeline."""
import logging
from fastapi import APIRouter, Depends, Query
from apps.api.dependencies import get_supabase
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/predictions", tags=["predictions"])


class MLPredictionOut(BaseModel):
    ticker: str
    predicted_return: float | None = None
    ml_rank: int | None = None
    model_version: str | None = None
    sector: str | None = None


@router.get("", response_model=list[MLPredictionOut])
async def get_predictions(
    limit: int = Query(50, le=200),
    sb=Depends(get_supabase),
):
    """Latest ML predictions sorted by predicted return."""
    res = sb.table("ml_predictions").select("*").order("predicted_return", desc=True).limit(limit).execute()
    return res.data or []


@router.get("/{ticker}", response_model=MLPredictionOut | None)
async def get_ticker_prediction(ticker: str, sb=Depends(get_supabase)):
    """ML prediction for a single ticker."""
    res = sb.table("ml_predictions").select("*").eq("ticker", ticker.upper()).limit(1).execute()
    return res.data[0] if res.data else None
