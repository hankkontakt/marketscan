"""
Transactions API — transaction log for TWR calculation.
RLS-protected: users can only access their own transactions.
"""
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from apps.api.dependencies import get_user_supabase
from apps.api.core.security import get_current_user, User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/transactions", tags=["transactions"])


class TransactionIn(BaseModel):
    ticker: str
    type: str = Field(..., pattern="^(buy|sell|deposit|withdrawal)$")
    shares: float | None = None
    price: float | None = None
    amount: float | None = None
    traded_at: str | None = None
    note: str | None = None


class TransactionOut(BaseModel):
    id: str
    ticker: str
    type: str
    shares: float | None = None
    price: float | None = None
    amount: float | None = None
    traded_at: str
    note: str | None = None
    created_at: str


class TransactionListOut(BaseModel):
    transactions: list[TransactionOut]
    total: int


class TWROut(BaseModel):
    twr: float | None = None
    total_return_pct: float | None = None
    periods: dict[str, float | None]


@router.get("", response_model=TransactionListOut)
def get_transactions(
    ticker: str | None = None,
    limit: int = 50,
    user: User = Depends(get_current_user),
    sb=Depends(get_user_supabase),
):
    """Get user's transactions, optionally filtered by ticker."""
    query = (
        sb.table("transactions")
        .select("*")
        .eq("user_id", user.id)
    )
    if ticker:
        query = query.eq("ticker", ticker.upper())
    query = query.order("traded_at", desc=True).limit(limit)

    res = query.execute()
    items = res.data or []

    return TransactionListOut(
        transactions=[_format_tx(t) for t in items],
        total=len(items),
    )


@router.post("", response_model=TransactionOut, status_code=201)
def create_transaction(
    body: TransactionIn,
    user: User = Depends(get_current_user),
    sb=Depends(get_user_supabase),
):
    """Record a new transaction."""
    # Get user's portfolio id
    port = (
        sb.table("portfolios").select("id").eq("user_id", user.id)
        .limit(1).execute()
    )
    if not port.data:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ingen portfölj hittad")

    data = {
        "user_id": user.id,
        "portfolio_id": port.data[0]["id"],
        "ticker": body.ticker.upper(),
        "type": body.type,
        "shares": body.shares,
        "price": body.price,
        "amount": body.amount,
        "note": body.note,
    }
    if body.traded_at:
        data["traded_at"] = body.traded_at

    res = sb.table("transactions").insert(data).execute()
    return _format_tx(res.data[0])


@router.delete("/{transaction_id}", status_code=204)
def delete_transaction(
    transaction_id: str,
    user: User = Depends(get_current_user),
    sb=Depends(get_user_supabase),
):
    """Delete a transaction (ownership check)."""
    res = (
        sb.table("transactions").delete()
        .eq("id", transaction_id)
        .eq("user_id", user.id)
        .execute()
    )
    if not res.data:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Transaktionen hittades inte")


@router.get("/twr", response_model=TWROut)
def get_twr(
    user: User = Depends(get_current_user),
    sb=Depends(get_user_supabase),
):
    """
    Calculate Time-Weighted Return (TWR) for the user's portfolio.
    TWR avoids distortion from deposits/withdrawals by geometrically
    linking sub-period returns between cash flows.
    """
    from collections import defaultdict
    from datetime import date, timedelta

    # Get all holdings with current prices
    port = sb.table("portfolios").select("id").eq("user_id", user.id).limit(1).execute()
    if not port.data:
        return TWROut(twr=None, total_return_pct=None, periods={})

    portfolio_id = port.data[0]["id"]

    holdings_res = sb.table("holdings").select("*").eq("portfolio_id", portfolio_id).execute()
    holdings = holdings_res.data or []
    if not holdings:
        return TWROut(twr=None, total_return_pct=None, periods={})

    tickers = [h["ticker"] for h in holdings]
    scan_res = sb.table("scan_results").select("ticker, price").in_("ticker", tickers).execute()
    scan_map = {r["ticker"]: float(r["price"]) for r in (scan_res.data or []) if r.get("price")}

    # Current portfolio value
    current_value = sum(float(h["shares"]) * scan_map.get(h["ticker"], 0) for h in holdings)

    # Get transactions
    tx_res = sb.table("transactions").select("*").eq("user_id", user.id).order("traded_at").execute()
    transactions = tx_res.data or []

    # Get snapshots for period returns (limit to most recent 100)
    snap_res = sb.table("portfolio_snapshots").select("*").eq("user_id", user.id).order("date", desc=True).limit(100).execute()
    snapshots = snap_res.data or []

    if not snapshots:
        return TWROut(twr=None, total_return_pct=None, periods={})

    # Calculate TWR using sub-periods between cash flows
    twr = _calculate_twr(transactions, snapshots, current_value)

    # Calculate total return (simple) using oldest snapshot
    first_snap = sorted_snapshots[0] if len(sorted_snapshots) > 0 else None
    total_cost = first_snap.get("total_cost")
    total_return = None
    if total_cost and float(total_cost) > 0:
        first_value = float(first_snap.get("total_value", 0))
        total_return = ((current_value - first_value) / first_value) * 100 if first_value > 0 else None

    # Period returns from snapshots (sliced from sorted oldest-first)
    periods: dict[str, float | None] = {}
    today = date.today()
    sorted_snapshots = sorted(snapshots, key=lambda s: s["date"] if isinstance(s["date"], str) else s["date"])
    for label, days in [("1M", 30), ("3M", 90), ("6M", 180), ("12M", 365)]:
        target = (today - timedelta(days=days)).isoformat()
        past_val = None
        for s in sorted_snapshots:
            sd = s["date"] if isinstance(s["date"], str) else s["date"].isoformat()
            if sd <= target:
                past_val = float(s["total_value"])
                break
        if past_val and past_val > 0:
            periods[label] = ((current_value - past_val) / past_val) * 100
        else:
            periods[label] = None

    return TWROut(
        twr=round(twr, 2) if twr is not None else None,
        total_return_pct=round(total_return, 2) if total_return is not None else None,
        periods=periods,
    )


def _calculate_twr(
    transactions: list[dict],
    snapshots: list[dict],
    current_value: float,
) -> float | None:
    """
    Calculate TWR by linking sub-period returns between cash flows.
    Simplified implementation: uses daily snapshots when available.
    """
    if not snapshots or current_value <= 0:
        return None

    # Group transactions by date (normalize to date-only for matching)
    tx_by_date: dict[str, list[dict]] = defaultdict(list)
    for tx in transactions:
        tx_date = tx["traded_at"][:10] if isinstance(tx["traded_at"], str) else tx["traded_at"]
        tx_by_date[tx_date].append(tx)

    # Sort snapshots and limit to reasonable number
    sorted_snaps = sorted(snapshots, key=lambda s: s["date"] if isinstance(s["date"], str) else s["date"])

    if len(sorted_snaps) < 2:
        return None

    # Link sub-period returns geometrically
    twr = 1.0
    prev_value = float(sorted_snaps[0]["total_value"])

    for snap in sorted_snaps[1:]:
        snap_date = snap["date"] if isinstance(snap["date"], str) else snap["date"].isoformat()
        snap_value = float(snap["total_value"])

        # Add cash flows on this date
        cash_flow = 0.0
        for tx in tx_by_date.get(snap_date, []):
            if tx["type"] == "deposit":
                cash_flow += float(tx.get("amount", 0) or 0)
            elif tx["type"] == "withdrawal":
                cash_flow -= float(tx.get("amount", 0) or 0)

        if prev_value > 0:
            hp = (snap_value - cash_flow) / prev_value
            twr *= hp

        prev_value = snap_value

    # Last period: from last snapshot to current
    # (simplified — in production, use daily snapshots)
    return (twr - 1.0) * 100


def _format_tx(t: dict) -> TransactionOut:
    return TransactionOut(
        id=t["id"],
        ticker=t["ticker"],
        type=t["type"],
        shares=float(t["shares"]) if t.get("shares") else None,
        price=float(t["price"]) if t.get("price") else None,
        amount=float(t["amount"]) if t.get("amount") else None,
        traded_at=t.get("traded_at", ""),
        note=t.get("note"),
        created_at=t.get("created_at", ""),
    )
