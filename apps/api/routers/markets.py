"""
Sector and global market data endpoints.
Sector heatmap from scan_results, global indices via Finnhub (primary)
or yfinance (fallback when FINNHUB_API_KEY is not set).
"""
import asyncio
import logging
import time
import httpx
from fastapi import APIRouter, Depends
from apps.api.dependencies import get_supabase
from apps.api.core.config import settings
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/markets", tags=["markets"])

# Simple in-memory cache for Finnhub indices (300s = 5 min)
_indices_cache: dict = {"data": None, "expires": 0}


def _get_cached_indices() -> list | None:
    if _indices_cache["data"] and time.time() < _indices_cache["expires"]:
        return _indices_cache["data"]
    return None


def _set_cached_indices(data: list):
    _indices_cache["data"] = data
    _indices_cache["expires"] = time.time() + 300


class SectorSummary(BaseModel):
    sector: str
    count: int
    avg_score: float
    avg_momentum: float
    avg_value: float | None = None
    avg_quality: float | None = None
    avg_growth: float | None = None
    avg_risk: float | None = None
    top_ticker: str | None = None
    top_score: float | None = None
    stark_count: int = 0
    ok_count: int = 0
    vanta_count: int = 0


class SectorOverviewOut(BaseModel):
    sectors: list[SectorSummary]
    total_tickers: int
    scan_date: str | None = None


@router.get("/sectors", response_model=SectorOverviewOut)
async def get_sector_overview(sb=Depends(get_supabase)):
    """Aggregated sector data for heatmap/overview."""
    result = sb.table("scan_results").select(
        "sector, score_total, score_momentum, score_value, score_quality, "
        "score_growth, score_risk, entry_signal, ticker, scan_date"
    ).execute()

    rows = result.data or []
    if not rows:
        return SectorOverviewOut(sectors=[], total_tickers=0, scan_date=None)

    scan_date = rows[0].get("scan_date") if rows else None

    from collections import defaultdict
    sectors: dict[str, dict] = defaultdict(lambda: {
        "count": 0, "scores": [], "momentums": [], "score_values": [],
        "score_qualities": [], "score_growths": [], "score_risks": [],
        "signals": defaultdict(int), "top_ticker": None, "top_score": 0,
    })

    for r in rows:
        sec = r.get("sector") or "Övrigt"
        s = sectors[sec]
        s["count"] += 1
        sc = r.get("score_total")
        if sc is not None:
            s["scores"].append(sc)
            if sc > s["top_score"]:
                s["top_score"] = sc
                s["top_ticker"] = r.get("ticker")
        mo = r.get("score_momentum")
        if mo is not None:
            s["momentums"].append(mo)
        _FIELD_MAP = {
            "score_value": "score_values",
            "score_quality": "score_qualities",
            "score_growth": "score_growths",
            "score_risk": "score_risks",
        }
        for field, dict_key in _FIELD_MAP.items():
            val = r.get(field)
            if val is not None:
                s[dict_key].append(val)
        sig = r.get("entry_signal")
        if sig:
            s["signals"][sig] += 1

    sector_list = []
    for name, data in sorted(sectors.items()):
        def _avg(vals):
            return round(sum(vals) / len(vals), 2) if vals else None
        sector_list.append(SectorSummary(
            sector=name,
            count=data["count"],
            avg_score=_avg(data["scores"]) or 0,
            avg_momentum=_avg(data["momentums"]) or 0,
            avg_value=_avg(data.get("score_values", [])),
            avg_quality=_avg(data.get("score_qualities", [])),
            avg_growth=_avg(data.get("score_growths", [])),
            avg_risk=_avg(data.get("score_risks", [])),
            top_ticker=data["top_ticker"],
            top_score=data["top_score"] or None,
            stark_count=data["signals"].get("STARK", 0),
            ok_count=data["signals"].get("OK", 0),
            vanta_count=data["signals"].get("VÄNTA", 0) + data["signals"].get("EJ_AKTUELL", 0),
        ))

    return SectorOverviewOut(
        sectors=sector_list,
        total_tickers=len(rows),
        scan_date=scan_date,
    )


class GlobalIndexOut(BaseModel):
    name: str
    price: float | None = None
    change_pct: float | None = None


class GlobalMarketsOut(BaseModel):
    indices: list[GlobalIndexOut]
    us_futures: list[GlobalIndexOut] = []


# Common index symbols on Finnhub
INDEX_SYMBOLS = [
    ("^OMX", "OMXS30"),
    ("^GSPC", "S&P 500"),
    ("^IXIC", "Nasdaq"),
    ("^DJI", "Dow Jones"),
    ("^FTSE", "FTSE 100"),
    ("^N225", "Nikkei 225"),
    ("^HSI", "Hang Seng"),
    ("^STOXX50E", "Euro Stoxx 50"),
    ("^DAX", "DAX"),
    ("^AXJO", "ASX 200"),
    ("^BSESN", "Sensex"),
    ("SSEC", "Shanghai Comp"),
]


async def _fetch_indices_yfinance() -> list[GlobalIndexOut]:
    """Fallback: fetch index data via yfinance when Finnhub key is unavailable."""
    # yfinance uses same ^ symbols as Finnhub for indices; DAX uses ^GDAXI not ^DAX
    YF_SYMBOLS = [
        ("^OMX",     "OMXS30"),
        ("^GSPC",    "S&P 500"),
        ("^IXIC",    "Nasdaq"),
        ("^DJI",     "Dow Jones"),
        ("^FTSE",    "FTSE 100"),
        ("^GDAXI",   "DAX"),
        ("^STOXX50E","Euro Stoxx 50"),
        ("^N225",    "Nikkei 225"),
        ("^HSI",     "Hang Seng"),
    ]

    def _blocking() -> list[GlobalIndexOut]:
        try:
            import yfinance as yf
        except ImportError:
            return []

        results: list[GlobalIndexOut] = []
        for symbol, name in YF_SYMBOLS:
            try:
                t = yf.Ticker(symbol)
                # Use history(period="2d") — more reliable than fast_info for indices
                # across all yfinance versions and works when markets are closed.
                hist = t.history(period="2d")
                if hist.empty:
                    continue
                price = float(hist["Close"].iloc[-1])
                prev = float(hist["Close"].iloc[-2]) if len(hist) >= 2 else None
                if price:
                    change = round(((price - prev) / prev) * 100, 2) if prev else None
                    results.append(GlobalIndexOut(name=name, price=round(price, 2), change_pct=change))
            except Exception as exc:
                logger.debug("yfinance index %s failed: %s", symbol, exc)
        return results

    try:
        return await asyncio.to_thread(_blocking)
    except Exception as exc:
        logger.warning("yfinance indices fallback failed: %s", exc)
        return []


@router.get("/indices", response_model=GlobalMarketsOut)
async def get_global_indices():
    """Global index snapshot.
    Primary: Finnhub (parallel requests, 5-min cache).
    Fallback: yfinance when FINNHUB_API_KEY is not configured.
    """
    # Cache hit
    cached = _get_cached_indices()
    if cached is not None:
        return GlobalMarketsOut(indices=cached)

    indices: list[GlobalIndexOut] = []

    if settings.FINNHUB_API_KEY:
        async def _fetch_index(client: httpx.AsyncClient, finnhub_symbol: str, name: str):
            try:
                resp = await client.get(
                    f"https://finnhub.io/api/v1/quote?symbol={finnhub_symbol}",
                    headers={"X-Finnhub-Token": settings.FINNHUB_API_KEY},
                )
                resp.raise_for_status()
                data = resp.json()
                if data.get("c"):
                    return GlobalIndexOut(
                        name=name,
                        price=data["c"],
                        change_pct=(
                            round(((data["c"] - data["pc"]) / data["pc"]) * 100, 2)
                            if data.get("pc")
                            else None
                        ),
                    )
            except Exception as e:
                logger.debug("Finnhub index %s failed: %s", finnhub_symbol, e)
            return None

        async with httpx.AsyncClient(timeout=8.0) as client:
            results = await asyncio.gather(
                *[_fetch_index(client, sym, name) for sym, name in INDEX_SYMBOLS],
                return_exceptions=True,
            )
        indices = [r for r in results if isinstance(r, GlobalIndexOut)]

    # If Finnhub unavailable or returned nothing — fall back to yfinance
    if not indices:
        logger.info("Finnhub indices empty or unavailable — falling back to yfinance")
        indices = await _fetch_indices_yfinance()

    _set_cached_indices(indices)
    return GlobalMarketsOut(indices=indices)


class TopMover(BaseModel):
    ticker: str
    name: str | None = None
    score_total: float | None = None
    change_pct: float | None = None
    entry_signal: str | None = None
    price: float | None = None
    reason: str | None = None


class TopMoversOut(BaseModel):
    up: list[TopMover]
    down: list[TopMover]
    score_winners: list[TopMover]
    score_losers: list[TopMover]


@router.get("/top-movers", response_model=TopMoversOut)
async def get_top_movers(sb=Depends(get_supabase)):
    """Today's top movers by price change and score winners/losers."""
    # Use PostgREST ordering to avoid fetching all rows
    up_res = (
        sb.table("scan_results").select("ticker,name,score_total,change_pct,entry_signal,price")
        .not_.is_("change_pct", "null")
        .order("change_pct", desc=True)
        .limit(5).execute()
    )
    down_res = (
        sb.table("scan_results").select("ticker,name,score_total,change_pct,entry_signal,price")
        .not_.is_("change_pct", "null")
        .order("change_pct", desc=False)
        .limit(5).execute()
    )
    score_winners_res = (
        sb.table("scan_results").select("ticker,name,score_total,change_pct,entry_signal,price")
        .not_.is_("score_total", "null")
        .order("score_total", desc=True)
        .limit(5).execute()
    )
    score_losers_res = (
        sb.table("scan_results").select("ticker,name,score_total,change_pct,entry_signal,price")
        .not_.is_("score_total", "null")
        .order("score_total", desc=False)
        .limit(5).execute()
    )

    up = [TopMover(**r) for r in (up_res.data or [])]
    down = [TopMover(**r) for r in (down_res.data or [])]
    score_winners = [TopMover(**r) for r in (score_winners_res.data or [])]
    score_losers = [TopMover(**r) for r in (score_losers_res.data or [])]

    return TopMoversOut(up=up, down=down, score_winners=score_winners, score_losers=score_losers)
