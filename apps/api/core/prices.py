"""
Live price lookup for a set of tickers.

The pipeline currently leaves `scan_results.price` NULL, and even when it is
populated it is a once-a-day snapshot. A portfolio should show the CURRENT
market value, so we fetch live prices here via yfinance (already a dependency,
used for the global indices). Swedish tickers like INVE-B.ST work directly.

Design rules:
  - Best-effort: NEVER raises. On any failure it returns a partial/empty dict,
    so the portfolio still loads (prices just show "–" instead of breaking).
  - Cached in-memory for 5 min to avoid hammering Yahoo on every page load.
  - One batched yf.download call for all tickers (fast for a normal portfolio).
"""
from __future__ import annotations

import logging
import time

logger = logging.getLogger(__name__)

_CACHE_TTL_S = 300
_cache: dict[str, tuple[float, float]] = {}  # ticker -> (price, fetched_at)


def fetch_live_prices(tickers: list[str]) -> dict[str, float]:
    """Return {ticker: latest_close} for as many tickers as we can resolve."""
    wanted = sorted({t for t in (tickers or []) if t})
    if not wanted:
        return {}

    now = time.time()
    out: dict[str, float] = {}
    to_fetch: list[str] = []
    for t in wanted:
        hit = _cache.get(t)
        if hit and now - hit[1] < _CACHE_TTL_S:
            out[t] = hit[0]
        else:
            to_fetch.append(t)

    if not to_fetch:
        return out

    try:
        import yfinance as yf

        df = yf.download(
            to_fetch, period="2d", progress=False, threads=True, auto_adjust=True
        )
        if df is not None and not df.empty and "Close" in df:
            close = df["Close"]
            if hasattr(close, "columns"):  # multiple tickers -> DataFrame
                for t in to_fetch:
                    if t in close.columns:
                        series = close[t].dropna()
                        if len(series):
                            out[t] = round(float(series.iloc[-1]), 2)
            else:  # single ticker -> Series
                series = close.dropna()
                if len(series):
                    out[to_fetch[0]] = round(float(series.iloc[-1]), 2)
    except Exception as e:  # network, yahoo change, missing lib — all non-fatal
        logger.warning("Live price fetch failed for %s: %s", to_fetch, e)

    # cache whatever we got
    for t, p in out.items():
        _cache[t] = (p, now)
    return out
