"""
backfill_roe_raw.py — Idempotent backfill of raw ROE from yfinance into scan_results.

Fetches yfinance returnOnEquity for rows where roe_raw IS NULL.
Can run via psycopg2 (DATABASE_URL) or supabase-py (SUPABASE_URL + SUPABASE_SERVICE_KEY).

Usage:
  python backend_worker/backfill_roe_raw.py --batch 50
  python backend_worker/backfill_roe_raw.py --limit 200 --batch 25
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from typing import Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("backfill_roe_raw")


def get_yfinance_roe(ticker: str) -> Optional[float]:
    """Fetch returnOnEquity from yfinance. Returns ratio (e.g. 0.17 for 17%)."""
    try:
        import yfinance as yf
        t = yf.Ticker(ticker)
        info = t.info or {}
        roe = info.get("returnOnEquity")
        if roe is not None and isinstance(roe, (int, float)):
            # Guard against extreme anomalies
            if -10.0 <= roe <= 10.0:
                return float(roe)
        return None
    except Exception as e:
        logger.debug("Failed to fetch yfinance ROE for %s: %s", ticker, e)
        return None


def run_backfill_psycopg2(dsn: str, batch_size: int, limit: Optional[int]) -> int:
    import psycopg2
    conn = psycopg2.connect(dsn)
    conn.autocommit = True
    updated_count = 0

    try:
        with conn.cursor() as cur:
            query = "SELECT ticker FROM scan_results WHERE roe_raw IS NULL ORDER BY ticker"
            if limit:
                query += f" LIMIT {int(limit)}"
            cur.execute(query)
            tickers = [r[0] for r in cur.fetchall()]

        logger.info("Found %d tickers with roe_raw IS NULL", len(tickers))

        for i in range(0, len(tickers), batch_size):
            batch = tickers[i:i + batch_size]
            logger.info("Processing batch %d-%d of %d...", i + 1, min(i + len(batch), len(tickers)), len(tickers))

            updates = []
            for ticker in batch:
                roe = get_yfinance_roe(ticker)
                if roe is not None:
                    updates.append((roe, ticker))
                time.sleep(0.1)  # small throttle for yfinance

            if updates:
                with conn.cursor() as cur:
                    for roe_val, t in updates:
                        cur.execute("UPDATE scan_results SET roe_raw = %s WHERE ticker = %s", (roe_val, t))
                    updated_count += len(updates)
                logger.info("Updated %d/%d tickers in batch", len(updates), len(batch))
            else:
                logger.info("No ROE values found in current batch")

    finally:
        conn.close()

    return updated_count


def run_backfill_supabase(batch_size: int, limit: Optional[int]) -> int:
    from supabase import create_client
    url = os.environ["SUPABASE_URL"]
    key = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_KEY")
    if not key:
        raise ValueError("SUPABASE_SERVICE_KEY or SUPABASE_KEY required")

    sb = create_client(url, key)
    query = sb.table("scan_results").select("ticker").is_("roe_raw", "null")
    if limit:
        query = query.limit(limit)
    res = query.execute()
    tickers = [r["ticker"] for r in (res.data or [])]

    logger.info("Found %d tickers with roe_raw IS NULL", len(tickers))
    updated_count = 0

    for i in range(0, len(tickers), batch_size):
        batch = tickers[i:i + batch_size]
        logger.info("Processing batch %d-%d of %d...", i + 1, min(i + len(batch), len(tickers)), len(tickers))

        for ticker in batch:
            roe = get_yfinance_roe(ticker)
            if roe is not None:
                try:
                    sb.table("scan_results").update({"roe_raw": roe}).eq("ticker", ticker).execute()
                    updated_count += 1
                except Exception as e:
                    logger.warning("Failed to update roe_raw for %s: %s", ticker, e)
            time.sleep(0.1)

    return updated_count


def main():
    parser = argparse.ArgumentParser(description="Backfill roe_raw from yfinance into scan_results")
    parser.add_argument("--batch", type=int, default=50, help="Batch size (default: 50)")
    parser.add_argument("--limit", type=int, default=None, help="Maximum number of tickers to process")
    parser.add_argument("--dsn", type=str, default=None, help="Postgres DSN (default: DATABASE_URL env)")
    args = parser.parse_args()

    dsn = args.dsn or os.environ.get("DATABASE_URL")
    if dsn:
        logger.info("Connecting via Postgres DSN")
        updated = run_backfill_psycopg2(dsn, args.batch, args.limit)
    elif os.environ.get("SUPABASE_URL"):
        logger.info("Connecting via Supabase API")
        updated = run_backfill_supabase(args.batch, args.limit)
    else:
        logger.warning("No DATABASE_URL or SUPABASE_URL set in environment. Dry run / schema validation.")
        return 0

    logger.info("Backfill complete. Updated %d rows.", updated)
    return 0


if __name__ == "__main__":
    sys.exit(main())
