"""
company_info_fetcher.py — Fetch company profile data with multi-source fallback.

Sources (tried in order per ticker):
  1. yfinance  — free, no key, good for US + large Swedish caps
  2. Finnhub   — requires FINNHUB_API_KEY, good coverage for Stockholm-listed stocks
  3. FMP       — requires FMP_API_KEY, additional fallback

Typical coverage:
  • Large Swedish caps (VOLV-B.ST, ERIC-B.ST, etc.): yfinance often has description
  • Mid/small Swedish (First North, NGM): yfinance usually empty → Finnhub fills in
  • US stocks: yfinance excellent

For Swedish tickers yfinance uses .ST suffix (e.g. VOLV-B.ST).
Finnhub/FMP use the base symbol without exchange suffix (e.g. VOLV-B).

Called from pipeline/entrypoint.py after weekly pipeline runs.

Run standalone:
    python -m backend_worker.company_info_fetcher               # all tickers
    python -m backend_worker.company_info_fetcher --ticker ERIC-B.ST

Future: add --translate flag to run descriptions through DeepSeek for
Swedish translation and store in description_sv column (migration TBD).
"""
import os
import time
import logging
import argparse

logger = logging.getLogger(__name__)

# Finnhub free tier: 60 calls/min. With ~1200 tickers and 3-source fallback
# we stay well under that at one ticker per second.
_FINNHUB_DELAY = 1.1   # seconds between Finnhub calls

# How many chars minimum to accept as a "real" description (filter out
# boilerplate like "N/A" or single-sentence placeholders).
_MIN_DESCRIPTION_LENGTH = 80


def _strip_exchange(ticker: str) -> str:
    """VOLV-B.ST → VOLV-B  (strip exchange suffix for Finnhub/FMP)."""
    return ticker.split(".")[0]


def _fetch_yfinance(ticker: str) -> dict:
    """Fetch via yfinance. Returns partial dict (some fields may be None)."""
    try:
        import yfinance as yf
        info = yf.Ticker(ticker).info
        return {
            "description":  info.get("longBusinessSummary") or None,
            "employees":    info.get("fullTimeEmployees") or None,
            "website":      info.get("website") or None,
            "industry":     info.get("industry") or None,
            "country":      info.get("country") or None,
            "beta":         info.get("beta") or None,
            "week_52_high": info.get("fiftyTwoWeekHigh") or None,
            "week_52_low":  info.get("fiftyTwoWeekLow") or None,
        }
    except Exception as exc:
        logger.debug("yfinance failed for %s: %s", ticker, exc)
        return {}


def _fetch_finnhub(ticker: str, api_key: str) -> dict:
    """Fetch via Finnhub /stock/profile2.

    NOTE: Finnhub free tier does NOT include a description/summary field.
    This gives us: employees, website, industry, country — useful for
    Swedish stocks where yfinance returns nothing at all.
    """
    import urllib.request
    import json

    base = _strip_exchange(ticker)
    url = f"https://finnhub.io/api/v1/stock/profile2?symbol={base}&token={api_key}"
    try:
        with urllib.request.urlopen(url, timeout=8) as resp:
            data = json.loads(resp.read())
    except Exception as exc:
        logger.debug("Finnhub failed for %s: %s", ticker, exc)
        return {}

    if not data or not data.get("name"):
        return {}

    return {
        "description":  None,  # Not available in Finnhub free tier
        "employees":    int(data["employeeTotal"]) if data.get("employeeTotal") else None,
        "website":      data.get("weburl") or None,
        "industry":     data.get("finnhubIndustry") or None,
        "country":      data.get("country") or None,
        "beta":         None,  # Not in profile2
        "week_52_high": None,
        "week_52_low":  None,
    }


def _fetch_fmp(ticker: str, api_key: str) -> dict:
    """Fetch via FMP /profile/{ticker}. Returns partial dict.

    FMP has good description coverage including many Swedish stocks.
    Endpoint: GET /api/v3/profile/{symbol}  → returns list of profile objects.
    """
    import urllib.request
    import json

    base = _strip_exchange(ticker)
    # Try without exchange suffix first (FMP prefers VOLV-B over VOLV-B.ST)
    for sym in [base, ticker]:
        url = f"https://financialmodelingprep.com/api/v3/profile/{sym}?apikey={api_key}"
        try:
            with urllib.request.urlopen(url, timeout=8) as resp:
                raw = json.loads(resp.read())
                # FMP returns a list; first element is the profile
                p = raw[0] if isinstance(raw, list) and raw else {}
                if not p or not p.get("symbol"):
                    continue
                # Parse 52-week range — format: "123.45 - 234.56"
                hi = lo = None
                rng = p.get("range") or ""
                if " - " in rng:
                    parts = rng.split(" - ")
                    try:
                        lo = float(parts[0].strip())
                        hi = float(parts[1].strip())
                    except ValueError:
                        pass
                return {
                    "description":  p.get("description") or None,
                    "employees":    int(p["fullTimeEmployees"]) if p.get("fullTimeEmployees") else None,
                    "website":      p.get("website") or None,
                    "industry":     p.get("industry") or None,
                    "country":      p.get("country") or None,
                    "beta":         float(p["beta"]) if p.get("beta") else None,
                    "week_52_high": hi,
                    "week_52_low":  lo,
                }
        except Exception as exc:
            logger.debug("FMP failed for %s: %s", sym, exc)
    return {}


def _merge(base: dict, extra: dict) -> dict:
    """Fill None values in base with values from extra."""
    result = dict(base)
    for k, v in extra.items():
        if result.get(k) is None and v is not None:
            result[k] = v
    return result


def _has_useful_data(d: dict) -> bool:
    """True if dict has at least some non-None, non-trivial values."""
    desc = d.get("description") or ""
    return (
        (len(desc) >= _MIN_DESCRIPTION_LENGTH) or
        d.get("employees") is not None or
        d.get("website") is not None or
        d.get("industry") is not None or
        d.get("beta") is not None
    )


def fetch_and_store(
    dsn: str,
    tickers: list | None = None,
    delay: float = 0.4,
) -> int:
    """Fetch company profiles from multi-source waterfall and upsert into company_profiles.

    Sources tried per ticker:
      1. yfinance (always)
      2. Finnhub (if FINNHUB_API_KEY is set and description still missing)
      3. FMP (if FMP_API_KEY is set and description still missing)

    Args:
        dsn:     PostgreSQL connection string (DATABASE_URL).
        tickers: List of ticker symbols, or None to use all from scan_results.
        delay:   Base delay between yfinance calls.

    Returns:
        Number of profiles successfully upserted.
    """
    try:
        import psycopg2
    except ImportError as exc:
        logger.error("Missing dependency: %s  (pip install psycopg2-binary)", exc)
        return 0

    finnhub_key = os.environ.get("FINNHUB_API_KEY", "")
    fmp_key     = os.environ.get("FMP_API_KEY", "")

    if finnhub_key:
        logger.info("Finnhub fallback: enabled")
    if fmp_key:
        logger.info("FMP fallback: enabled")
    if not finnhub_key and not fmp_key:
        logger.info(
            "Only yfinance available — coverage for Swedish small-caps will be limited. "
            "Set FINNHUB_API_KEY for better coverage."
        )

    try:
        conn = psycopg2.connect(dsn)
    except Exception as exc:
        logger.error("DB connection failed: %s", exc)
        return 0

    try:
        cur = conn.cursor()

        if tickers is None:
            cur.execute("SELECT ticker FROM scan_results ORDER BY ticker")
            tickers = [row[0] for row in cur.fetchall()]
            logger.info(
                "Fetching company profiles for %d tickers from scan_results",
                len(tickers),
            )

        ok = skipped = errors = 0
        source_counts = {"yfinance": 0, "finnhub": 0, "fmp": 0}

        for i, ticker in enumerate(tickers, 1):
            try:
                # ── 1. yfinance ──────────────────────────────────────────────
                data = _fetch_yfinance(ticker)
                time.sleep(delay)

                # ── 2. Finnhub fallback — fill missing fields ─────────────────
                # Always call if description is missing (most Swedish small-caps)
                if finnhub_key and not (data.get("description") and len(data["description"] or "") >= _MIN_DESCRIPTION_LENGTH):
                    fh = _fetch_finnhub(ticker, finnhub_key)
                    if fh:
                        data = _merge(data, fh)
                        if fh.get("description") or fh.get("employees") or fh.get("website"):
                            source_counts["finnhub"] += 1
                    time.sleep(_FINNHUB_DELAY)

                # ── 3. FMP fallback — fill any remaining gaps ─────────────────
                if fmp_key and not (data.get("description") and len(data["description"] or "") >= _MIN_DESCRIPTION_LENGTH):
                    fm = _fetch_fmp(ticker, fmp_key)
                    if fm:
                        data = _merge(data, fm)
                        if fm.get("description") or fm.get("beta"):
                            source_counts["fmp"] += 1

                # ── Decide whether to store ───────────────────────────────────
                if not _has_useful_data(data):
                    logger.debug("No useful profile data for %s — skipping", ticker)
                    skipped += 1
                    continue

                # Clamp description length (some summaries are extremely long)
                desc = data.get("description") or None
                if desc and len(desc) > 2000:
                    desc = desc[:1997] + "…"

                cur.execute(
                    """
                    INSERT INTO company_profiles
                        (ticker, description, employees, website, industry,
                         country, beta, week_52_high, week_52_low, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                    ON CONFLICT (ticker) DO UPDATE SET
                        description  = EXCLUDED.description,
                        employees    = EXCLUDED.employees,
                        website      = EXCLUDED.website,
                        industry     = EXCLUDED.industry,
                        country      = EXCLUDED.country,
                        beta         = EXCLUDED.beta,
                        week_52_high = EXCLUDED.week_52_high,
                        week_52_low  = EXCLUDED.week_52_low,
                        updated_at   = NOW()
                    """,
                    (
                        ticker,
                        desc,
                        data.get("employees"),
                        data.get("website"),
                        data.get("industry"),
                        data.get("country"),
                        data.get("beta"),
                        data.get("week_52_high"),
                        data.get("week_52_low"),
                    ),
                )
                conn.commit()
                ok += 1

                if i % 50 == 0:
                    logger.info(
                        "Progress: %d/%d (ok=%d, skipped=%d, errors=%d | "
                        "finnhub_fills=%d, fmp_fills=%d)",
                        i, len(tickers), ok, skipped, errors,
                        source_counts["finnhub"], source_counts["fmp"],
                    )

            except Exception as exc:
                logger.warning("Failed to process %s: %s", ticker, exc)
                errors += 1
                try:
                    conn.rollback()
                except Exception:
                    pass
                time.sleep(delay)

        logger.info(
            "Company profiles complete: %d updated, %d skipped (no data), %d errors | "
            "sources: yfinance baseline, finnhub fills=%d, fmp fills=%d",
            ok, skipped, errors,
            source_counts["finnhub"], source_counts["fmp"],
        )
        return ok

    finally:
        try:
            conn.close()
        except Exception:
            pass


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    parser = argparse.ArgumentParser(
        description="Fetch company profiles (yfinance + Finnhub + FMP fallback)"
    )
    parser.add_argument(
        "--ticker",
        help="Single ticker to update (default: all tickers in scan_results)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.4,
        help="Base delay between yfinance calls in seconds (default: 0.4)",
    )
    args = parser.parse_args()

    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL environment variable not set")

    ticker_list = [args.ticker.upper()] if args.ticker else None
    n = fetch_and_store(dsn, ticker_list, delay=args.delay)
    print(f"Done: {n} profiles updated")
