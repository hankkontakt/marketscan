"""
Portfolio Risk Analyzer — nightly computation of risk metrics per user portfolio.

Runs as a GitHub Actions job after the main pipeline. Fetches 1-year price history
from yfinance, computes risk statistics, and writes to portfolio_risk_cache.

Metrics computed:
  - Sharpe ratio (annualised, risk-free ≈ 3.5% SEK swap)
  - Sortino ratio (downside deviation)
  - Calmar ratio (CAGR / max drawdown)
  - Historical VaR 95% and CVaR 95%
  - Beta vs OMXS30 (^OMX)
  - Max drawdown + drawdown duration
  - Correlation matrix between all holdings
  - HRP and min-variance optimal weights
  - Factor exposure vs universe average

Usage (GitHub Actions):
    python -m marketscan.backend_worker.risk_analyzer
"""
import os
import json
import logging
import math
from datetime import datetime, date, timedelta

import psycopg2
import numpy as np

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# Annualisation constants
TRADING_DAYS = 252
RISK_FREE_RATE = 0.035 / TRADING_DAYS  # ~3.5% annual, daily rate
MARKET_TICKER = "^OMX"                 # OMXS30 as benchmark


# ─── Data Loading ─────────────────────────────────────────────────────────────

def _fetch_price_history(tickers: list[str], period: str = "1y") -> dict[str, list[float]]:
    """Download adjusted close prices for a list of tickers via yfinance."""
    try:
        import yfinance as yf
    except ImportError:
        logger.error("yfinance not installed")
        return {}

    if not tickers:
        return {}

    all_tickers = list(set(tickers + [MARKET_TICKER]))
    logger.info("Fetching price history for %d tickers (%s)...", len(all_tickers), period)

    try:
        raw = yf.download(
            all_tickers,
            period=period,
            interval="1d",
            auto_adjust=True,
            progress=False,
            threads=True,
        )
        close = raw["Close"] if "Close" in raw.columns else raw

        result: dict[str, list[float]] = {}
        for t in all_tickers:
            if t in close.columns:
                series = close[t].dropna()
                if len(series) >= 30:
                    result[t] = series.values.tolist()
        return result
    except Exception as exc:
        logger.warning("yfinance download failed: %s", exc)
        return {}


def _align_returns(price_history: dict[str, list[float]]) -> tuple[np.ndarray, list[str]]:
    """Convert price series to daily return matrix. Returns (matrix, tickers)."""
    # Find min length across tickers to align
    min_len = min(len(v) for v in price_history.values()) - 1
    if min_len < 20:
        return np.array([]), []

    tickers = []
    returns_list = []
    for t, prices in price_history.items():
        if t == MARKET_TICKER:
            continue
        arr = np.array(prices[-min_len - 1:])
        daily_ret = np.diff(arr) / arr[:-1]
        daily_ret = np.where(np.isfinite(daily_ret), daily_ret, 0)
        tickers.append(t)
        returns_list.append(daily_ret)

    if not returns_list:
        return np.array([]), []

    return np.array(returns_list), tickers  # shape: (n_tickers, n_days)


# ─── Risk Metrics ─────────────────────────────────────────────────────────────

def _sharpe(portfolio_returns: np.ndarray) -> float:
    """Annualised Sharpe ratio."""
    excess = portfolio_returns - RISK_FREE_RATE
    std = portfolio_returns.std()
    if std == 0:
        return 0.0
    return float(excess.mean() / std * math.sqrt(TRADING_DAYS))


def _sortino(portfolio_returns: np.ndarray) -> float:
    """Annualised Sortino ratio (downside deviation)."""
    excess = portfolio_returns - RISK_FREE_RATE
    downside = portfolio_returns[portfolio_returns < 0]
    if len(downside) == 0:
        return float("inf")
    down_std = downside.std()
    if down_std == 0:
        return 0.0
    return float(excess.mean() / down_std * math.sqrt(TRADING_DAYS))


def _max_drawdown(portfolio_returns: np.ndarray) -> float:
    """Maximum peak-to-trough drawdown as a negative fraction."""
    cumulative = (1 + portfolio_returns).cumprod()
    running_max = np.maximum.accumulate(cumulative)
    drawdowns = (cumulative - running_max) / running_max
    return float(drawdowns.min())


def _var_cvar(portfolio_returns: np.ndarray, confidence: float = 0.95) -> tuple[float, float]:
    """1-day Historical VaR and CVaR (Expected Shortfall)."""
    threshold = np.percentile(portfolio_returns, (1 - confidence) * 100)
    cvar = float(portfolio_returns[portfolio_returns <= threshold].mean())
    return float(threshold), cvar


def _beta(portfolio_returns: np.ndarray, market_returns: np.ndarray) -> float:
    """Portfolio beta vs market."""
    min_len = min(len(portfolio_returns), len(market_returns))
    p = portfolio_returns[-min_len:]
    m = market_returns[-min_len:]
    cov_matrix = np.cov(p, m)
    var_market = cov_matrix[1, 1]
    if var_market == 0:
        return 1.0
    return float(cov_matrix[0, 1] / var_market)


def _correlation_matrix(returns_matrix: np.ndarray) -> np.ndarray:
    """Pearson correlation matrix between tickers."""
    try:
        return np.corrcoef(returns_matrix)
    except Exception:
        return np.eye(len(returns_matrix))


# ─── Portfolio Optimisation ───────────────────────────────────────────────────

def _hrp_weights(returns_matrix: np.ndarray, tickers: list[str]) -> dict[str, float]:
    """
    Hierarchical Risk Parity weights.
    Simple implementation using scipy hierarchical clustering.
    """
    try:
        from scipy.cluster.hierarchy import linkage, to_tree
        from scipy.spatial.distance import squareform

        corr = _correlation_matrix(returns_matrix)
        # Convert correlation to distance
        dist = np.sqrt(np.clip((1 - corr) / 2, 0, 1))
        np.fill_diagonal(dist, 0)

        condensed = squareform(dist, checks=False)
        link = linkage(condensed, method="single")

        # Recursive bisection
        n = len(tickers)
        weights = np.ones(n) / n  # start equal

        def _get_cluster_var(idxs: list[int]) -> float:
            sub = returns_matrix[idxs]
            cov = np.cov(sub) if len(idxs) > 1 else np.array([[np.var(sub[0])]])
            w = np.ones(len(idxs)) / len(idxs)
            return float(w @ cov @ w) if len(idxs) > 1 else float(cov[0, 0])

        root, _ = to_tree(link, rd=True)

        def _hrp_recurse(node, idxs: list[int]) -> dict[int, float]:
            if node.is_leaf():
                return {node.id: 1.0}

            left_ids = node.left.pre_order()
            right_ids = node.right.pre_order()

            left_var = _get_cluster_var(left_ids)
            right_var = _get_cluster_var(right_ids)

            total_var = left_var + right_var
            if total_var == 0:
                alpha = 0.5
            else:
                alpha = right_var / total_var  # left gets more if left has less variance

            left_w = _hrp_recurse(node.left, left_ids)
            right_w = _hrp_recurse(node.right, right_ids)

            result = {}
            for k, v in left_w.items():
                result[k] = v * alpha
            for k, v in right_w.items():
                result[k] = v * (1 - alpha)
            return result

        raw_weights = _hrp_recurse(root, list(range(n)))
        total = sum(raw_weights.values())
        return {tickers[i]: round(w / total, 6) for i, w in sorted(raw_weights.items())}

    except Exception as exc:
        logger.warning("HRP failed, using equal weights: %s", exc)
        w = 1.0 / len(tickers)
        return {t: round(w, 6) for t in tickers}


def _minvar_weights(returns_matrix: np.ndarray, tickers: list[str]) -> dict[str, float]:
    """Minimum variance portfolio weights via quadratic programming (scipy)."""
    try:
        from scipy.optimize import minimize

        cov = np.cov(returns_matrix)
        n = len(tickers)

        def portfolio_var(w):
            return float(w @ cov @ w)

        constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1}]
        bounds = [(0.02, 0.40) for _ in range(n)]  # 2%-40% per position
        w0 = np.ones(n) / n

        result = minimize(portfolio_var, w0, method="SLSQP",
                          bounds=bounds, constraints=constraints,
                          options={"ftol": 1e-9, "maxiter": 1000})

        if result.success:
            w = result.x / result.x.sum()
            return {tickers[i]: round(float(w[i]), 6) for i in range(n)}
        else:
            raise ValueError("Optimisation did not converge")

    except Exception as exc:
        logger.warning("Min-variance failed, using equal weights: %s", exc)
        w = 1.0 / len(tickers)
        return {t: round(w, 6) for t in tickers}


# ─── Factor Exposure ─────────────────────────────────────────────────────────

def _get_factor_exposure(
    tickers: list[str],
    weights: list[float],
    dsn: str,
) -> dict:
    """Fetch scan_results factor scores and compute portfolio + benchmark exposures."""
    try:
        with psycopg2.connect(dsn) as conn, conn.cursor() as cur:
            cur.execute("""
                SELECT ticker,
                       score_value, score_momentum, score_quality,
                       score_growth, score_dividend, score_risk
                FROM scan_results
                WHERE ticker = ANY(%s)
            """, (tickers,))
            rows = {r[0]: r[1:] for r in cur.fetchall()}

            cur.execute("""
                SELECT AVG(score_value), AVG(score_momentum), AVG(score_quality),
                       AVG(score_growth), AVG(score_dividend), AVG(score_risk)
                FROM scan_results
            """)
            bench_row = cur.fetchone()

        factors = ["factor_value", "factor_momentum", "factor_quality",
                   "factor_growth", "factor_dividend", "factor_risk"]

        portfolio_scores = {}
        for i, factor_key in enumerate(factors):
            weighted_sum = 0.0
            total_w = 0.0
            for ticker, w in zip(tickers, weights):
                if ticker in rows and rows[ticker][i] is not None:
                    weighted_sum += float(rows[ticker][i]) * w
                    total_w += w
            portfolio_scores[factor_key] = round(weighted_sum / total_w, 2) if total_w > 0 else None

        bench_factors = {}
        bench_keys = ["bench_value", "bench_momentum", "bench_quality",
                      "bench_growth", "bench_dividend", "bench_risk"]
        for i, bk in enumerate(bench_keys):
            bench_factors[bk] = round(float(bench_row[i]), 2) if bench_row and bench_row[i] is not None else None

        return {**portfolio_scores, **bench_factors}

    except Exception as exc:
        logger.warning("Factor exposure computation failed: %s", exc)
        return {}


# ─── Main Computation ────────────────────────────────────────────────────────

def compute_and_cache(dsn: str) -> int:
    """
    For every user with active holdings:
    1. Fetch holdings from DB
    2. Download price history (yfinance)
    3. Compute all risk metrics
    4. Write to portfolio_risk_cache and portfolio_factor_exposure
    Returns: number of portfolios processed.
    """
    processed = 0
    with psycopg2.connect(dsn) as conn, conn.cursor() as cur:
        # Get all users with at least one holding
        cur.execute("""
            SELECT DISTINCT p.user_id, p.id AS portfolio_id
            FROM portfolios p
            JOIN holdings h ON h.portfolio_id = p.id
        """)
        users = cur.fetchall()

    logger.info("Computing risk for %d portfolios", len(users))

    # Fetch market returns once
    market_prices = _fetch_price_history([MARKET_TICKER], period="1y").get(MARKET_TICKER, [])
    market_returns = np.array([])
    if len(market_prices) > 1:
        arr = np.array(market_prices)
        market_returns = np.diff(arr) / arr[:-1]
        market_returns = np.where(np.isfinite(market_returns), market_returns, 0)

    for user_id, portfolio_id in users:
        try:
            with psycopg2.connect(dsn) as conn, conn.cursor() as cur:
                cur.execute("""
                    SELECT h.ticker, h.shares, h.cost_basis,
                           s.price, s.market_cap
                    FROM holdings h
                    LEFT JOIN scan_results s ON s.ticker = h.ticker
                    WHERE h.portfolio_id = %s
                """, (portfolio_id,))
                rows = cur.fetchall()

            if not rows:
                continue

            tickers = [r[0] for r in rows]
            shares  = [float(r[1]) for r in rows]
            prices  = [float(r[3]) if r[3] else float(r[2] or 0) for r in rows]

            # Portfolio weights by current value
            values  = [s * p for s, p in zip(shares, prices)]
            total_v = sum(values)
            if total_v <= 0:
                continue
            weights = [v / total_v for v in values]

            # ── Price History ──
            price_history = _fetch_price_history(tickers, period="1y")

            # Filter to only tickers with enough data
            valid = [(t, w) for t, w in zip(tickers, weights) if t in price_history]
            if len(valid) < 2:
                logger.info("User %s: not enough price history, skipping", user_id)
                continue

            valid_tickers, valid_weights = zip(*valid)
            valid_tickers = list(valid_tickers)
            valid_weights_norm = np.array(list(valid_weights))
            valid_weights_norm = valid_weights_norm / valid_weights_norm.sum()

            # ── Returns Matrix ──
            returns_matrix, _ = _align_returns(
                {t: price_history[t] for t in valid_tickers}
            )
            if len(returns_matrix) == 0:
                continue

            # ── Portfolio Returns ──
            portfolio_returns = valid_weights_norm @ returns_matrix

            # ── Metrics ──
            sharpe   = _sharpe(portfolio_returns)
            sortino  = _sortino(portfolio_returns)
            max_dd   = _max_drawdown(portfolio_returns)
            cagr     = float(((1 + portfolio_returns).prod() ** (TRADING_DAYS / len(portfolio_returns))) - 1)
            calmar   = abs(cagr / max_dd) if max_dd != 0 else 0.0
            var95, cvar95 = _var_cvar(portfolio_returns)
            vol_ann  = float(portfolio_returns.std() * math.sqrt(TRADING_DAYS))
            total_ret = float((1 + portfolio_returns).prod() - 1)
            beta     = float(_beta(portfolio_returns, market_returns)) if len(market_returns) > 0 else 1.0

            # Concentration
            top_holding_pct = round(max(valid_weights_norm) * 100, 2)

            # HHI for sector concentration — compute from holdings
            sector_values: dict[str, float] = {}
            with psycopg2.connect(dsn) as conn, conn.cursor() as cur:
                cur.execute("""
                    SELECT s.sector, SUM(h.shares * COALESCE(s.price, h.cost_basis, 0))
                    FROM holdings h
                    LEFT JOIN scan_results s ON s.ticker = h.ticker
                    WHERE h.portfolio_id = %s AND s.sector IS NOT NULL
                    GROUP BY s.sector
                """, (portfolio_id,))
                sector_rows = cur.fetchall()
            total_sv = sum(float(r[1]) for r in sector_rows)
            if total_sv > 0:
                sector_hhi = sum((float(r[1]) / total_sv) ** 2 for r in sector_rows)
            else:
                sector_hhi = 0.0

            # ── Correlation Matrix ──
            corr = _correlation_matrix(returns_matrix)
            corr_list = [[round(float(v), 4) for v in row] for row in corr]

            # ── Optimal Weights ──
            hrp_w    = _hrp_weights(returns_matrix, valid_tickers)
            minvar_w = _minvar_weights(returns_matrix, valid_tickers)

            # ── Factor Exposure ──
            factor_exp = _get_factor_exposure(valid_tickers, list(valid_weights_norm), dsn)

            # ── Write to DB ──
            with psycopg2.connect(dsn) as conn, conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO portfolio_risk_cache (
                        user_id, computed_at,
                        sharpe_ratio, sortino_ratio, calmar_ratio,
                        total_return_pct, cagr_pct,
                        volatility_ann, max_drawdown_pct,
                        var_95_pct, cvar_95_pct, beta_market,
                        num_holdings, top_holding_pct, sector_hhi,
                        hrp_weights, minvar_weights,
                        correlation_matrix, tickers_ordered
                    )
                    VALUES (%s, NOW(), %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (user_id) DO UPDATE SET
                        computed_at = NOW(),
                        sharpe_ratio = EXCLUDED.sharpe_ratio,
                        sortino_ratio = EXCLUDED.sortino_ratio,
                        calmar_ratio = EXCLUDED.calmar_ratio,
                        total_return_pct = EXCLUDED.total_return_pct,
                        cagr_pct = EXCLUDED.cagr_pct,
                        volatility_ann = EXCLUDED.volatility_ann,
                        max_drawdown_pct = EXCLUDED.max_drawdown_pct,
                        var_95_pct = EXCLUDED.var_95_pct,
                        cvar_95_pct = EXCLUDED.cvar_95_pct,
                        beta_market = EXCLUDED.beta_market,
                        num_holdings = EXCLUDED.num_holdings,
                        top_holding_pct = EXCLUDED.top_holding_pct,
                        sector_hhi = EXCLUDED.sector_hhi,
                        hrp_weights = EXCLUDED.hrp_weights,
                        minvar_weights = EXCLUDED.minvar_weights,
                        correlation_matrix = EXCLUDED.correlation_matrix,
                        tickers_ordered = EXCLUDED.tickers_ordered
                """, (
                    user_id,
                    round(sharpe, 4), round(sortino, 4), round(calmar, 4),
                    round(total_ret * 100, 4), round(cagr * 100, 4),
                    round(vol_ann * 100, 4), round(max_dd * 100, 4),
                    round(var95 * 100, 4), round(cvar95 * 100, 4), round(beta, 4),
                    len(valid_tickers), top_holding_pct, round(sector_hhi, 6),
                    json.dumps(hrp_w), json.dumps(minvar_w),
                    json.dumps(corr_list), valid_tickers,
                ))
                conn.commit()

                if factor_exp:
                    cur.execute("""
                        INSERT INTO portfolio_factor_exposure
                            (user_id, computed_at,
                             factor_value, factor_momentum, factor_quality,
                             factor_growth, factor_dividend, factor_risk,
                             bench_value, bench_momentum, bench_quality,
                             bench_growth, bench_dividend, bench_risk)
                        VALUES (%s, NOW(), %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (user_id) DO UPDATE SET
                            computed_at = NOW(),
                            factor_value = EXCLUDED.factor_value,
                            factor_momentum = EXCLUDED.factor_momentum,
                            factor_quality = EXCLUDED.factor_quality,
                            factor_growth = EXCLUDED.factor_growth,
                            factor_dividend = EXCLUDED.factor_dividend,
                            factor_risk = EXCLUDED.factor_risk,
                            bench_value = EXCLUDED.bench_value,
                            bench_momentum = EXCLUDED.bench_momentum,
                            bench_quality = EXCLUDED.bench_quality,
                            bench_growth = EXCLUDED.bench_growth,
                            bench_dividend = EXCLUDED.bench_dividend,
                            bench_risk = EXCLUDED.bench_risk
                    """, (
                        user_id,
                        factor_exp.get("factor_value"),
                        factor_exp.get("factor_momentum"),
                        factor_exp.get("factor_quality"),
                        factor_exp.get("factor_growth"),
                        factor_exp.get("factor_dividend"),
                        factor_exp.get("factor_risk"),
                        factor_exp.get("bench_value"),
                        factor_exp.get("bench_momentum"),
                        factor_exp.get("bench_quality"),
                        factor_exp.get("bench_growth"),
                        factor_exp.get("bench_dividend"),
                        factor_exp.get("bench_risk"),
                    ))
                    conn.commit()

            processed += 1
            logger.info(
                "Risk cached for user %s: Sharpe=%.2f MaxDD=%.1f%% VaR95=%.1f%%",
                user_id, sharpe, max_dd * 100, var95 * 100,
            )

        except Exception as exc:
            logger.warning("Risk computation failed for user %s: %s", user_id, exc)
            continue

    return processed


if __name__ == "__main__":
    dsn = os.environ["DATABASE_URL"]
    n = compute_and_cache(dsn)
    logger.info("Risk analysis complete: %d portfolios processed", n)
