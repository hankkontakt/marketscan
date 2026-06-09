"""
Insider trades API — combines Finnhub data with FI (Finansinspektionen) data.

Endpoints:
  GET /stocks/{ticker}/insider   — per-stock insider trades (Finnhub + FI)
  GET /insider-radar             — market-wide insider cluster detection
"""
import logging
from collections import defaultdict
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from datetime import date, timedelta
from apps.api.dependencies import get_supabase
from apps.api.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/stocks", tags=["stocks"])

# Separate router for the market-wide radar (no /stocks prefix)
radar_router = APIRouter(tags=["insider"])


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


# ─── Insider Radar (market-wide) ──────────────────────────────────────────────

class RecentTradeOut(BaseModel):
    name: str | None = None
    role: str | None = None
    type: str
    amount: float | None = None
    shares: float | None = None
    trade_date: str
    source: str = "fi"


class InsiderClusterOut(BaseModel):
    ticker: str
    name: str | None = None
    sector: str | None = None
    entry_signal: str | None = None
    score_total: float | None = None
    price: float | None = None
    change_pct: float | None = None
    ml_rank: int | None = None
    trade_count: int
    unique_insiders: int
    total_amount: float
    total_shares: float
    latest_date: str
    cluster_score: float
    recent_trades: list[RecentTradeOut]


@radar_router.get("/insider-radar", response_model=list[InsiderClusterOut])
def get_insider_radar(
    days: int = Query(30, ge=1, le=365, description="Lookback window in days"),
    trade_type: str | None = Query(None, description="'buy', 'sell', or omit for all"),
    min_amount: float = Query(0, ge=0, description="Minimum total amount per cluster (SEK)"),
    limit: int = Query(50, ge=1, le=100),
    sb=Depends(get_supabase),
) -> list[InsiderClusterOut]:
    """
    Market-wide insider trading radar.

    Groups insider trades by ticker over the lookback window, computes a
    cluster_score (combines trade count, unique insiders, amount size),
    and joins with current scan_results for stock context.

    Useful for spotting: multiple insiders buying the same stock,
    large one-off purchases, recent unusual activity.
    """
    from_date = (date.today() - timedelta(days=days)).isoformat()

    # ── 1. Fetch insider trades ──────────────────────────────────────────────
    q = (
        sb.table("insider_trades")
        .select("ticker,name,role,type,shares,amount,trade_date")
        .gte("trade_date", from_date)
        .order("trade_date", desc=True)
        .limit(1000)
    )
    if trade_type in ("buy", "sell"):
        q = q.eq("type", trade_type)

    try:
        result = q.execute()
        trades = result.data or []
    except Exception as e:
        logger.warning("insider_trades query failed: %s", e)
        trades = []

    if not trades:
        return []

    # ── 2. Cluster by ticker ─────────────────────────────────────────────────
    clusters: dict[str, dict] = defaultdict(lambda: {
        "total_amount": 0.0,
        "total_shares": 0.0,
        "trade_count": 0,
        "unique_insiders": set(),
        "latest_date": "",
        "recent_trades": [],
    })

    for t in trades:
        ticker = t["ticker"]
        amount = float(t.get("amount") or 0)
        shares = float(t.get("shares") or 0)
        c = clusters[ticker]
        c["total_amount"] += amount
        c["total_shares"] += shares
        c["trade_count"] += 1
        name = t.get("name") or ""
        if name:
            c["unique_insiders"].add(name)
        td = t.get("trade_date", "")
        if td and td > c["latest_date"]:
            c["latest_date"] = td
        if len(c["recent_trades"]) < 5:
            c["recent_trades"].append(t)

    # ── 3. Apply min_amount filter ───────────────────────────────────────────
    if min_amount > 0:
        clusters = {k: v for k, v in clusters.items() if v["total_amount"] >= min_amount}

    if not clusters:
        return []

    # ── 4. Fetch stock context for matched tickers ───────────────────────────
    ticker_list = list(clusters.keys())[:100]  # safety cap for .in_() query
    try:
        sr = (
            sb.table("scan_results")
            .select("ticker,name,sector,entry_signal,score_total,price,change_pct,ml_rank")
            .in_("ticker", ticker_list)
            .execute()
        )
        stock_map = {r["ticker"]: r for r in (sr.data or [])}
    except Exception as e:
        logger.warning("scan_results join failed in insider-radar: %s", e)
        stock_map = {}

    # ── 5. Build output & compute cluster_score ──────────────────────────────
    output: list[InsiderClusterOut] = []
    for ticker, c in clusters.items():
        stock = stock_map.get(ticker, {})
        n_insiders = len(c["unique_insiders"])

        # Cluster score: weighted blend of trade frequency, insider breadth, size
        amount_score = min(c["total_amount"] / 500_000, 10.0)  # cap at 10 for 5M+ SEK
        cluster_score = round(
            c["trade_count"] * 2.0 + n_insiders * 3.0 + amount_score, 2
        )

        recent = [
            RecentTradeOut(
                name=t.get("name"),
                role=t.get("role"),
                type=t.get("type", "buy"),
                amount=float(t["amount"]) if t.get("amount") else None,
                shares=float(t["shares"]) if t.get("shares") else None,
                trade_date=t.get("trade_date", ""),
            )
            for t in c["recent_trades"]
        ]

        output.append(InsiderClusterOut(
            ticker=ticker,
            name=stock.get("name"),
            sector=stock.get("sector"),
            entry_signal=stock.get("entry_signal"),
            score_total=float(stock["score_total"]) if stock.get("score_total") is not None else None,
            price=float(stock["price"]) if stock.get("price") is not None else None,
            change_pct=float(stock["change_pct"]) if stock.get("change_pct") is not None else None,
            ml_rank=stock.get("ml_rank"),
            trade_count=c["trade_count"],
            unique_insiders=n_insiders,
            total_amount=round(c["total_amount"], 0),
            total_shares=round(c["total_shares"], 0),
            latest_date=c["latest_date"],
            cluster_score=cluster_score,
            recent_trades=recent,
        ))

    # Sort by cluster_score descending, take top N
    output.sort(key=lambda x: x.cluster_score, reverse=True)
    return output[:limit]
