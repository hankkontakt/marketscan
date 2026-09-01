"""Backtesting engine for strategy validation & per-segment IC evaluation (ROND 14)."""
import os
import sys
import json
import logging
from datetime import datetime
from typing import Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "stock-scanner"))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("backtest_runner")


def evaluate_segment_ic(
    scores: list[dict],
    segment: Optional[str] = None,
    forward_return_key: str = "forward_return_1m",
    rank_key: str = "master_rank",
) -> dict:
    """Beräknar Rank Information Coefficient (IC) per segment.

    scores: list of dicts med `rank_key`, `forward_return_key`, och eventuellt `segment`.
    """
    filtered = scores
    if segment:
        filtered = [s for s in scores if s.get("segment") == segment]

    pairs = [
        (float(s[rank_key]), float(s[forward_return_key]))
        for s in filtered
        if s.get(rank_key) is not None and s.get(forward_return_key) is not None
    ]

    n = len(pairs)
    if n < 5:
        return {"segment": segment or "all", "n": n, "rank_ic": None, "t_stat": None}

    # Spearman rank correlation
    try:
        import numpy as np
        from scipy.stats import spearmanr
        ranks_x = [p[0] for p in pairs]
        ranks_y = [p[1] for p in pairs]
        ic, p_val = spearmanr(ranks_x, ranks_y)
        t_stat = float(ic * np.sqrt((n - 2) / (1 - ic**2))) if abs(ic) < 1.0 else 0.0
        return {
            "segment": segment or "all",
            "n": n,
            "rank_ic": round(float(ic), 4),
            "p_value": round(float(p_val), 4),
            "t_stat": round(float(t_stat), 2),
        }
    except Exception as e:
        logger.debug("Spearman IC calculation failed: %s", e)
        return {"segment": segment or "all", "n": n, "rank_ic": None, "error": str(e)}


def simulate_master_rank_scores(rows: list[dict], weights: dict | None = None) -> list[dict]:
    """Kör MasterRank-motorns compute_table (inkl. R15 street-parity-vakter & segment percentil)."""
    from backend_worker.master_rank import compute_table, load_weights
    w = weights or load_weights()
    return compute_table(rows, w)


def run_backtest(strategy="momentum", tickers=None):
    """Run a historical backtest for a given strategy."""
    try:
        from backtesting.backtest import BacktestEngine
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
