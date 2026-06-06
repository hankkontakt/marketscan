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

logger = logging.getLogger(__name__)

_TICKER_RE = re.compile(r"^[A-Za-z0-9.\-]{1,20}$")


def _validate_ticker(ticker: str) -> str:
    t = ticker.upper().strip()
    if not _TICKER_RE.match(t):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Ogiltigt ticker-format: {ticker}")
    return t


def _generate_mock_candles(ticker: str, current_price: float, days: int = 400) -> list[dict]:
    """Generate deterministic mock OHLCV candles for dev when R2 is not configured.
    Seeded by ticker so the same stock always gets the same chart shape."""
    rng = random.Random(abs(hash(ticker)) % (2 ** 31))

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
    rng = random.Random((abs(hash(ticker)) + 1) % (2 ** 31))
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
    period: str | None = None
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
    """OHLCV data from R2 for TradingView Lightweight Charts.
    Falls back to generated mock data when R2 is not configured."""
    t = _validate_ticker(ticker)
    try:
        data = query_price_history(t)
        return {"ticker": ticker, "candles": data}
    except Exception as e:
        logger.warning("R2 price history unavailable for %s — falling back to mock data: %s", ticker, e)
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
        data = query_score_history(t, limit=limit)
        return {"ticker": ticker, "history": data}
    except Exception as e:
        logger.warning("R2 score history unavailable for %s — falling back to mock data: %s", ticker, e)
        try:
            row = sb.table("scan_results").select("score_total, entry_signal").eq("ticker", t).single().execute()
            current_score = row.data.get("score_total") if row.data else 65.0
            current_signal = row.data.get("entry_signal") if row.data else "OK"
        except Exception as inner_e:
            logger.warning("Could not fetch current score for %s: %s", ticker, inner_e)
            current_score, current_signal = 65.0, "OK"
        history = _generate_mock_score_history(t, float(current_score or 65), limit)
        return {"ticker": ticker, "history": history, "is_synthetic": True}


@router.get("", response_model=list[StockSearchResult])
async def search_stocks(q: str, limit: int = 10, sb=Depends(get_supabase)):
    """Quick search by ticker or name — used by ⌘K palette."""
    result = (
        sb.table("scan_results")
        .select("ticker, name, segment, score_total, entry_signal, price, change_pct")
        .or_(f"ticker.ilike.%{q}%,name.ilike.%{q}%")
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
    ticker_map = {r["ticker"]: r for r in rows}

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
        ("Dir.avk", "dividend_yield"),
        ("Beta", "beta"),
        ("Signal", "entry_signal"),
    ]

    metrics = []
    for label, field in metric_defs:
        values = {}
        for t in body.tickers:
            row = ticker_map.get(t.upper())
            values[t] = row.get(field) if row else None
        metrics.append(CompareMetric(label=label, values=values))

    return CompareResponse(tickers=body.tickers, metrics=metrics)


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

    return {"ticker": ticker, "earnings": data[:12]}


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
    """Show all 9 Piotroski F-Score criteria with pass/fail."""
    t = _validate_ticker(ticker)
    row = sb.table("scan_results").select(
        "piotroski_f,roa,ocf_to_assets,accrual,debt_to_equity,current_ratio,"
        "shares_diluted,gross_margin,asset_turnover,piotroski_roa,"
        "piotroski_ocf,piotroski_accrual,piotroski_leverage,piotroski_liquidity,"
        "piotroski_dilution,piotroski_margin,piotroski_turnover"
    ).eq("ticker", t).single().execute()

    if not row.data:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Aktie {ticker} hittades inte")

    r = row.data
    total = r.get("piotroski_f", 0)

    criteria = [
        PiotroskiCriterion(name="ROA är positiv", passed=r.get("piotroski_roa", False), explanation="Positiv avkastning på totala tillgångar — bolaget genererar vinst relativt sina tillgångar."),
        PiotroskiCriterion(name="OCF är positiv", passed=r.get("piotroski_ocf", False), explanation="Positivt kassaflöde från verksamheten — den löpande verksamheten genererar pengar."),
        PiotroskiCriterion(name="OCF > ROA (Accrual)", passed=r.get("piotroski_accrual", False), explanation="Kassaflödet är högre än nettoresultatet — vinsten är av hög kvalitet, inte baserad på bokföringsposter."),
        PiotroskiCriterion(name="Minskad skuldsättning", passed=not r.get("piotroski_leverage", True), explanation="Skuldsättningsgraden har minskat — bolaget blir mindre finansiellt riskabelt.") if r.get("debt_to_equity") else PiotroskiCriterion(name="Skuldsättning (finans)", passed=bool(r.get("piotroski_leverage")), explanation="Finansbolag bedöms annorlunda — skuldsättning är en del av affärsmodellen."),
        PiotroskiCriterion(name="Förbättrad likviditet", passed=r.get("piotroski_liquidity", False), explanation="Current ratio har ökat — bolagets kortsiktiga betalningsförmåga förbättras."),
        PiotroskiCriterion(name="Ingen utspädning", passed=not r.get("piotroski_dilution", True), explanation="Antalet aktier har inte ökat — befintliga aktieägare blir inte utspädda."),
        PiotroskiCriterion(name="Förbättrad bruttomarginal", passed=r.get("piotroski_margin", False), explanation="Bruttomarginalen har ökat — bolaget får bättre betalt för sina produkter."),
        PiotroskiCriterion(name="Förbättrad tillgångsomsättning", passed=r.get("piotroski_turnover", False), explanation="Tillgångarna används mer effektivt — mer intäkter per tillgångskrona."),
    ]

    return PiotroskiDetailOut(
        ticker=ticker,
        total_score=total or 0,
        criteria=criteria,
    )
