"""
Live price lookup for a set of tickers — httpx only.

IMPORTANT: the API serverless bundle deliberately EXCLUDES yfinance/pandas
(see apps/api/requirements.txt: "CRITICAL: NO pandas, xgboost, yfinance …").
An earlier version imported yfinance and silently returned nothing in
production (it only worked locally). This version uses Yahoo's public v8 chart
endpoint over httpx — which IS in the bundle — so it works on Vercel.

The pipeline leaves scan_results.price NULL, and even when populated it is a
once-a-day snapshot, so the portfolio fetches current prices here.

Design rules:
  - Best-effort: NEVER raises. Returns a partial/empty dict on any failure, so
    the portfolio still loads (prices just show "–").
  - 5-min in-memory cache to avoid hammering Yahoo on every page load.
  - A browser User-Agent is required or Yahoo returns 403/429.
"""
from __future__ import annotations

import logging
import time

import httpx

logger = logging.getLogger(__name__)

_CACHE_TTL_S = 300
# ticker -> ({"price": float, "change_pct": float|None}, fetched_at)
_cache: dict[str, tuple[dict, float]] = {}

_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{sym}"
_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; MarketScan/1.0; +https://marketscan.app)"}


def _fetch_one(client: httpx.Client, ticker: str) -> dict | None:
    """Latest price + day change for one ticker via Yahoo v8 chart.
    Returns {"price", "change_pct"} or None on any failure."""
    try:
        r = client.get(
            _CHART_URL.format(sym=ticker),
            params={"range": "1d", "interval": "1d"},
            headers=_HEADERS,
            timeout=8.0,
        )
        if r.status_code != 200:
            logger.debug("price %s: HTTP %s", ticker, r.status_code)
            return None
        meta = r.json()["chart"]["result"][0]["meta"]
        price = meta.get("regularMarketPrice") or meta.get("previousClose")
        if price is None:
            return None
        prev = meta.get("chartPreviousClose") or meta.get("previousClose")
        # change_pct is a FRACTION (0.0085 == 0.85%) — the frontend formats it
        # with Intl percent style, which multiplies by 100. Returning a percent
        # here (0.85) would render as 85%.
        change_pct = None
        if prev:
            change_pct = round((float(price) - float(prev)) / float(prev), 4)
        return {"price": round(float(price), 2), "change_pct": change_pct}
    except Exception as e:
        logger.debug("price %s failed: %s", ticker, e)
        return None


def fetch_live_quotes(tickers: list[str]) -> dict[str, dict]:
    """Return {ticker: {"price", "change_pct"}} for resolvable tickers."""
    wanted = sorted({t for t in (tickers or []) if t})
    if not wanted:
        return {}

    now = time.time()
    out: dict[str, dict] = {}
    to_fetch: list[str] = []
    for t in wanted:
        hit = _cache.get(t)
        if hit and now - hit[1] < _CACHE_TTL_S:
            out[t] = hit[0]
        else:
            to_fetch.append(t)

    if to_fetch:
        try:
            with httpx.Client() as client:
                for t in to_fetch:
                    q = _fetch_one(client, t)
                    if q is not None:
                        out[t] = q
                        _cache[t] = (q, now)
        except Exception as e:  # client construction / unexpected — non-fatal
            logger.warning("live price fetch failed: %s", e)

    return out


def fetch_live_prices(tickers: list[str]) -> dict[str, float]:
    """Return {ticker: latest_price} — convenience wrapper over fetch_live_quotes."""
    return {t: q["price"] for t, q in fetch_live_quotes(tickers).items()}
