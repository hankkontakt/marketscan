"""
company_info_fetcher.py — Fetch company profile data from yfinance.

Fetches longBusinessSummary, employees, website, industry, country, beta,
52-week high/low for all tickers in scan_results and upserts into
company_profiles table (migration 026).

Called from pipeline/entrypoint.py after weekly pipeline runs.

Run standalone:
    python -m backend_worker.company_info_fetcher               # all tickers
    python -m backend_worker.company_info_fetcher --ticker AAPL # single ticker

Note: yfinance is free and needs no API key. Rate-limited to avoid bans
(default 0.4s delay between requests). For ~1 200 tickers ≈ 8 minutes.

Future: add --translate flag to run descriptions through DeepSeek for
Swedish translation and store in description_sv column (migration TBD).
"""
import os
import time
import logging
import argparse

logger = logging.getLogger(__name__)


def fetch_and_store(
    dsn: str,
    tickers: list | None = None,
    delay: float = 0.4,
) -> int:
    """Fetch company profiles from yfinance and upsert into company_profiles.

    Args:
        dsn:     PostgreSQL connection string (DATABASE_URL).
        tickers: List of ticker symbols, or None to use all from scan_results.
        delay:   Seconds to wait between yfinance requests (rate limiting).

    Returns:
        Number of profiles successfully upserted.
    """
    try:
        import yfinance as yf
        import psycopg2
    except ImportError as exc:
        logger.error("Missing dependency: %s  (pip install yfinance psycopg2-binary)", exc)
        return 0

    try:
        conn = psycopg2.connect(dsn)
    except Exception as exc:
        logger.error("DB connection failed: %s", exc)
        return 0

    try:
        cur = conn.cursor()

        # Resolve ticker list
        if tickers is None:
            cur.execute("SELECT ticker FROM scan_results ORDER BY ticker")
            tickers = [row[0] for row in cur.fetchall()]
            logger.info(
                "Fetching company profiles for %d tickers from scan_results",
                len(tickers),
            )

        ok = skipped = errors = 0

        for i, ticker in enumerate(tickers, 1):
            try:
                info = yf.Ticker(ticker).info

                description  = info.get("longBusinessSummary") or None
                employees    = info.get("fullTimeEmployees") or None
                website      = info.get("website") or None
                industry     = info.get("industry") or None
                country      = info.get("country") or None
                beta         = info.get("beta") or None
                week_52_high = info.get("fiftyTwoWeekHigh") or None
                week_52_low  = info.get("fiftyTwoWeekLow") or None

                # Skip if yfinance returned nothing useful at all
                if not any([description, employees, website, industry, beta]):
                    logger.debug("No profile data for %s — skipping", ticker)
                    skipped += 1
                    time.sleep(delay)
                    continue

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
                        ticker, description, employees, website, industry,
                        country, beta, week_52_high, week_52_low,
                    ),
                )
                conn.commit()
                ok += 1

                if i % 100 == 0:
                    logger.info(
                        "Progress: %d/%d (ok=%d, skipped=%d, errors=%d)",
                        i, len(tickers), ok, skipped, errors,
                    )

                time.sleep(delay)

            except Exception as exc:
                logger.warning("Failed to fetch profile for %s: %s", ticker, exc)
                errors += 1
                try:
                    conn.rollback()
                except Exception:
                    pass
                time.sleep(delay)

        logger.info(
            "Company profiles complete: %d updated, %d skipped, %d errors (total %d)",
            ok, skipped, errors, len(tickers),
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
        description="Fetch company profiles from yfinance → company_profiles table"
    )
    parser.add_argument(
        "--ticker",
        help="Single ticker to update (default: all tickers in scan_results)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.4,
        help="Delay in seconds between yfinance requests (default: 0.4)",
    )
    args = parser.parse_args()

    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL environment variable not set")

    ticker_list = [args.ticker.upper()] if args.ticker else None
    n = fetch_and_store(dsn, ticker_list, delay=args.delay)
    print(f"Done: {n} profiles updated")
