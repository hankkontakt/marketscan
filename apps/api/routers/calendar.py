"""Calendar endpoints: earnings, dividends, economic, IPO calendars via Finnhub."""
import asyncio
import logging
from datetime import date, timedelta
from fastapi import APIRouter, Depends
from httpx import AsyncClient
from apps.api.core.config import settings
from apps.api.dependencies import get_supabase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/calendar", tags=["calendar"])

# Max universe tickers to fetch dividends for (avoids hitting rate limits)
_DIVIDEND_UNIVERSE_LIMIT = 25


async def _fetch_ticker_dividends(
    client: AsyncClient, ticker: str, f: str, t: str
) -> list[dict]:
    """Fetch dividend history for a single ticker from Finnhub."""
    try:
        resp = await client.get(
            "https://finnhub.io/api/v1/stock/dividend2",
            params={"symbol": ticker, "from": f, "to": t},
            headers={"X-Finnhub-Token": settings.FINNHUB_API_KEY},
        )
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, list):
            return [
                {
                    "symbol": ticker,
                    "date": item.get("date"),
                    "payDate": item.get("payDate"),
                    "exDate": item.get("exDate"),
                    "amount": item.get("amount"),
                    "frequency": item.get("freq"),
                }
                for item in data
                if item.get("date") or item.get("payDate")
            ]
    except Exception as e:
        logger.debug("Dividend fetch failed for %s: %s", ticker, e)
    return []


@router.get("/earnings")
async def get_earnings_calendar(from_date: str | None = None, to_date: str | None = None):
    """Upcoming earnings reports (free Finnhub tier — global results)."""
    if not settings.FINNHUB_API_KEY:
        return {"events": []}
    today = date.today()
    f = from_date or today.isoformat()
    t = to_date or (today + timedelta(days=30)).isoformat()
    try:
        async with AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                "https://finnhub.io/api/v1/calendar/earnings",
                params={"from": f, "to": t},
                headers={"X-Finnhub-Token": settings.FINNHUB_API_KEY},
            )
            resp.raise_for_status()
            data = resp.json()
            events = data.get("earningsCalendar", [])
            return {"events": events[:100]}
    except Exception as e:
        logger.warning("Finnhub earnings calendar failed: %s", e)
        return {"events": []}


@router.get("/ipo")
async def get_ipo_calendar(from_date: str | None = None, to_date: str | None = None):
    """Upcoming IPOs."""
    if not settings.FINNHUB_API_KEY:
        return {"events": []}
    today = date.today()
    f = from_date or today.isoformat()
    t = to_date or (today + timedelta(days=90)).isoformat()
    try:
        async with AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                "https://finnhub.io/api/v1/calendar/ipo",
                params={"from": f, "to": t},
                headers={"X-Finnhub-Token": settings.FINNHUB_API_KEY},
            )
            resp.raise_for_status()
            data = resp.json()
            return {"events": data.get("ipoCalendar", [])[:30]}
    except Exception as e:
        logger.warning("Finnhub IPO calendar failed: %s", e)
        return {"events": []}


@router.get("/dividends")
async def get_dividends_calendar(
    from_date: str | None = None,
    to_date: str | None = None,
    sb=Depends(get_supabase),
):
    """Dividend calendar: fetches dividends for top universe stocks.

    Finnhub has no global dividend calendar endpoint on the free tier.
    We fetch per-ticker dividends for the highest-scoring stocks in the universe.
    """
    if not settings.FINNHUB_API_KEY:
        return {"events": []}
    today = date.today()
    f = from_date or today.isoformat()
    t = to_date or (today + timedelta(days=90)).isoformat()

    # Pick the top-scoring tickers from the universe
    try:
        tickers_res = (
            sb.table("scan_results")
            .select("ticker")
            .order("score_total", desc=True)
            .limit(_DIVIDEND_UNIVERSE_LIMIT)
            .execute()
        )
        tickers = [r["ticker"] for r in (tickers_res.data or [])]
    except Exception as e:
        logger.warning("Could not fetch universe tickers for dividend calendar: %s", e)
        return {"events": []}

    if not tickers:
        return {"events": []}

    # Parallel-fetch dividends for each ticker
    async with AsyncClient(timeout=15.0) as client:
        results = await asyncio.gather(
            *[_fetch_ticker_dividends(client, ticker, f, t) for ticker in tickers],
            return_exceptions=True,
        )

    events: list[dict] = []
    for result in results:
        if isinstance(result, list):
            events.extend(result)

    # Sort by pay date / ex-date
    events.sort(key=lambda x: x.get("date") or x.get("payDate") or "")
    return {"events": events[:60]}


@router.get("/economic")
async def get_economic_calendar(from_date: str | None = None, to_date: str | None = None):
    """Economic events (requires Finnhub premium plan).

    Returns empty list for free-tier users — this is expected behaviour.
    """
    if not settings.FINNHUB_API_KEY:
        return {"events": []}
    today = date.today()
    f = from_date or today.isoformat()
    t = to_date or (today + timedelta(days=30)).isoformat()
    try:
        async with AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                "https://finnhub.io/api/v1/calendar/economic",
                params={"from": f, "to": t},
                headers={"X-Finnhub-Token": settings.FINNHUB_API_KEY},
            )
            resp.raise_for_status()
            data = resp.json()
            return {"events": data.get("economicCalendar", [])[:50]}
    except Exception as e:
        logger.warning("Finnhub economic calendar failed (premium required on free tier): %s", e)
        return {"events": []}
