"""
GET /stocks/{ticker} — detailed stock view.
Hot data from Postgres, cold (price history, score history) from R2/DuckDB.
Falls back to generated mock data when R2 is not configured.
"""
import re
import random
import math
import logging
import httpx
from datetime import date, timedelta, datetime
from fastapi import APIRouter, Depends, HTTPException, status
from apps.api.dependencies import get_supabase
from apps.api.core.duckdb_r2 import query_score_history, query_price_history
from apps.api.core.config import settings
from apps.api.core.search_utils import safe_search

logger = logging.getLogger(__name__)

_TICKER_RE = re.compile(r"^[A-Za-z0-9.\-]{1,20}$")


def _validate_ticker(ticker: str) -> str:
    t = ticker.upper().strip()
    if not _TICKER_RE.match(t):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Ogiltigt ticker-format: {ticker}")
    return t


def _generate_mock_candles(ticker: str, current_price: float, days: int = 400) -> list[dict]:
    """Generate deterministic mock OHLCV candles for dev when R2 is not configured.
    Seeded by ticker so the same stock always gets the same chart shape.
    Uses sum of byte values for stable seed (Python hash is randomized)."""
    seed = sum(bytearray(ticker.encode("utf-8"))) + len(ticker)
    rng = random.Random(seed)

    candles = []
    # Start ~30% below current to give chart some upward movement
    price = current_price / (1 + rng.uniform(0.1, 0.35))
    start_date = date.today() - timedelta(days=days)

    for i in range(days):
        d = start_date + timedelta(days=i)
        if d.weekday() >= 5:   # skip weekends
            continue

        # Random walk: small daily drift + volatility
        daily_ret = rng.gauss(0.0004, 0.014)
        close = max(price * (1 + daily_ret), 0.01)
        open_p = price * (1 + rng.gauss(0, 0.004))
        spread = abs(rng.gauss(0, 0.018)) * close
        high = max(open_p, close) + spread * rng.random()
        low  = min(open_p, close) - spread * rng.random()
        vol  = max(50_000, int(rng.gauss(800_000, 250_000)))

        candles.append({
            "time": d.isoformat(),
            "open": round(open_p, 2),
            "high": round(max(high, open_p, close), 2),
            "low":  round(min(low, open_p, close), 2),
            "close": round(close, 2),
            "volume": vol,
        })
        price = close

    # Scale so the final close matches the real current price
    if candles and candles[-1]["close"] > 0:
        scale = current_price / candles[-1]["close"]
        for c in candles:
            c["open"]  = round(c["open"]  * scale, 2)
            c["high"]  = round(c["high"]  * scale, 2)
            c["low"]   = round(c["low"]   * scale, 2)
            c["close"] = round(c["close"] * scale, 2)

    return candles


def _generate_mock_score_history(ticker: str, current_score: float, weeks: int = 52) -> list[dict]:
    """Deterministic mock weekly score history for dev when R2 is not configured."""
    seed = sum(bytearray(ticker.encode("utf-8"))) + len(ticker) + 1
    rng = random.Random(seed)
    score = max(10, min(95, current_score - rng.uniform(5, 20)))
    history = []
    today = date.today()
    for i in range(weeks, 0, -1):
        d = today - timedelta(weeks=i)
        # Skip to Monday
        d = d - timedelta(days=d.weekday())
        score = max(10, min(99, score + rng.gauss(0.5, 3)))
        if i == 1:
            score = current_score  # End at real score
        history.append({
            "date": d.isoformat(),
            "score": round(score, 1),
            "signal": "STARK" if score >= 75 else "OK" if score >= 55 else "VÄNTA",
        })
    return history

from apps.api.schemas.scan import ScanRow
from pydantic import BaseModel, Field


class PriceHistoryOut(BaseModel):
    ticker: str
    candles: list[dict]
    is_synthetic: bool = False


class ScoreHistoryOut(BaseModel):
    ticker: str
    history: list[dict]
    is_synthetic: bool = False


class StockSearchResult(BaseModel):
    ticker: str
    name: str | None = None
    segment: str | None = None
    score_total: float | None = None
    entry_signal: str | None = None
    price: float | None = None
    change_pct: float | None = None


class StockLookupResult(BaseModel):
    ticker: str
    name: str | None = None
    sector: str | None = None
    segment: str | None = None
    score_total: float | None = None
    entry_signal: str | None = None
    price: float | None = None
    change_pct: float | None = None
    market_cap: float | None = None
    in_universe: bool = True


class NewsItemOut(BaseModel):
    date: str
    headline: str
    summary: str
    source: str
    url: str | None = None
    sentiment: str | None = None
    ticker: str | None = None


class NewsResponse(BaseModel):
    ticker: str
    news: list[NewsItemOut]


class EarningsItem(BaseModel):
    # P1-5: Added quarter/year which frontend displays as "{quarter} {year}"
    period: str | None = None
    quarter: int | None = None
    year: int | None = None
    actual: float | None = None
    estimate: float | None = None
    surprise: float | None = None
    surprise_pct: float | None = None
    revenue: float | None = None


class EarningsResponse(BaseModel):
    ticker: str
    earnings: list[EarningsItem]


router = APIRouter(prefix="/stocks", tags=["stocks"])


@router.get("/{ticker}", response_model=ScanRow)
async def get_stock(ticker: str, sb=Depends(get_supabase)):
    """Current scan data for a single ticker."""
    t = _validate_ticker(ticker)
    result = (
        sb.table("scan_results")
        .select("*")
        .eq("ticker", t)
        .single()
        .execute()
    )
    if not result.data:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Aktie {ticker} hittades inte")
    return result.data


@router.get("/{ticker}/price-history", response_model=PriceHistoryOut)
async def get_price_history(ticker: str, sb=Depends(get_supabase)):
    """OHLCV data from Finnhub API, with fallback to R2/DuckDB then mock data."""
    t = _validate_ticker(ticker)

    # 1. Try Finnhub API for real price data
    if settings.FINNHUB_API_KEY:
        try:
            today = date.today()
            one_year_ago = today - timedelta(days=365)
            url = (
                f"https://finnhub.io/api/v1/stock/candle"
                f"?symbol={t}"
                f"&resolution=D"
                f"&from={int((today - timedelta(days=400)).timestamp())}"
                f"&to={int(today.timestamp())}"
            )
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, headers={"X-Finnhub-Token": settings.FINNHUB_API_KEY})
                resp.raise_for_status()
                data = resp.json()
                if data.get("s") == "ok" and data.get("t"):
                    candles = [
                        {
                            "time": datetime.fromtimestamp(data["t"][i]).strftime("%Y-%m-%d"),
                            "open": round(data["o"][i], 2),
                            "high": round(data["h"][i], 2),
                            "low":  round(data["l"][i], 2),
                            "close": round(data["c"][i], 2),
                            "volume": data["v"][i],
                        }
                        for i in range(len(data["t"]))
                        if datetime.fromtimestamp(data["t"][i]).weekday() < 6
                    ]
                    if len(candles) >= 10:
                        return {"ticker": ticker, "candles": candles}
        except Exception as e:
            logger.warning("Finnhub price history failed for %s: %s", ticker, e)

    # 2. Try R2/DuckDB (P1-1: must await the async function)
    try:
        data = await query_price_history(t)
        return {"ticker": ticker, "candles": data}
    except Exception as e:
        logger.warning("R2 price history unavailable for %s — falling back to mock data: %s", ticker, e)

    # 3. Fallback: mock candles
    try:
        row = sb.table("scan_results").select("price").eq("ticker", t).single().execute()
        current_price = row.data.get("price") if row.data else None
    except Exception as inner_e:
        logger.warning("Could not fetch current price for %s: %s", ticker, inner_e)
        current_price = None

    candles = _generate_mock_candles(t, current_price or 100.0)
    return {"ticker": ticker, "candles": candles, "is_synthetic": True}


@router.get("/{ticker}/score-history", response_model=ScoreHistoryOut)
async def get_score_history(ticker: str, limit: int = 52, sb=Depends(get_supabase)):
    """Weekly score snapshots from R2. Falls back to generated mock data."""
    t = _validate_ticker(ticker)
    try:
        # P1-1: must await the async function
        data = await query_score_history(t, limit=limit)
        return {"ticker": ticker, "history": data}
    except Exception as e:
        logger.warning("R2 score history unavailable for %s — falling back to mock data: %s", ticker, e)
        try:
            row = sb.table("scan_results").select("score_total").eq("ticker", t).single().execute()
            current_score = row.data.get("score_total") if row.data else 65.0
        except Exception as inner_e:
            logger.warning("Could not fetch current score for %s: %s", ticker, inner_e)
            current_score = 65.0
        history = _generate_mock_score_history(t, float(current_score or 65), limit)
        return {"ticker": ticker, "history": history, "is_synthetic": True}


@router.get("/search", response_model=list[StockLookupResult])
async def lookup_stocks(q: str, limit: int = 10, sb=Depends(get_supabase)):
    """Search stocks across universe AND external sources.

    First searches scan_results (the universe). If no matches found,
    falls back to Finnhub to look up the ticker by symbol.
    Returns in_universe flag so frontend can show appropriate messaging.
    """
    safe_q = safe_search(q)
    if not safe_q:
        return []

    # 1. Search universe first
    universe_res = (
        sb.table("scan_results")
        .select("ticker, name, segment, sector, score_total, entry_signal, price, change_pct, market_cap")
        .or_(f"ticker.ilike.%{safe_q}%,name.ilike.%{safe_q}%")
        .order("score_total", desc=True)
        .limit(limit)
        .execute()
    )
    if universe_res.data:
        return [
            StockLookupResult(**row, in_universe=True)
            for row in universe_res.data
        ]

    # 2. Try Finnhub profile lookup for ticker not in universe
    if settings.FINNHUB_API_KEY:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(
                    f"https://finnhub.io/api/v1/stock/profile2?symbol={safe_q.upper()}",
                    headers={"X-Finnhub-Token": settings.FINNHUB_API_KEY},
                )
                resp.raise_for_status()
                profile = resp.json()
                if profile and profile.get("ticker"):
                    return [StockLookupResult(
                        ticker=profile["ticker"].upper(),
                        name=profile.get("name"),
                        sector=profile.get("finnhubIndustry"),
                        market_cap=profile.get("marketCapitalization"),
                        in_universe=False,
                    )]
        except Exception as e:
            logger.debug("Finnhub lookup failed for %s: %s", safe_q, e)

    # 3. No match anywhere
    return []


@router.get("", response_model=list[StockSearchResult])
async def search_stocks(q: str, limit: int = 10, sb=Depends(get_supabase)):
    """Quick search by ticker or name — used by ⌘K palette."""
    # P0-4: sanitize before interpolating into PostgREST filter
    safe_q = safe_search(q)
    if not safe_q:
        return []
    result = (
        sb.table("scan_results")
        .select("ticker, name, segment, score_total, entry_signal, price, change_pct")
        .or_(f"ticker.ilike.%{safe_q}%,name.ilike.%{safe_q}%")
        .order("score_total", desc=True)
        .limit(limit)
        .execute()
    )
    return result.data


class CompareRequest(BaseModel):
    tickers: list[str] = Field(..., min_length=2, max_length=5)


class CompareMetric(BaseModel):
    label: str
    values: dict[str, float | str | None]


class CompareResponse(BaseModel):
    tickers: list[str]
    metrics: list[CompareMetric]


@router.post("/compare", response_model=CompareResponse)
async def compare_stocks(body: CompareRequest, sb=Depends(get_supabase)):
    """Compare up to 5 stocks side-by-side."""
    tickers = [_validate_ticker(t) for t in body.tickers[:5]]
    result = sb.table("scan_results").select(
        "ticker,name,score_total,score_value,score_quality,score_momentum,"
        "score_growth,score_risk,score_dividend,score_sentiment,"
        "pe_trailing,roe,piotroski_f,market_cap,dividend_yield,beta,"
        "price,change_pct,entry_signal,trend_signal,sector"
    ).in_("ticker", tickers).execute()

    rows = result.data or []
    # Get snapshot data for each validated ticker
    row_map = {r["ticker"]: r for r in rows}

    # Return validated & uppercased tickers
    validated = [t.upper() for t in tickers]

    metric_defs = [
        ("Totalbetyg", "score_total"),
        ("Värdering", "score_value"),
        ("Kvalitet", "score_quality"),
        ("Momentum", "score_momentum"),
        ("Tillväxt", "score_growth"),
        ("Risk", "score_risk"),
        ("P/E", "pe_trailing"),
        ("ROE", "roe"),
        ("Piotroski", "piotroski_f"),
        ("Utdelning", "dividend_yield"),
        ("Beta", "beta"),
        ("Signal", "entry_signal"),
    ]

    metrics = []
    for label, field in metric_defs:
        values = {}
        for t in validated:
            row = row_map.get(t.upper())
            values[t] = row.get(field) if row else None
        metrics.append(CompareMetric(label=label, values=values))

    return CompareResponse(tickers=validated, metrics=metrics)


@router.get("/{ticker}/news", response_model=NewsResponse)
async def get_stock_news(ticker: str):
    """Company news via Finnhub API."""
    t = _validate_ticker(ticker)
    if not settings.FINNHUB_API_KEY:
        return {"ticker": ticker, "news": []}

    today = date.today()
    one_year_ago = today - timedelta(days=365)

    url = (
        f"https://finnhub.io/api/v1/company-news"
        f"?symbol={t}"
        f"&from={one_year_ago.isoformat()}"
        f"&to={today.isoformat()}"
    )

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers={"X-Finnhub-Token": settings.FINNHUB_API_KEY})
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        logger.warning("Finnhub news failed for %s: %s", ticker, e)
        return {"ticker": ticker, "news": []}

    # Finnhub returns articles sorted by datetime descending
    news: list[dict] = []
    for item in data[:20]:
        headline = item.get("headline", "")
        if not headline:
            continue
        ts = item.get("datetime")
        dt = datetime.fromtimestamp(ts).strftime("%Y-%m-%d") if ts else ""
        news.append(NewsItemOut(
            date=dt,
            headline=headline,
            summary=item.get("summary", "")[:300],
            source=item.get("source", "Finnhub"),
            url=item.get("url"),
            sentiment=item.get("sentiment", None),
            ticker=ticker.upper(),
        ))

    return {"ticker": ticker, "news": news}


@router.get("/{ticker}/earnings", response_model=EarningsResponse)
async def get_stock_earnings(ticker: str):
    """Earnings calendar data via Finnhub API."""
    t = _validate_ticker(ticker)
    if not settings.FINNHUB_API_KEY:
        return {"ticker": ticker, "earnings": []}

    url = (
        f"https://finnhub.io/api/v1/stock/earnings"
        f"?symbol={t}"
    )

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers={"X-Finnhub-Token": settings.FINNHUB_API_KEY})
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        logger.warning("Finnhub earnings failed for %s: %s", ticker, e)
        return {"ticker": ticker, "earnings": []}

    # P1-5: Map Finnhub fields explicitly so response_model doesn't strip them
    earnings = []
    for item in data[:12]:
        # Finnhub format: {"period":"2024-03-31","quarter":1,"year":2024,"actual":X,"estimate":Y,...}
        earnings.append(EarningsItem(
            period=item.get("period"),
            quarter=item.get("quarter"),
            year=item.get("year"),
            actual=item.get("actual"),
            estimate=item.get("estimate"),
            surprise=item.get("surprise"),
            surprise_pct=item.get("surprisePercent"),
            revenue=item.get("revenue"),
        ))
    return {"ticker": ticker, "earnings": earnings}


class InsiderTradeOut(BaseModel):
    name: str | None = None
    share: float | None = None
    change: float | None = None
    filiing_date: str | None = None
    transaction_date: str | None = None
    transaction_price: float | None = None
    transaction_code: str | None = None
    url: str | None = None


class InsiderTradesResponse(BaseModel):
    ticker: str
    insider_trades: list[InsiderTradeOut]


@router.get("/{ticker}/insider-trades", response_model=InsiderTradesResponse)
async def get_insider_trades(ticker: str):
    """Insider trading data via Finnhub API."""
    t = _validate_ticker(ticker)
    if not settings.FINNHUB_API_KEY:
        return {"ticker": ticker, "insider_trades": []}

    url = f"https://finnhub.io/api/v1/stock/insider-transactions?symbol={t}"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers={"X-Finnhub-Token": settings.FINNHUB_API_KEY})
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        logger.warning("Finnhub insider trades failed for %s: %s", ticker, e)
        return {"ticker": ticker, "insider_trades": []}

    trades = []
    for item in (data.get("data", []) or [])[:15]:
        trades.append(InsiderTradeOut(
            name=item.get("name"),
            share=item.get("share"),
            change=item.get("change"),
            filiing_date=item.get("filingDate"),
            transaction_date=item.get("transactionDate"),
            transaction_price=item.get("transactionPrice"),
            transaction_code=item.get("transactionCode"),
        ))

    return {"ticker": ticker, "insider_trades": trades}


class PiotroskiCriterion(BaseModel):
    name: str
    passed: bool
    explanation: str


class PiotroskiDetailOut(BaseModel):
    ticker: str
    total_score: int
    criteria: list[PiotroskiCriterion]


@router.get("/{ticker}/piotroski", response_model=PiotroskiDetailOut)
async def get_piotroski_detail(ticker: str, sb=Depends(get_supabase)):
    """Show Piotroski F-Score total with per-criterion breakdown.

    P1-4 fix: Only selects columns that exist in scan_results schema.
    Sub-criteria are derived heuristically from the available columns
    (roa, debt_to_equity, current_ratio, gross_margin, roe) until the
    pipeline is extended to store piotroski_* boolean sub-columns.
    """
    t = _validate_ticker(ticker)
    row = sb.table("scan_results").select(
        "piotroski_f,roa,debt_to_equity,current_ratio,gross_margin,roe,operating_margin"
    ).eq("ticker", t).single().execute()

    if not row.data:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Aktie {ticker} hittades inte")

    r = row.data
    total = int(r.get("piotroski_f") or 0)

    # Heuristic criteria derived from available columns
    # The full Piotroski test requires year-over-year deltas which we don't store —
    # flag criteria as None (unknown) when data is insufficient
    roa = r.get("roa")
    dte = r.get("debt_to_equity")
    cr = r.get("current_ratio")
    gm = r.get("gross_margin")

    criteria = [
        PiotroskiCriterion(
            name="ROA är positiv",
            passed=bool(roa and roa > 0),
            explanation="Positiv avkastning på totala tillgångar — bolaget genererar vinst relativt sina tillgångar.",
        ),
        PiotroskiCriterion(
            name="Kassaflöde från verksamheten",
            passed=total >= 4,  # proxy: high score implies positive OCF
            explanation="Positivt operativt kassaflöde — en indikation på löpande kassaflödet. (Exakt data saknas i nuvarande pipeline.)",
        ),
        PiotroskiCriterion(
            name="Vinstkvalitet (OCF > ROA)",
            passed=total >= 5,
            explanation="Kassaflödet överstiger bokförd vinst — vinsten är trovärdig, inte bokföringsbetingad. (Proxyvärde.)",
        ),
        PiotroskiCriterion(
            name="Skuldsättning — låg/minskande",
            passed=bool(dte is not None and dte < 1.0),
            explanation="Skuldsättningsgraden är under 100 % — bolaget är inte tungt belånat.",
        ),
        PiotroskiCriterion(
            name="Likviditet (current ratio > 1)",
            passed=bool(cr is not None and cr > 1.0),
            explanation="Current ratio > 1 — bolaget kan betala kortsiktiga skulder med kortsiktiga tillgångar.",
        ),
        PiotroskiCriterion(
            name="Ingen aktiesutspädning",
            passed=total >= 4,
            explanation="Ingen betydande aktieemission det senaste året. (Proxyvärde — exakt delta saknas.)",
        ),
        PiotroskiCriterion(
            name="Bruttomarginal positiv",
            passed=bool(gm is not None and gm > 0),
            explanation="Positiv bruttomarginal — bolaget säljer med vinst före rörelsekostnader.",
        ),
        PiotroskiCriterion(
            name="Tillgångsomsättning",
            passed=total >= 5,
            explanation="Effektiv användning av tillgångar. (Proxyvärde — delta kräver historiska balansar.)",
        ),
    ]

    return PiotroskiDetailOut(
        ticker=ticker,
        total_score=total,
        criteria=criteria,
    )


class BenchmarkOut(BaseModel):
    ticker: str
    name: str
    candles: list[dict]
    is_synthetic: bool = False


@router.get("/benchmark/omxs30", response_model=BenchmarkOut)
async def get_omxs30_benchmark():
    """OMXS30 historical data for portfolio benchmark comparison."""
    if settings.FINNHUB_API_KEY:
        try:
            today = date.today()
            url = (
                f"https://finnhub.io/api/v1/stock/candle"
                f"?symbol=^OMX"
                f"&resolution=D"
                f"&from={int((today - timedelta(days=400)).timestamp())}"
                f"&to={int(today.timestamp())}"
            )
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, headers={"X-Finnhub-Token": settings.FINNHUB_API_KEY})
                resp.raise_for_status()
                data = resp.json()
                if data.get("s") == "ok" and data.get("t"):
                    candles = [
                        {
                            "time": datetime.fromtimestamp(data["t"][i]).strftime("%Y-%m-%d"),
                            "close": round(data["c"][i], 2),
                        }
                        for i in range(len(data["t"]))
                        if datetime.fromtimestamp(data["t"][i]).weekday() < 6
                    ]
                    if len(candles) >= 10:
                        return {"ticker": "^OMX", "name": "OMXS30", "candles": candles}
        except Exception as e:
            logger.warning("Finnhub OMXS30 failed: %s", e)

    # Fallback: synthetic benchmark (flat 5% annual return)
    return {
        "ticker": "^OMX",
        "name": "OMXS30",
        "candles": _generate_mock_benchmark_candles(),
        "is_synthetic": True,
    }


def _generate_mock_benchmark_candles(days: int = 400) -> list[dict]:
    """Generate a ~8% annual return benchmark for dev."""
    import random
    rng = random.Random(42)  # fixed seed for reproducibility
    price = 2500.0
    candles = []
    from datetime import date, timedelta
    start = date.today() - timedelta(days=days)
    for i in range(days):
        d = start + timedelta(days=i)
        if d.weekday() >= 5:
            continue
        ret = rng.gauss(0.0003, 0.01)  # ~7.5% annual
        price *= (1 + ret)
        candles.append({"time": d.isoformat(), "close": round(price, 2)})
    return candles
