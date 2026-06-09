"""
Live portfolio risk metrics from 1-year daily price history.

Why this exists: the risk endpoint only had two real-time metrics (beta and
volatility, from per-stock scan_results factors). Sharpe, Sortino, max drawdown,
VaR and CVaR were left empty unless a nightly job had pre-computed them into
portfolio_risk_cache — so a freshly built portfolio showed "–" for most metrics.

This computes them on demand from actual price history. Pure Python only
(statistics + math) because pandas/numpy are NOT in the API bundle. Prices come
from Yahoo's v8 chart endpoint over httpx (in the bundle). Best-effort: returns
{} if there isn't enough history, so the caller can fall back gracefully.
"""
from __future__ import annotations

import logging
import math
import statistics
import time

import httpx

logger = logging.getLogger(__name__)

_CHART = "https://query1.finance.yahoo.com/v8/finance/chart/{sym}"
_UA = {"User-Agent": "Mozilla/5.0 (compatible; MarketScan/1.0)"}
_TRADING_DAYS = 252

_hist_cache: dict[str, tuple[dict, float]] = {}  # ticker -> ({ts: close}, fetched_at)
_HIST_TTL_S = 3600  # 1 h — daily history barely changes intraday


def _fetch_history(client: httpx.Client, ticker: str) -> dict:
    """{timestamp: close} of ~1y daily closes for one ticker. {} on failure."""
    now = time.time()
    hit = _hist_cache.get(ticker)
    if hit and now - hit[1] < _HIST_TTL_S:
        return hit[0]
    try:
        r = client.get(
            _CHART.format(sym=ticker),
            params={"range": "1y", "interval": "1d"},
            headers=_UA,
            timeout=10.0,
        )
        if r.status_code != 200:
            return {}
        res = r.json()["chart"]["result"][0]
        ts = res.get("timestamp") or []
        closes = res["indicators"]["quote"][0]["close"]
        hist = {t: c for t, c in zip(ts, closes) if c is not None}
        _hist_cache[ticker] = (hist, now)
        return hist
    except Exception as e:
        logger.debug("history %s failed: %s", ticker, e)
        return {}


def _returns(values: list[float]) -> list[float]:
    return [
        (values[i] - values[i - 1]) / values[i - 1]
        for i in range(1, len(values))
        if values[i - 1]
    ]


def compute_live_risk(holdings: list[dict], benchmark: str = "^OMX") -> dict:
    """
    holdings: [{"ticker", "shares"}]. Returns a dict of risk metrics (percent
    units where the schema expects percent), or {} if there is too little data.
    """
    rows = [h for h in holdings if h.get("ticker") and h.get("shares")]
    if not rows:
        return {}

    try:
        with httpx.Client() as client:
            hist = {h["ticker"]: _fetch_history(client, h["ticker"]) for h in rows}
            bench = _fetch_history(client, benchmark)
    except Exception as e:
        logger.warning("risk history fetch failed: %s", e)
        return {}

    valid = {t: h for t, h in hist.items() if len(h) > 30}
    if not valid:
        return {}

    common = sorted(set.intersection(*[set(h.keys()) for h in valid.values()]))
    if len(common) < 30:
        return {}

    shares = {h["ticker"]: float(h["shares"]) for h in rows if h["ticker"] in valid}
    values = [sum(valid[t][d] * shares[t] for t in valid) for d in common]
    rets = _returns(values)
    if len(rets) < 20:
        return {}

    mean = statistics.fmean(rets)
    std = statistics.pstdev(rets) or 1e-9
    sqrt_y = math.sqrt(_TRADING_DAYS)

    downside = [r for r in rets if r < 0]
    dstd = statistics.pstdev(downside) if len(downside) > 1 else 0.0

    # Max drawdown over the cumulative curve
    cum, peak, maxdd = 1.0, 1.0, 0.0
    for r in rets:
        cum *= (1 + r)
        peak = max(peak, cum)
        maxdd = min(maxdd, (cum - peak) / peak)

    srt = sorted(rets)
    k = max(0, int(len(srt) * 0.05))
    var95 = -srt[k]
    tail = srt[: k + 1]
    cvar95 = -statistics.fmean(tail) if tail else var95

    total_return = values[-1] / values[0] - 1 if values[0] else 0.0
    cagr = (values[-1] / values[0]) ** (_TRADING_DAYS / len(rets)) - 1 if values[0] else None

    # Beta vs benchmark (e.g. OMXS30)
    beta = None
    if len(bench) > 30:
        bdays = sorted(set(common) & set(bench.keys()))
        if len(bdays) > 21:
            pv = [sum(valid[t][d] * shares[t] for t in valid) for d in bdays]
            bv = [bench[d] for d in bdays]
            pr, br = _returns(pv), _returns(bv)
            m = min(len(pr), len(br))
            if m > 20:
                pr, br = pr[-m:], br[-m:]
                pmean, bmean = statistics.fmean(pr), statistics.fmean(br)
                cov = sum((pr[i] - pmean) * (br[i] - bmean) for i in range(m)) / m
                bvar = statistics.pvariance(br) or 1e-9
                beta = cov / bvar

    return {
        "sharpe_ratio": round((mean / std) * sqrt_y, 2),
        "sortino_ratio": round((mean / dstd) * sqrt_y, 2) if dstd else None,
        "volatility_ann": round(std * sqrt_y * 100, 2),
        "max_drawdown_pct": round(maxdd * 100, 2),
        "var_95_pct": round(var95 * 100, 2),
        "cvar_95_pct": round(cvar95 * 100, 2),
        "total_return_pct": round(total_return * 100, 2),
        "cagr_pct": round(cagr * 100, 2) if cagr is not None else None,
        "beta_market": round(beta, 2) if beta is not None else None,
        "days": len(rets),
    }
