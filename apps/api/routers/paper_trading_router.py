"""Paper trading — simulated portfolio."""
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from apps.api.dependencies import get_supabase_admin
from apps.api.core.security import get_current_user, User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/paper", tags=["paper-trading"])


@router.get("/portfolio")
def get_paper_portfolio(
    user: User = Depends(get_current_user),
    sb=Depends(get_supabase_admin),  # P1-6: use same client tier as POST so reads are consistent
):
    """Get current user's paper trading portfolio."""
    port = sb.table("paper_portfolios").select("*").eq("user_id", user.id).limit(1).execute()
    if not port.data:
        return {"cash": 100000, "positions": [], "trades": [], "total_value": 100000}

    portfolio = port.data[0]
    positions = sb.table("paper_positions").select("*").eq("portfolio_id", portfolio["id"]).execute()
    trades = sb.table("paper_trades").select("*").eq("portfolio_id", portfolio["id"]).order("traded_at", desc=True).limit(50).execute()

    # Enrich positions with current prices from scan_results
    tickers = [p["ticker"] for p in (positions.data or [])]
    total_stock_value = 0
    enriched_positions = []

    if tickers:
        prices = sb.table("scan_results").select("ticker,price").in_("ticker", tickers).execute()
        price_map = {r["ticker"]: r.get("price") for r in (prices.data or [])}

        for pos in (positions.data or []):
            current_price = price_map.get(pos["ticker"], pos["avg_cost"])
            market_value = pos["shares"] * current_price
            cost_basis = pos["shares"] * pos["avg_cost"]
            total_stock_value += market_value
            enriched_positions.append({
                "ticker": pos["ticker"],
                "shares": pos["shares"],
                "avg_cost": pos["avg_cost"],
                "current_price": current_price,
                "market_value": round(market_value, 2),
                "pnl": round(market_value - cost_basis, 2),
                "pnl_pct": round(((current_price / pos["avg_cost"]) - 1) * 100, 2),
            })

    cash = float(portfolio.get("cash", 100000))
    return {
        "id": portfolio["id"],
        "cash": cash,
        "positions": enriched_positions,
        "trades": trades.data or [],
        "total_value": round(total_stock_value + cash, 2),
    }


@router.post("/trade")
def execute_paper_trade(
    body: dict,
    user: User = Depends(get_current_user),
    sb=Depends(get_supabase_admin),
):
    """Execute a paper trade (buy/sell)."""
    ticker = body.get("ticker", "").upper()
    side = body.get("side", "BUY")
    shares = float(body.get("shares", 0))

    if not ticker or shares <= 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Ogiltig trade")

    # Get current price
    price_res = sb.table("scan_results").select("price").eq("ticker", ticker).limit(1).execute()
    if not price_res.data or not price_res.data[0].get("price"):
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Aktie {ticker} hittades inte")
    price = float(price_res.data[0]["price"])
    total = shares * price

    # Get or create paper portfolio
    port = sb.table("paper_portfolios").select("*").eq("user_id", user.id).limit(1).execute()
    if not port.data:
        new_port = sb.table("paper_portfolios").insert({"user_id": user.id, "cash": 100000}).execute()
        portfolio_id = new_port.data[0]["id"]
        cash = 100000.0
    else:
        portfolio_id = port.data[0]["id"]
        cash = float(port.data[0].get("cash", 0))

    if side == "BUY":
        if total > cash:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Otillräckligt med likvida medel")

        # Record trade
        sb.table("paper_trades").insert({
            "portfolio_id": portfolio_id,
            "ticker": ticker,
            "side": "BUY",
            "shares": shares,
            "price": price,
            "total": total,
        }).execute()

        # Update cash
        sb.table("paper_portfolios").update({"cash": cash - total}).eq("id", portfolio_id).execute()

        # Upsert position
        existing = sb.table("paper_positions").select("*").eq("portfolio_id", portfolio_id).eq("ticker", ticker).limit(1).execute()
        if existing.data:
            pos = existing.data[0]
            new_shares = pos["shares"] + shares
            new_avg = ((pos["avg_cost"] * pos["shares"]) + (price * shares)) / new_shares
            sb.table("paper_positions").update({"shares": new_shares, "avg_cost": new_avg}).eq("id", pos["id"]).execute()
        else:
            sb.table("paper_positions").insert({
                "portfolio_id": portfolio_id,
                "ticker": ticker,
                "shares": shares,
                "avg_cost": price,
            }).execute()

    elif side == "SELL":
        # Check position exists with enough shares
        existing = sb.table("paper_positions").select("*").eq("portfolio_id", portfolio_id).eq("ticker", ticker).limit(1).execute()
        if not existing.data or existing.data[0]["shares"] < shares:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Otillräckligt med aktier att sälja")

        sb.table("paper_trades").insert({
            "portfolio_id": portfolio_id,
            "ticker": ticker,
            "side": "SELL",
            "shares": shares,
            "price": price,
            "total": total,
        }).execute()

        sb.table("paper_portfolios").update({"cash": cash + total}).eq("id", portfolio_id).execute()

        new_shares = existing.data[0]["shares"] - shares
        if new_shares <= 0:
            sb.table("paper_positions").delete().eq("id", existing.data[0]["id"]).execute()
        else:
            sb.table("paper_positions").update({"shares": new_shares}).eq("id", existing.data[0]["id"]).execute()

    return {"status": "ok", "side": side, "ticker": ticker, "shares": shares, "price": price, "total": round(total, 2)}


@router.post("/reset")
def reset_paper_portfolio(
    user: User = Depends(get_current_user),
    sb=Depends(get_supabase_admin),
):
    """Reset paper portfolio to initial state."""
    port = sb.table("paper_portfolios").select("id").eq("user_id", user.id).limit(1).execute()
    if port.data:
        pid = port.data[0]["id"]
        sb.table("paper_trades").delete().eq("portfolio_id", pid).execute()
        sb.table("paper_positions").delete().eq("portfolio_id", pid).execute()
        sb.table("paper_portfolios").update({"cash": 100000}).eq("id", pid).execute()
    return {"status": "ok", "message": "Portföljen har återställts"}
