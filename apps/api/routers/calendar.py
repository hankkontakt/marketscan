"""Calendar endpoints: earnings, dividends, economic, IPO calendars via Finnhub."""
import logging
from datetime import date, timedelta
from fastapi import APIRouter
from httpx import AsyncClient
from apps.api.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/calendar", tags=["calendar"])


@router.get("/earnings")
async def get_earnings_calendar(from_date: str | None = None, to_date: str | None = None):
    """Upcoming earnings reports."""
    if not settings.FINNHUB_API_KEY:
        return {"events": []}
    today = date.today()
    f = from_date or today.isoformat()
    t = to_date or (today + timedelta(days=30)).isoformat()
    try:
        async with AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                "https://finnhub.io/api/v1/calendar/earnings",
                params={"from": f, "to": t, "symbol": ""},
                headers={"X-Finnhub-Token": settings.FINNHUB_API_KEY},
            )
            resp.raise_for_status()
            data = resp.json()
            return {"events": data.get("earningsCalendar", [])[:50]}
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
async def get_dividends_calendar(from_date: str | None = None, to_date: str | None = None):
    """Upcoming dividend payments."""
    if not settings.FINNHUB_API_KEY:
        return {"events": []}
    today = date.today()
    f = from_date or today.isoformat()
    t = to_date or (today + timedelta(days=90)).isoformat()
    try:
        async with AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                "https://finnhub.io/api/v1/stock/dividend-calendar",
                params={"from": f, "to": t},
                headers={"X-Finnhub-Token": settings.FINNHUB_API_KEY},
            )
            resp.raise_for_status()
            data = resp.json()
            return {"events": data[:50]} if isinstance(data, list) else {"events": []}
    except Exception as e:
        logger.warning("Finnhub dividend calendar failed: %s", e)
        return {"events": []}


@router.get("/economic")
async def get_economic_calendar(from_date: str | None = None, to_date: str | None = None):
    """Economic events (central bank decisions, CPI, etc.)."""
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
        logger.warning("Finnhub economic calendar failed: %s", e)
        return {"events": []}
