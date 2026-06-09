"""
insider_fetcher.py — Fetch insider trading data via Finnhub and store in insider_trades.

Finnhub /stock/insider-transactions endpoint returns insider trades for a given
symbol. We iterate over all tickers in scan_results and upsert new trades.

Deduplication: trades are matched on (ticker, name, trade_date, type, shares).
Only new rows are inserted — existing ones are left unchanged.

Usage:
    python -m backend_worker.insider_fetcher               # all tickers
    python -m backend_worker.insider_fetcher --ticker ERIC-B.ST
    python -m backend_worker.insider_fetcher --days 90     # fetch trades from last 90 days

Schedule: runs nightly (03:30 UTC) after the main pipeline.
"""
import os
import time
import logging
import argparse
import urllib.request
import json
from datetime import date, timedelta

logger = logging.getLogger(__name__)

# Finnhub free tier: 60 calls/min. We sleep 1.1s between calls to stay safe.
_FINNHUB_DELAY = 1.1

# Transaction codes that map to "buy" vs "sell"
# Finnhub uses standard SEC transaction codes:
#   P = Purchase (open market buy)
#   S = Sale (open market sell)
#   A = Grant/Award (also treated as buy-side)
_BUY_CODES  = {"P", "A", "JJ"}
_SELL_CODES = {"S", "D", "F", "I", "G"}


def _strip_exchange(ticker: str) -> str:
    """VOLV-B.ST → VOLV-B  (Finnhub uses base symbol without exchange suffix)."""
    return ticker.split(".")[0]


def _classify_trade(code: str) -> str | None:
    """Return 'buy', 'sell', or None (skip) for a Finnhub transaction code."""
    if not code:
        return None
    code = code.upper()
    if code in _BUY_CODES:
        return "buy"
    if code in _SELL_CODES:
        return "sell"
    return None


def _fetch_finnhub_insider(ticker: str, api_key: str, from_date: str) -> list[dict]:
    """
    Fetch insider transactions for one ticker from Finnhub.

    Args:
        ticker:    e.g. "ERIC-B.ST"  → stripped to "ERIC-B" for Finnhub
        api_key:   Finnhub API key
        from_date: ISO date string (YYYY-MM-DD), only include trades on/after this date

    Returns:
        List of dicts with keys: name, role, type, shares, amount, trade_date
    """
    base = _strip_exchange(ticker)
    url = (
        f"https://finnhub.io/api/v1/stock/insider-transactions"
        f"?symbol={base}&from={from_date}&token={api_key}"
    )
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read())
    except Exception as exc:
        logger.debug("Finnhub insider failed for %s: %s", ticker, exc)
        return []

    raw_trades = data.get("data") or []
    result = []
    for item in raw_trades:
        trade_date = item.get("transactionDate") or ""
        if not trade_date or trade_date < from_date:
            continue

        trade_type = _classify_trade(item.get("transactionCode", ""))
        if trade_type is None:
            continue  # skip options awards, plan entries, etc.

        shares = item.get("share")
        amount_change = item.get("change")  # net change in shares owned (signed)

        # Finnhub doesn't provide SEK amount directly — use |change × price|
        # as a proxy. We store None if we can't compute it.
        price = item.get("transactionPrice")
        amount_sek: float | None = None
        if price and amount_change is not None:
            try:
                amount_sek = abs(float(amount_change) * float(price))
            except (TypeError, ValueError):
                pass

        result.append({
            "ticker":     ticker,
            "name":       (item.get("name") or "").strip() or "Unknown",
            "role":       (item.get("position") or "").strip() or None,
            "type":       trade_type,
            "shares":     float(shares) if shares is not None else None,
            "amount":     amount_sek,
            "trade_date": trade_date,
        })

    return result


def fetch_and_store(
    dsn: str,
    tickers: list | None = None,
    lookback_days: int = 90,
    delay: float = _FINNHUB_DELAY,
) -> int:
    """
    Fetch insider trades for all (or given) tickers and upsert into insider_trades.

    Args:
        dsn:           PostgreSQL connection string (DATABASE_URL).
        tickers:       List of ticker symbols, or None to use all from scan_results.
        lookback_days: How many days back to fetch (default: 90).
        delay:         Seconds to sleep between Finnhub calls.

    Returns:
        Number of new rows inserted.
    """
    try:
        import psycopg2
        import psycopg2.extras
    except ImportError as exc:
        logger.error("Missing dependency: %s  (pip install psycopg2-binary)", exc)
        return 0

    api_key = os.environ.get("FINNHUB_API_KEY", "")
    if not api_key:
        logger.error("FINNHUB_API_KEY is not set — cannot fetch insider data")
        return 0

    from_date = (date.today() - timedelta(days=lookback_days)).isoformat()
    logger.info("Fetching insider trades from %s (lookback %d days)", from_date, lookback_days)

    try:
        conn = psycopg2.connect(dsn)
    except Exception as exc:
        logger.error("DB connection failed: %s", exc)
        return 0

    try:
        cur = conn.cursor()

        if tickers is None:
            cur.execute("SELECT DISTINCT ticker FROM scan_results ORDER BY ticker")
            tickers = [row[0] for row in cur.fetchall()]
            logger.info("Scanning %d tickers for insider trades", len(tickers))

        inserted = errors = skipped = 0

        for i, ticker in enumerate(tickers, 1):
            try:
                trades = _fetch_finnhub_insider(ticker, api_key, from_date)
                time.sleep(delay)

                if not trades:
                    skipped += 1
                    continue

                for t in trades:
                    # Upsert: skip if same (ticker, name, trade_date, type) already exists
                    cur.execute(
                        """
                        INSERT INTO insider_trades
                            (ticker, name, role, type, shares, amount, trade_date)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT DO NOTHING
                        """,
                        (
                            t["ticker"],
                            t["name"],
                            t["role"],
                            t["type"],
                            t["shares"],
                            t["amount"],
                            t["trade_date"],
                        ),
                    )
                    if cur.rowcount > 0:
                        inserted += 1

                conn.commit()

                if i % 100 == 0:
                    logger.info(
                        "Progress: %d/%d — inserted=%d, skipped=%d, errors=%d",
                        i, len(tickers), inserted, skipped, errors,
                    )

            except Exception as exc:
                logger.warning("Failed for %s: %s", ticker, exc)
                errors += 1
                try:
                    conn.rollback()
                except Exception:
                    pass
                time.sleep(delay)

        logger.info(
            "Insider fetch complete: %d new trades inserted, %d tickers skipped (no data), %d errors",
            inserted, skipped, errors,
        )
        return inserted

    finally:
        try:
            conn.close()
        except Exception:
            pass


def _add_unique_constraint(dsn: str) -> None:
    """
    Add a unique constraint on (ticker, name, trade_date, type) so ON CONFLICT DO NOTHING
    works correctly. Idempotent — does nothing if the constraint already exists.
    """
    try:
        import psycopg2
        conn = psycopg2.connect(dsn)
        cur = conn.cursor()
        cur.execute("""
            DO $$
            BEGIN
              IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'insider_trades_dedup_key'
              ) THEN
                ALTER TABLE insider_trades
                  ADD CONSTRAINT insider_trades_dedup_key
                  UNIQUE (ticker, name, trade_date, type);
              END IF;
            END
            $$;
        """)
        conn.commit()
        conn.close()
        logger.info("Unique constraint on insider_trades ensured")
    except Exception as exc:
        logger.warning("Could not add unique constraint (may already exist): %s", exc)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    parser = argparse.ArgumentParser(
        description="Fetch insider trades (Finnhub) and store in insider_trades"
    )
    parser.add_argument("--ticker", help="Single ticker (default: all in scan_results)")
    parser.add_argument("--days", type=int, default=90, help="Lookback days (default: 90)")
    parser.add_argument("--delay", type=float, default=_FINNHUB_DELAY, help="Delay between calls")
    args = parser.parse_args()

    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL environment variable not set")

    # Ensure dedup constraint exists
    _add_unique_constraint(dsn)

    ticker_list = [args.ticker.upper()] if args.ticker else None
    n = fetch_and_store(dsn, ticker_list, lookback_days=args.days, delay=args.delay)
    print(f"Done: {n} new insider trades stored")
