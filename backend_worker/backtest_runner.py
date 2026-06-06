"""Backtesting engine for strategy validation."""
import os
import sys
import json
import logging
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "stock-scanner"))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("backtest_runner")


def run_backtest(strategy="momentum", tickers=None):
    """Run a historical backtest for a given strategy.

    Parameters
    ----------
    strategy : str
        Strategy name (e.g. "momentum", "mean_reversion", "breakout").
    tickers : list of str, optional
        List of ticker symbols to backtest. Defaults to major tech tickers.

    Returns
    -------
    dict
        Backtest results including return, Sharpe, drawdown, and equity curve.
    """
    try:
        from backtesting.backtest import BacktestEngine
        from backtesting.walk_forward import WalkForwardAnalyzer
    except ImportError as e:
        logger.error("Failed to import backtesting modules: %s", e)
        logger.error("Ensure stock-scanner repo is available at: %s",
                     os.path.join(os.path.dirname(__file__), "..", "stock-scanner"))
        sys.exit(1)

    if tickers is None:
        tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"]

    logger.info("Running '%s' backtest on %d tickers: %s", strategy, len(tickers), ", ".join(tickers))

    engine = BacktestEngine(strategy=strategy)
    try:
        result = engine.run(tickers)
    except Exception as e:
        logger.error("Backtest execution failed: %s", e)
        sys.exit(1)

    output = {
        "strategy_name": strategy,
        "tickers": tickers,
        "total_return": round(float(result.get("total_return", 0)), 4),
        "cagr": round(float(result.get("cagr", 0)), 4),
        "sharpe": round(float(result.get("sharpe", 0)), 4),
        "max_drawdown": round(float(result.get("max_drawdown", 0)), 4),
        "volatility": round(float(result.get("volatility", 0)), 4),
        "win_rate": round(float(result.get("win_rate", 0)), 4),
        "num_trades": result.get("num_trades", 0),
        "start_date": result.get("start_date"),
        "end_date": result.get("end_date"),
        "equity_curve": result.get("equity_curve", []),
        "timestamp": datetime.now().isoformat(),
    }

    print(json.dumps(output))
    logger.info("Backtest complete. Sharpe: %.2f, Return: %.1f%%",
                output["sharpe"], output["total_return"] * 100)


if __name__ == "__main__":
    strategy = sys.argv[1] if len(sys.argv) > 1 else "momentum"
    run_backtest(strategy)
