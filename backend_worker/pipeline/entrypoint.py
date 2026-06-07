"""
GitHub Actions entrypoint — bridges existing core/ logic to new storage.
Imports from stock-scanner-fix/core/ via PYTHONPATH.
Run: python -m backend_worker.pipeline.entrypoint --mode morning
"""
import sys
import time
import logging
import argparse
import os

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def _segment_from_market_cap(market_cap_millions: float | None) -> str:
    """Determine segment from Finnhub marketCapitalization (in USD millions)."""
    if market_cap_millions is None:
        return "small_cap"
    if market_cap_millions >= 10_000:
        return "large_cap"
    if market_cap_millions >= 1_000:
        return "mid_cap"
    if market_cap_millions >= 100:
        return "small_cap"
    return "micro_cap"


def supplement_user_requested_tickers(dsn: str) -> None:
    """After the main pipeline, add basic Finnhub data for user-requested tickers.

    When a user adds a stock outside the current universe to their watchlist or
    portfolio, it lands in user_ticker_requests. This function fetches profile +
    quote from Finnhub for each pending ticker and inserts a basic row into
    scan_results so the stock appears in search results on the next page load.

    Only runs when FINNHUB_API_KEY is set. Non-fatal: a failure here does not
    roll back the main pipeline run.
    """
    finnhub_key = os.environ.get("FINNHUB_API_KEY", "")
    if not finnhub_key:
        logger.info("Skipping user-ticker supplement — FINNHUB_API_KEY not set")
        return

    try:
        import psycopg2
        import httpx
    except ImportError as e:
        logger.warning("Cannot run user-ticker supplement — missing dependency: %s", e)
        return

    try:
        conn = psycopg2.connect(dsn)
    except Exception as e:
        logger.warning("Could not connect to DB for user-ticker supplement: %s", e)
        return

    try:
        cur = conn.cursor()

        # Fetch pending tickers not yet added to the universe
        cur.execute(
            "SELECT DISTINCT ticker FROM user_ticker_requests WHERE added_to_universe = false"
        )
        tickers = [row[0] for row in cur.fetchall()]

        if not tickers:
            logger.info("No pending user-requested tickers")
            return

        logger.info("Supplementing %d user-requested ticker(s): %s", len(tickers), tickers)

        for ticker in tickers:
            try:
                with httpx.Client(timeout=8.0) as client:
                    profile_resp = client.get(
                        "https://finnhub.io/api/v1/stock/profile2",
                        params={"symbol": ticker},
                        headers={"X-Finnhub-Token": finnhub_key},
                    )
                    profile = profile_resp.json() if profile_resp.is_success else {}

                    quote_resp = client.get(
                        "https://finnhub.io/api/v1/quote",
                        params={"symbol": ticker},
                        headers={"X-Finnhub-Token": finnhub_key},
                    )
                    quote = quote_resp.json() if quote_resp.is_success else {}

                name = profile.get("name") or ticker
                sector = profile.get("finnhubIndustry")
                market_cap = profile.get("marketCapitalization")  # USD millions
                price = quote.get("c")  # current price
                change_pct = quote.get("dp")  # day change %
                segment = _segment_from_market_cap(market_cap)

                # Skip if Finnhub returned no useful data (unknown ticker)
                if not price and not profile.get("name"):
                    logger.warning("Finnhub returned no data for %s — skipping", ticker)
                    continue

                # Insert basic row — skip if ticker already has a full scored row
                cur.execute(
                    """
                    INSERT INTO scan_results
                        (ticker, name, segment, sector, price, change_pct, market_cap, scan_date)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, NOW()::date)
                    ON CONFLICT (ticker) DO NOTHING
                    """,
                    (
                        ticker,
                        name,
                        segment,
                        sector,
                        price,
                        change_pct,
                        (market_cap * 1_000_000) if market_cap else None,  # store in USD
                    ),
                )

                # Mark request as processed
                cur.execute(
                    "UPDATE user_ticker_requests SET added_to_universe = true WHERE ticker = %s",
                    (ticker,),
                )
                conn.commit()
                logger.info("Added user-requested ticker %s (%s, %s) to scan_results", ticker, name, segment)

            except Exception as e:
                logger.warning("Failed to supplement ticker %s: %s", ticker, e)
                try:
                    conn.rollback()
                except Exception:
                    pass

    finally:
        try:
            conn.close()
        except Exception:
            pass


def run(mode: str) -> None:
    from backend_worker.db_loader import load_scan, log_pipeline_run
    from backend_worker.r2_uploader import upload_score_snapshot

    # Start pipeline run log
    dsn = os.environ["DATABASE_URL"]
    log_pipeline_run(mode, "running", dsn=dsn)

    t0 = time.time()
    tickers_ok = tickers_err = 0
    error_msg = None

    try:
        # Import existing scoring engine
        from core.daily_pipeline import run_pipeline
        result = run_pipeline(mode)

        if result is not None and hasattr(result, "empty") and not result.empty:
            tickers_ok = load_scan(result, dsn)
            upload_score_snapshot(result)
        else:
            logger.warning("Pipeline returned no data")

    except Exception as exc:
        logger.exception("Pipeline failed")
        error_msg = str(exc)[:500]
        tickers_err = 1
        raise
    finally:
        duration = round(time.time() - t0, 1)
        status = "failed" if error_msg else "success"
        log_pipeline_run(mode, status, tickers_ok, tickers_err, duration, error_msg, dsn)
        logger.info("Pipeline %s finished in %ss", mode, duration)

    # After successful main run: add basic data for user-requested tickers
    if not error_msg:
        try:
            supplement_user_requested_tickers(dsn)
        except Exception as e:
            logger.warning("User-ticker supplement step failed (non-fatal): %s", e)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", default="morning",
                        choices=["morning", "evening", "weekly", "manual"])
    args = parser.parse_args()
    run(args.mode)
