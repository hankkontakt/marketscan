"""Paper trading engine — simulates portfolio performance."""
import os
import sys
import json
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("paper_trading")


def evaluate_positions(positions, current_prices):
    """Calculate P&L for current paper positions.

    Parameters
    ----------
    positions : list of dict
        Each entry must contain "ticker", "shares", and "avg_cost".
    current_prices : dict
        Mapping of ticker -> current market price.

    Returns
    -------
    dict
        Per-position P&L and aggregated portfolio metrics.
    """
    if not positions:
        logger.warning("No positions to evaluate.")
        return {
            "positions": [],
            "total_value": 0.0,
            "total_cost": 0.0,
            "total_pnl": 0.0,
            "total_pnl_pct": 0.0,
            "timestamp": datetime.now().isoformat(),
        }

    total_value = 0.0
    total_cost = 0.0
    results = []

    for pos in positions:
        ticker = pos.get("ticker", "UNKNOWN")
        shares = pos.get("shares", 0)
        avg_cost = pos.get("avg_cost", 0.0)
        current_price = current_prices.get(ticker, avg_cost)

        if shares <= 0:
            logger.debug("Skipping position %s with non-positive shares.", ticker)
            continue

        market_value = shares * current_price
        cost_basis = shares * avg_cost
        pnl = market_value - cost_basis
        pnl_pct = ((current_price - avg_cost) / avg_cost) * 100 if avg_cost > 0 else 0.0

        total_value += market_value
        total_cost += cost_basis

        results.append({
            "ticker": ticker,
            "shares": shares,
            "avg_cost": avg_cost,
            "current_price": current_price,
            "market_value": round(market_value, 2),
            "pnl": round(pnl, 2),
            "pnl_pct": round(pnl_pct, 2),
        })

    total_pnl = total_value - total_cost
    total_pnl_pct = ((total_value / total_cost) - 1) * 100 if total_cost > 0 else 0.0

    return {
        "positions": results,
        "total_value": round(total_value, 2),
        "total_cost": round(total_cost, 2),
        "total_pnl": round(total_pnl, 2),
        "total_pnl_pct": round(total_pnl_pct, 2),
        "timestamp": datetime.now().isoformat(),
    }


if __name__ == "__main__":
    # Example usage — in production, positions come from Supabase
    sample_positions = [
        {"ticker": "AAPL", "shares": 10, "avg_cost": 150.0},
        {"ticker": "MSFT", "shares": 5, "avg_cost": 300.0},
    ]
    sample_prices = {"AAPL": 175.0, "MSFT": 320.0}
    result = evaluate_positions(sample_positions, sample_prices)
    print(json.dumps(result, indent=2))
