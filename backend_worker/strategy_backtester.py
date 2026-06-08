"""
Strategy Backtester — simulates historical performance of user-defined screener strategies.

For a given strategy (saved in the strategies table):
  1. Loads score_history data for the simulation period
  2. Applies the strategy's filter_json conditions to each historical snapshot
  3. Constructs a portfolio using the configured position sizing
  4. Simulates rebalancing at the configured frequency
  5. Computes performance metrics and equity curve
  6. Stores results in strategy_runs + strategy_daily_equity

Requires score_history data (populated by score_tracker.py).
Runs via GitHub Actions on-demand or scheduled.

Usage:
    python -m marketscan.backend_worker.strategy_backtester --strategy-id UUID
    python -m marketscan.backend_worker.strategy_backtester --run-all
"""
import os
import json
import math
import logging
import argparse
from datetime import date, timedelta
from collections import defaultdict

import psycopg2
import psycopg2.extras
import numpy as np

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

TRADING_DAYS   = 252
RISK_FREE_RATE = 0.035


# ─── Filter Evaluation ───────────────────────────────────────────────────────

_OPS = {
    ">=": lambda a, b: a >= b,
    "<=": lambda a, b: a <= b,
    ">":  lambda a, b: a > b,
    "<":  lambda a, b: a < b,
    "=":  lambda a, b: str(a) == str(b),
    "!=": lambda a, b: str(a) != str(b),
    "in": lambda a, b: str(a) in (b if isinstance(b, list) else [b]),
}

def _matches_filter(row: dict, filter_json: dict) -> bool:
    """
    Evaluate a filter_json against a score_history row.
    filter_json mirrors the /api/scan query params format:
      segments, score_min, score_max, sector, entry_signal,
      trend_signal, piotroski_min, plus arbitrary conditions list.
    """
    if not filter_json:
        return True

    segment = row.get("segment")
    if "segments" in filter_json:
        segs = filter_json["segments"]
        if isinstance(segs, list) and segment not in segs:
            return False
        elif isinstance(segs, str) and segment != segs:
            return False

    score = row.get("score_total")
    if score is not None:
        if "score_min" in filter_json and float(score) < float(filter_json["score_min"]):
            return False
        if "score_max" in filter_json and float(score) > float(filter_json["score_max"]):
            return False

    if "entry_signal" in filter_json:
        if row.get("entry_signal") != filter_json["entry_signal"]:
            return False

    if "trend_signal" in filter_json:
        if row.get("trend_signal") != filter_json["trend_signal"]:
            return False

    if "piotroski_min" in filter_json:
        pf = row.get("piotroski_f")
        if pf is None or int(pf) < int(filter_json["piotroski_min"]):
            return False

    # Arbitrary conditions list: [{field, op, value}]
    for cond in filter_json.get("conditions", []):
        field = cond.get("field")
        op    = cond.get("op")
        value = cond.get("value")
        if not field or not op:
            continue
        row_val = row.get(field)
        if row_val is None:
            return False
        op_fn = _OPS.get(op)
        if not op_fn:
            continue
        try:
            if not op_fn(float(row_val), float(value)):
                return False
        except (TypeError, ValueError):
            if not op_fn(str(row_val), str(value)):
                return False

    return True


# ─── Position Sizing ─────────────────────────────────────────────────────────

def _calc_weights(tickers: list[str], rows: list[dict], method: str) -> dict[str, float]:
    """Compute portfolio weights given sizing method."""
    if not tickers:
        return {}

    if method == "equal":
        w = 1.0 / len(tickers)
        return {t: w for t in tickers}

    elif method == "score_weighted":
        scores = {t: float(r.get("score_total") or 50) for t, r in zip(tickers, rows)}
        total  = sum(scores.values())
        if total == 0:
            w = 1.0 / len(tickers)
            return {t: w for t in tickers}
        return {t: s / total for t, s in scores.items()}

    elif method == "kelly":
        # Simplified half-Kelly: weight ∝ score² (convex preference for top stocks)
        scores = {t: float(r.get("score_total") or 50) ** 2 for t, r in zip(tickers, rows)}
        total  = sum(scores.values())
        if total == 0:
            w = 1.0 / len(tickers)
            return {t: w for t in tickers}
        # Cap at 25% per position to avoid concentration
        raw = {t: s / total for t, s in scores.items()}
        # Renorm after capping
        capped = {t: min(w, 0.25) for t, w in raw.items()}
        cap_total = sum(capped.values())
        return {t: w / cap_total for t, w in capped.items()}

    return {t: 1.0 / len(tickers) for t in tickers}


# ─── Rebalancing Calendar ─────────────────────────────────────────────────────

def _rebalance_dates(start: date, end: date, freq: str) -> list[date]:
    """Generate rebalancing dates between start and end."""
    dates = []
    current = start

    if freq == "daily":
        while current <= end:
            dates.append(current)
            current += timedelta(days=1)

    elif freq == "weekly":
        # Move to nearest Monday
        days_ahead = 0 - current.weekday()
        if days_ahead < 0:
            days_ahead += 7
        current = current + timedelta(days=days_ahead)
        while current <= end:
            dates.append(current)
            current += timedelta(weeks=1)

    elif freq == "monthly":
        while current <= end:
            dates.append(current.replace(day=1))
            # Next month
            if current.month == 12:
                current = current.replace(year=current.year + 1, month=1, day=1)
            else:
                current = current.replace(month=current.month + 1, day=1)

    elif freq == "quarterly":
        quarter_months = [1, 4, 7, 10]
        while current <= end:
            dates.append(current.replace(day=1))
            qm_idx = quarter_months.index(current.month) if current.month in quarter_months else -1
            if qm_idx == -1:
                # Find next quarter start
                for qm in quarter_months:
                    if qm > current.month:
                        current = current.replace(month=qm, day=1)
                        break
                else:
                    current = current.replace(year=current.year + 1, month=1, day=1)
            else:
                next_qm_idx = (qm_idx + 1) % 4
                if next_qm_idx == 0:
                    current = current.replace(year=current.year + 1, month=1, day=1)
                else:
                    current = current.replace(month=quarter_months[next_qm_idx], day=1)

    return [d for d in dates if start <= d <= end]


# ─── Metrics Computation ──────────────────────────────────────────────────────

def _compute_metrics(daily_returns: list[float], initial_capital: float, final_capital: float) -> dict:
    """Compute strategy performance metrics from daily returns list."""
    arr = np.array(daily_returns) if daily_returns else np.array([0.0])

    # Total return
    total_ret = (final_capital - initial_capital) / initial_capital if initial_capital > 0 else 0

    # CAGR
    n_days = len(arr)
    if n_days > 0 and initial_capital > 0:
        years = n_days / TRADING_DAYS
        cagr = ((final_capital / initial_capital) ** (1 / years) - 1) if years > 0 else 0
    else:
        cagr = 0

    # Sharpe
    std = arr.std()
    excess = arr - RISK_FREE_RATE / TRADING_DAYS
    sharpe = float(excess.mean() / std * math.sqrt(TRADING_DAYS)) if std > 0 else 0

    # Sortino
    downside = arr[arr < 0]
    down_std = downside.std() if len(downside) > 0 else 0
    sortino = float(excess.mean() / down_std * math.sqrt(TRADING_DAYS)) if down_std > 0 else 0

    # Max drawdown
    cumulative = np.cumprod(1 + arr)
    running_max = np.maximum.accumulate(cumulative)
    drawdowns = (cumulative - running_max) / running_max
    max_dd = float(drawdowns.min())

    # Calmar
    calmar = abs(cagr / max_dd) if max_dd != 0 else 0

    # Volatility
    vol_ann = float(arr.std() * math.sqrt(TRADING_DAYS))

    # Win rate & trade stats (per-period)
    win_rate = float((arr > 0).mean() * 100) if len(arr) > 0 else 0

    return {
        "total_return_pct": round(total_ret * 100, 4),
        "cagr_pct":         round(cagr * 100, 4),
        "sharpe_ratio":     round(sharpe, 4),
        "sortino_ratio":    round(sortino, 4),
        "max_drawdown_pct": round(max_dd * 100, 4),
        "calmar_ratio":     round(calmar, 4),
        "volatility_ann":   round(vol_ann * 100, 4),
        "win_rate_pct":     round(win_rate, 2),
        "final_capital":    round(final_capital, 2),
    }


# ─── Core Backtest ────────────────────────────────────────────────────────────

def run_backtest(strategy_id: str, dsn: str, existing_run_id: str | None = None) -> str | None:
    """
    Run a full backtest for a strategy. Returns run_id if successful, else None.

    Args:
        strategy_id: UUID of the strategy to backtest
        dsn: PostgreSQL DSN
        existing_run_id: If provided, update this run record instead of creating a new one.
                         Used when the API pre-creates a pending run for the user.
    """
    with psycopg2.connect(dsn, client_encoding="UTF8") as conn:
        conn.autocommit = False
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Load strategy
        cur.execute("SELECT * FROM strategies WHERE id = %s", (strategy_id,))
        strategy = cur.fetchone()
        if not strategy:
            logger.error("Strategy %s not found", strategy_id)
            return None

        filter_json    = strategy["filter_json"] or {}
        max_positions  = int(strategy["max_positions"] or 10)
        sizing_method  = strategy["position_sizing"] or "equal"
        rebalance_freq = strategy["rebalance_freq"] or "monthly"
        initial_capital = float(strategy["initial_capital"] or 100000)
        commission_pct  = float(strategy["commission_pct"] or 0.05) / 100

        # Check available history
        cur.execute("SELECT MIN(scan_date), MAX(scan_date) FROM score_history")
        date_range = cur.fetchone()
        if not date_range or not date_range["min"] or not date_range["max"]:
            logger.warning("No score_history data available for backtesting")
            if existing_run_id:
                cur.execute(
                    "UPDATE strategy_runs SET status = 'failed', error_message = %s WHERE id = %s",
                    ("No score_history data available", existing_run_id),
                )
                conn.commit()
            return None

        start_date = date_range["min"]
        end_date   = date_range["max"]

        if isinstance(start_date, str):
            from datetime import date as dt
            start_date = dt.fromisoformat(start_date)
            end_date   = dt.fromisoformat(end_date)

        # Create or update run record
        if existing_run_id:
            cur.execute("""
                UPDATE strategy_runs
                SET status = 'running', start_date = %s, end_date = %s
                WHERE id = %s
                RETURNING id
            """, (start_date, end_date, existing_run_id))
            row = cur.fetchone()
            run_id = row["id"] if row else existing_run_id
        else:
            cur.execute("""
                INSERT INTO strategy_runs
                    (strategy_id, user_id, start_date, end_date, status)
                VALUES (%s, %s, %s, %s, 'running')
                RETURNING id
            """, (strategy_id, strategy["user_id"], start_date, end_date))
            run_id = cur.fetchone()["id"]
        conn.commit()
        logger.info("Starting backtest run %s for strategy '%s'", run_id, strategy["name"])

        # Load ALL score_history for the period
        cur.execute("""
            SELECT sh.*, sr.segment, sr.sector, sr.name
            FROM score_history sh
            LEFT JOIN scan_results sr ON sr.ticker = sh.ticker
            WHERE sh.scan_date BETWEEN %s AND %s
            ORDER BY sh.scan_date ASC
        """, (start_date, end_date))
        all_history = cur.fetchall()

    # Group by date
    history_by_date: dict[date, list[dict]] = defaultdict(list)
    for row in all_history:
        d = row["scan_date"]
        if isinstance(d, str):
            from datetime import date as dt
            d = dt.fromisoformat(d)
        history_by_date[d].append(dict(row))

    sorted_dates = sorted(history_by_date.keys())
    if not sorted_dates:
        logger.warning("No data in score_history for date range")
        _update_run_failed(run_id, dsn, "No score_history data")
        return None

    # ── Simulation ────────────────────────────────────────────────────────────
    rebal_dates  = set(_rebalance_dates(sorted_dates[0], sorted_dates[-1], rebalance_freq))
    capital      = initial_capital
    positions: dict[str, float] = {}  # ticker → shares * price (value)
    daily_equity = []
    daily_returns = []
    total_trades = 0

    prev_date = None

    for d in sorted_dates:
        rows = history_by_date[d]
        date_rows = {r["ticker"]: r for r in rows}

        # Update current portfolio value
        portfolio_value = capital
        for ticker, val in list(positions.items()):
            if ticker in date_rows and date_rows[ticker].get("price"):
                # Revalue at current price
                pass  # We track value directly
            # We use price returns to update values
        # Actually track as portfolio_value = capital + sum of position values
        # For simplicity: positions dict stores VALUE not shares

        if d in rebal_dates or not positions:
            # ── Rebalance: select new portfolio ──────────────────────────────
            matches = [r for r in rows if _matches_filter(r, filter_json)]
            matches.sort(key=lambda x: float(x.get("score_total") or 0), reverse=True)
            selected = matches[:max_positions]

            if not selected:
                # No matches: stay in cash
                if positions:
                    # Sell everything
                    total_trades += len(positions)
                    capital = portfolio_value * (1 - commission_pct * len(positions))
                    positions = {}
            else:
                selected_tickers = [r["ticker"] for r in selected]
                weights = _calc_weights(
                    selected_tickers,
                    [r for r in selected],
                    sizing_method,
                )

                # Calculate new positions
                old_tickers = set(positions.keys())
                new_tickers = set(selected_tickers)

                # Trades = positions that change
                changed = len(old_tickers.symmetric_difference(new_tickers))
                total_trades += changed
                commission_cost = changed * commission_pct * (portfolio_value / max(len(selected), 1))
                portfolio_value = max(portfolio_value - commission_cost, 0)

                # Assign values based on weights
                positions = {t: portfolio_value * w for t, w in weights.items()}
                capital   = portfolio_value * sum(1 - sum(weights.values()), 0.0)

        elif prev_date and positions:
            # ── Update position values using price returns ─────────────────────
            new_positions = {}
            total_change = 0.0
            total_prev_value = sum(positions.values())

            for ticker, prev_val in positions.items():
                prev_row = history_by_date.get(prev_date, [])
                prev_data = next((r for r in prev_row if r["ticker"] == ticker), None)
                curr_data = date_rows.get(ticker)

                if prev_data and curr_data and prev_data.get("price") and curr_data.get("price"):
                    prev_p = float(prev_data["price"])
                    curr_p = float(curr_data["price"])
                    if prev_p > 0:
                        ret = (curr_p - prev_p) / prev_p
                        new_val = prev_val * (1 + ret)
                        new_positions[ticker] = new_val
                        total_change += new_val - prev_val
                    else:
                        new_positions[ticker] = prev_val
                else:
                    new_positions[ticker] = prev_val  # hold at last known value

            positions = new_positions

        portfolio_value = capital + sum(positions.values())

        # Daily return
        if daily_equity:
            prev_val = daily_equity[-1]["portfolio_value"]
            if prev_val > 0:
                daily_ret = (portfolio_value - prev_val) / prev_val
                daily_returns.append(daily_ret)
            else:
                daily_returns.append(0.0)
        else:
            daily_returns.append(0.0)

        daily_equity.append({
            "run_id":          str(run_id),
            "date":            d.isoformat(),
            "portfolio_value": round(portfolio_value, 2),
            "num_positions":   len(positions),
            "daily_return_pct": round(daily_returns[-1] * 100, 4),
        })

        prev_date = d

    # ── Compute metrics ───────────────────────────────────────────────────────
    final_capital = daily_equity[-1]["portfolio_value"] if daily_equity else initial_capital
    metrics = _compute_metrics(daily_returns, initial_capital, final_capital)
    metrics["total_trades"] = total_trades
    metrics["avg_hold_days"] = round(len(sorted_dates) / max(total_trades, 1), 1)

    # ── Write results ─────────────────────────────────────────────────────────
    with psycopg2.connect(dsn, client_encoding="UTF8") as conn:
        conn.autocommit = False
        cur = conn.cursor()

        # Update run with metrics
        cur.execute("""
            UPDATE strategy_runs SET
                status = 'completed', completed_at = NOW(),
                total_return_pct = %s, cagr_pct = %s,
                sharpe_ratio = %s, sortino_ratio = %s,
                max_drawdown_pct = %s, calmar_ratio = %s,
                volatility_ann = %s, win_rate_pct = %s,
                total_trades = %s, avg_hold_days = %s,
                profit_factor = %s, final_capital = %s
            WHERE id = %s
        """, (
            metrics["total_return_pct"], metrics["cagr_pct"],
            metrics["sharpe_ratio"], metrics["sortino_ratio"],
            metrics["max_drawdown_pct"], metrics["calmar_ratio"],
            metrics["volatility_ann"], metrics["win_rate_pct"],
            metrics["total_trades"], metrics.get("avg_hold_days", 0),
            metrics.get("profit_factor", 0), metrics["final_capital"],
            run_id,
        ))

        # Insert equity curve in batches
        if daily_equity:
            psycopg2.extras.execute_batch(
                cur,
                """
                INSERT INTO strategy_daily_equity
                    (run_id, date, portfolio_value, num_positions, daily_return_pct)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (run_id, date) DO UPDATE SET
                    portfolio_value = EXCLUDED.portfolio_value,
                    num_positions = EXCLUDED.num_positions,
                    daily_return_pct = EXCLUDED.daily_return_pct
                """,
                [(
                    e["run_id"], e["date"], e["portfolio_value"],
                    e["num_positions"], e["daily_return_pct"],
                ) for e in daily_equity],
                page_size=500,
            )

        conn.commit()

    logger.info(
        "Backtest complete: return=%.1f%% CAGR=%.1f%% Sharpe=%.2f MaxDD=%.1f%% Trades=%d",
        metrics["total_return_pct"], metrics["cagr_pct"],
        metrics["sharpe_ratio"], metrics["max_drawdown_pct"], total_trades,
    )
    return str(run_id)


def _update_run_failed(run_id: str, dsn: str, error: str) -> None:
    with psycopg2.connect(dsn) as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE strategy_runs SET status='failed', error_msg=%s, completed_at=NOW() WHERE id=%s",
            (error[:500], run_id)
        )
        conn.commit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--strategy-id",  help="UUID of strategy to backtest")
    parser.add_argument("--run-all",      action="store_true", help="Backtest all strategies")
    parser.add_argument("--run-pending",  action="store_true", help="Pick up all pending strategy_runs from DB")
    args = parser.parse_args()

    dsn = os.environ["DATABASE_URL"]

    if args.run_pending:
        # Pick up all runs with status='pending' from the DB
        with psycopg2.connect(dsn, client_encoding="UTF8") as conn:
            conn.autocommit = True
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT r.id AS run_id, r.strategy_id
                    FROM strategy_runs r
                    WHERE r.status = 'pending'
                    ORDER BY r.created_at ASC
                """)
                pending = cur.fetchall()

        logger.info("Found %d pending backtest runs", len(pending))
        for run_id, strategy_id in pending:
            logger.info("Processing run %s for strategy %s", run_id, strategy_id)
            try:
                run_backtest(str(strategy_id), dsn, existing_run_id=str(run_id))
            except Exception as exc:
                logger.error("Run %s failed: %s", run_id, exc)
                _update_run_failed(str(run_id), dsn, str(exc))

    elif args.run_all:
        with psycopg2.connect(dsn, client_encoding="UTF8") as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id, name FROM strategies ORDER BY created_at")
                all_strategies = cur.fetchall()

        for sid, sname in all_strategies:
            logger.info("Backtesting strategy: %s (%s)", sname, sid)
            try:
                run_backtest(str(sid), dsn)
            except Exception as exc:
                logger.error("Backtest failed for %s: %s", sid, exc)

    elif args.strategy_id:
        run_backtest(args.strategy_id, dsn)
    else:
        logger.error("Provide --strategy-id UUID, --run-pending, or --run-all")
