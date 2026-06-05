"""
GET /stocks/{ticker} — detailed stock view.
Hot data from Postgres, cold (price history, score history) from R2/DuckDB.
Falls back to generated mock data when R2 is not configured.
"""
import random
import math
import logging
from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from apps.api.dependencies import get_supabase
from apps.api.core.duckdb_r2 import query_score_history, query_price_history

logger = logging.getLogger(__name__)


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

router = APIRouter(prefix="/stocks", tags=["stocks"])


@router.get("/{ticker}")
async def get_stock(ticker: str, sb=Depends(get_supabase)):
    """Current scan data for a single ticker."""
    result = (
        sb.table("scan_results")
        .select("*")
        .eq("ticker", ticker.upper())
        .single()
        .execute()
    )
    if not result.data:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Aktie {ticker} hittades inte")
    return result.data


@router.get("/{ticker}/price-history")
async def get_price_history(ticker: str, sb=Depends(get_supabase)):
    """OHLCV data from R2 for TradingView Lightweight Charts.
    Falls back to generated mock data when R2 is not configured."""
    try:
        data = query_price_history(ticker.upper())
        return {"ticker": ticker, "candles": data}
    except Exception as e:
        logger.warning("R2 price history unavailable for %s — falling back to mock data: %s", ticker, e)
        # R2 not configured — generate realistic mock candles from current price
        try:
            row = sb.table("scan_results").select("price").eq("ticker", ticker.upper()).single().execute()
            current_price = row.data.get("price") if row.data else None
        except Exception as inner_e:
            logger.warning("Could not fetch current price for %s: %s", ticker, inner_e)
            current_price = None

        candles = _generate_mock_candles(ticker.upper(), current_price or 100.0)
        return {"ticker": ticker, "candles": candles}


@router.get("/{ticker}/score-history")
async def get_score_history(ticker: str, limit: int = 52, sb=Depends(get_supabase)):
    """Weekly score snapshots from R2. Falls back to generated mock data."""
    try:
        data = query_score_history(ticker.upper(), limit=limit)
        return {"ticker": ticker, "history": data}
    except Exception as e:
        logger.warning("R2 score history unavailable for %s — falling back to mock data: %s", ticker, e)
        try:
            row = sb.table("scan_results").select("score_total, entry_signal").eq("ticker", ticker.upper()).single().execute()
            current_score = row.data.get("score_total") if row.data else 65.0
            current_signal = row.data.get("entry_signal") if row.data else "OK"
        except Exception as inner_e:
            logger.warning("Could not fetch current score for %s: %s", ticker, inner_e)
            current_score, current_signal = 65.0, "OK"
        history = _generate_mock_score_history(ticker.upper(), float(current_score or 65), limit)
        return {"ticker": ticker, "history": history}


@router.get("")
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
