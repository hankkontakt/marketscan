"""Calendar endpoints: earnings, dividends, economic, IPO calendars via Finnhub.
Supports scope=mine|all — mine filters to user's watchlist+portfolio tickers.
"""
import asyncio
import logging
from datetime import date, timedelta
from fastapi import APIRouter, Depends, Query
from httpx import AsyncClient
from apps.api.core.config import settings
from apps.api.dependencies import get_supabase, get_user_supabase
from apps.api.core.security import get_optional_user, User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/calendar", tags=["calendar"])

_MAX_TICKER_FANOUT = 30


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


def _get_user_tickers(sb) -> list[str]:
    """Fetch user's watchlist + portfolio tickers for scope=mine filtering."""
    try:
        watch = sb.table("watchlist").select("ticker").execute()
        portfolio = sb.table("holdings").select("ticker").execute()
        tickers = set()
        for r in (watch.data or []):
            tickers.add(r["ticker"])
        for r in (portfolio.data or []):
            tickers.add(r["ticker"])
        return list(tickers)[:_MAX_TICKER_FANOUT]
    except Exception as e:
        logger.debug("Could not fetch user tickers for calendar: %s", e)
        return []


def _filter_by_tickers(events: list[dict], tickers: set[str]) -> list[dict]:
    """Filter events to only those matching user's tickers."""
    if not tickers:
        return []
    return [e for e in events if e.get("symbol") in tickers]


@router.get("/earnings")
async def get_earnings_calendar(
    from_date: str | None = None,
    to_date: str | None = None,
    scope: str = Query("mine", regex="^(mine|all)$"),
    user: User | None = Depends(get_optional_user),
    sb=Depends(get_user_supabase),
):
    """Upcoming earnings reports.

    scope=mine (default): filter to user's watchlist+portfolio tickers only.
    scope=all: all available earnings (Finnhub global feed, may be sparse).
    Unauthenticated requests always return all events regardless of scope.
    """
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
            events = data.get("earningsCalendar", [])[:100]

        if scope == "mine" and user:
            user_tickers = set(_get_user_tickers(sb))
            if user_tickers:
                events = _filter_by_tickers(events, user_tickers)

        return {"events": events}
    except Exception as e:
        logger.warning("Finnhub earnings calendar failed: %s", e)
        return {"events": []}


@router.get("/ipo")
async def get_ipo_calendar(from_date: str | None = None, to_date: str | None = None):
    """Upcoming IPOs. Always global — no per-ticker filtering."""
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
    scope: str = Query("mine", regex="^(mine|all)$"),
    user: User | None = Depends(get_optional_user),
    sb=Depends(get_user_supabase),
):
    """Dividend calendar.

    scope=mine (default): fetch dividends for user's watchlist+portfolio tickers.
    scope=all: fetch for top-scoring universe tickers.
    Unauthenticated requests fall back to universe tickers regardless of scope.
    """
    if not settings.FINNHUB_API_KEY:
        return {"events": []}
    today = date.today()
    f = from_date or today.isoformat()
    t = to_date or (today + timedelta(days=90)).isoformat()

    # Determine which tickers to fetch dividends for
    if scope == "mine" and user:
        tickers = _get_user_tickers(sb)
    else:
        try:
            tickers_res = (
                sb.table("scan_results")
                .select("ticker")
                .order("score_total", desc=True)
                .limit(25)
                .execute()
            )
            tickers = [r["ticker"] for r in (tickers_res.data or [])]
        except Exception as e:
            logger.warning("Could not fetch universe tickers for dividend calendar: %s", e)
            return {"events": []}

    if not tickers:
        return {"events": []}

    async with AsyncClient(timeout=15.0) as client:
        results = await asyncio.gather(
            *[_fetch_ticker_dividends(client, ticker, f, t) for ticker in tickers],
            return_exceptions=True,
        )

    events: list[dict] = []
    for result in results:
        if isinstance(result, list):
            events.extend(result)

    events.sort(key=lambda x: x.get("date") or x.get("payDate") or "")
    return {"events": events[:60]}


@router.get("/economic")
async def get_economic_calendar(from_date: str | None = None, to_date: str | None = None):
    """Economic events (requires Finnhub premium plan).

    Returns empty list for free-tier users — this is expected behaviour.
    Always global — no per-ticker filtering.
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
