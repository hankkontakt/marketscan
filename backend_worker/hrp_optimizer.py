"""
Hierarchical Risk Parity portfolio optimizer.

DEPRECATED — 2026-06-08
This file is not imported by any router or workflow and is kept only as
reference code. If HRP optimisation is needed in the future, integrate it
into apps/api/routers/portfolio.py using the service-layer pattern.
No active callers; safe to remove once confirmed unused in all branches.
"""
import os
import sys
import json
import logging
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "stock-scanner"))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("hrp_optimizer")


def optimize_portfolio(tickers, weights_in=None):
    """Run HRP optimization for given tickers.

    Parameters
    ----------
    tickers : list of str
        List of ticker symbols to optimize.
    weights_in : list of float, optional
        Initial weights (ignored by HRP, kept for API compatibility).

    Returns
    -------
    dict or None
        Optimized portfolio weights and metrics, or None on failure.
    """
    import pandas as pd
    import yfinance as yf
    import numpy as np

    try:
        from portfolio.hrp_optimizer import HRPOptimizer
    except ImportError as e:
        logger.error("Failed to import HRPOptimizer: %s", e)
        logger.error("Ensure stock-scanner repo is available at: %s",
                     os.path.join(os.path.dirname(__file__), "..", "stock-scanner"))
        sys.exit(1)

    if not tickers:
        logger.error("No tickers provided.")
        return None

    logger.info("Optimizing portfolio for %d tickers...", len(tickers))

    # Download historical prices
    try:
        data = yf.download(tickers, period="2y", group_by="ticker", auto_adjust=True, progress=False)
    except Exception as e:
        logger.error("Failed to download price data: %s", e)
        return None

    prices = pd.DataFrame()
    for t in tickers:
        try:
            prices[t] = data[t]["Close"]
        except (KeyError, TypeError):
            try:
                prices[t] = data["Close"][t]
            except (KeyError, TypeError):
                logger.warning("Could not extract price data for %s, skipping.", t)
                continue

    if prices.empty or len(prices.columns) < 2:
        logger.error("Not enough price data to optimize (need at least 2 tickers with data).")
        return None

    returns = prices.pct_change().dropna()

    try:
        optimizer = HRPOptimizer()
        weights = optimizer.optimize(returns)
    except Exception as e:
        logger.error("HRP optimization failed: %s", e)
        return None

    # Calculate portfolio metrics
    import numpy as np
    mean_returns = returns.mean() * 252
    cov_matrix = returns.cov() * 252

    port_return = (mean_returns * weights).sum()
    port_vol = np.sqrt(weights.T @ cov_matrix @ weights)
    sharpe = port_return / port_vol if port_vol > 1e-8 else 0.0

    result = {
        "method": "HRP",
        "weights": {t: round(float(w), 4) for t, w in zip(tickers, weights) if w > 0.01},
        "expected_return": round(float(port_return), 4),
        "expected_volatility": round(float(port_vol), 4),
        "sharpe": round(float(sharpe), 4),
    }

    print(json.dumps(result))
    logger.info("HRP optimization complete. Sharpe: %.4f", sharpe)
    return result


if __name__ == "__main__":
    if len(sys.argv) < 2:
        logger.error("Usage: python hrp_optimizer.py TICKER1,TICKER2,...")
        sys.exit(1)
    raw = sys.argv[1]
    tickers = [t.strip().upper() for t in raw.split(",") if t.strip()]
    if not tickers:
        logger.error("No valid tickers provided.")
        sys.exit(1)
    optimize_portfolio(tickers)
