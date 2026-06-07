"""
Insider trades API — combines Finnhub data with FI (Finansinspektionen) data.
"""
import logging
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from datetime import date, timedelta
from apps.api.dependencies import get_supabase
from apps.api.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/stocks", tags=["stocks"])


class InsiderTradeOut(BaseModel):
    name: str | None = None
    role: str | None = None
    type: str | None = None
    shares: float | None = None
    amount: float | None = None
    trade_date: str | None = None
    source: str = "finnhub"


class InsiderTradesResponse(BaseModel):
    ticker: str
    insider_trades: list[InsiderTradeOut]
    has_fi_data: bool = False


@router.get("/{ticker}/insider", response_model=InsiderTradesResponse)
async def get_insider_trades(ticker: str, sb=Depends(get_supabase)):
    """Get insider trades from both Finnhub and FI data."""
    t = ticker.upper().strip()
    all_trades: list[InsiderTradeOut] = []

    # 1. Try local FI data (enriched by pipeline)
    try:
        thirty_days_ago = (date.today() - timedelta(days=90)).isoformat()
        res = (
            sb.table("insider_trades")
            .select("*")
            .eq("ticker", t)
            .gte("trade_date", thirty_days_ago)
            .order("trade_date", desc=True)
            .limit(20)
            .execute()
        )
        fi_trades = res.data or []
        for item in fi_trades:
            all_trades.append(InsiderTradeOut(
                name=item.get("name"),
                role=item.get("role"),
                type=item.get("type"),
                shares=float(item["shares"]) if item.get("shares") else None,
                amount=float(item["amount"]) if item.get("amount") else None,
                trade_date=item.get("trade_date"),
                source="fi",
            ))
    except Exception as e:
        logger.debug("FI insider data unavailable for %s: %s", t, e)

    has_fi = len(all_trades) > 0

    # 2. Try Finnhub as fallback
    if not has_fi and settings.FINNHUB_API_KEY:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"https://finnhub.io/api/v1/stock/insider-transactions?symbol={t}",
                    headers={"X-Finnhub-Token": settings.FINNHUB_API_KEY},
                )
                resp.raise_for_status()
                data = resp.json()
                for item in (data.get("data", []) or [])[:15]:
                    all_trades.append(InsiderTradeOut(
                        name=item.get("name"),
                        role=item.get("position"),  # Finnhub field for insider role
                        type=item.get("transactionCode"),
                        shares=item.get("share"),
                        amount=item.get("change"),
                        trade_date=item.get("transactionDate"),
                        source="finnhub",
                    ))
        except Exception as e:
            logger.debug("Finnhub insider data unavailable for %s: %s", t, e)

    return InsiderTradesResponse(
        ticker=t,
        insider_trades=all_trades[:20],
        has_fi_data=has_fi,
    )
