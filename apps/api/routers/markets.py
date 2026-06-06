"""
Sector and global market data endpoints.
Sector heatmap from scan_results, global indices via Finnhub.
"""
import logging
import httpx
from fastapi import APIRouter, Depends
from apps.api.dependencies import get_supabase
from apps.api.core.config import settings
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/markets", tags=["markets"])


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
        "score_growth, score_risk, entry_signal, ticker"
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


@router.get("/indices", response_model=GlobalMarketsOut)
async def get_global_indices():
    """Global index snapshot."""
    if not settings.FINNHUB_API_KEY:
        # Fallback to scan_results countries
        return GlobalMarketsOut(indices=[])

    indices = []
    for finnhub_symbol, name in INDEX_SYMBOLS:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(
                    f"https://finnhub.io/api/v1/quote"
                    f"?symbol={finnhub_symbol}"
                    f"&token={settings.FINNHUB_API_KEY}"
                )
                resp.raise_for_status()
                data = resp.json()
                if data.get("c"):
                    indices.append(GlobalIndexOut(
                        name=name,
                        price=data["c"],
                        change_pct=round(((data["c"] - data["pc"]) / data["pc"]) * 100, 2) if data.get("pc") else None,
                    ))
        except Exception as e:
            logger.debug("Finnhub index %s failed: %s", finnhub_symbol, e)

    return GlobalMarketsOut(indices=indices)
