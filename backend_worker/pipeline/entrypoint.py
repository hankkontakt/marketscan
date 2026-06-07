"""
GitHub Actions entrypoint — bridges existing core/ logic to new storage.
Imports from stock-scanner/core/ via PYTHONPATH.
Run: python -m marketscan.backend_worker.pipeline.entrypoint --mode morning

Design: for morning/evening/manual we run a FAST path that skips the
slow steps (news fetching for 767 stocks, DeepSeek AI, SMTP email) that
cause the pipeline to hang indefinitely. We load the existing parquet,
update today's prices, run ML predictions, and load into Supabase.

For weekly/smallcap we still call the full run_pipeline() (it does a
real fundamentals refresh) but with a 75-minute SIGALRM hard timeout.
"""
import sys
import time
import logging
import argparse
import os
import signal
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Fast pipeline (morning / evening / manual)
# ---------------------------------------------------------------------------

def _fast_pipeline(report_dir: Path):
    """
    Fast path for morning/evening/manual modes.

    Steps:
      1. Load latest scored parquet (or CSV) from stock-scanner/reports/
      2. Update today's prices via yfinance batch  (~10 seconds)
      3. Run ML predictions (XGBoost)              (~1 second)
      4. Save updated parquet
      5. Return the DataFrame for DB loading

    This deliberately skips: news fetching, AI analysis, email — all of
    which block indefinitely and are not needed to populate scan_results.
    """
    import pandas as pd
    from datetime import date

    # 1. Load latest parquet
    parquet_files = sorted(report_dir.glob("scored_universe_*.parquet"), reverse=True)
    csv_files     = sorted(report_dir.glob("scored_universe_*.csv"),     reverse=True)

    if not parquet_files and not csv_files:
        logger.error("No scored_universe file found in %s — cannot run fast pipeline", report_dir)
        return None

    if parquet_files:
        df = pd.read_parquet(parquet_files[0])
        logger.info("Loaded %d rows from %s", len(df), parquet_files[0].name)
    else:
        df = pd.read_csv(csv_files[0])
        logger.info("Loaded %d rows from %s (CSV)", len(df), csv_files[0].name)

    if df.empty:
        logger.error("Loaded file is empty")
        return None

    # 2. Update prices
    try:
        from core.data_fetcher import fetch_prices_only, update_scored_with_prices
        tickers = [
            t for t in df["ticker"].dropna().unique().tolist()
            if not str(t).startswith("^")
        ][:300]
        logger.info("Fetching prices for %d tickers...", len(tickers))
        price_data = fetch_prices_only(tickers, period="6mo", max_workers=12)
        if price_data:
            df = update_scored_with_prices(df, price_data)
            logger.info("Prices updated for %d tickers", len(price_data))
        else:
            logger.warning("fetch_prices_only returned empty — using yesterday's prices")
    except Exception as exc:
        logger.warning("Price update failed (using stale prices): %s", exc)

    # 3. ML predictions
    try:
        from core.ml_predictor import predict_returns_sector
        df_ml = predict_returns_sector(df, default_universe="universe")
        if "predicted_return" in df_ml.columns:
            df = df_ml
            logger.info("ML predictions added for %d rows", len(df))
    except Exception as exc:
        logger.warning("ML predictions skipped: %s", exc)

    # 4. Save updated parquet
    try:
        today_str = date.today().strftime("%Y-%m-%d")
        out_pq  = report_dir / f"scored_universe_{today_str}.parquet"
        out_csv = report_dir / f"scored_universe_{today_str}.csv"
        df.to_parquet(out_pq, index=False)
        df.to_csv(out_csv, index=False)
        logger.info("Saved %s + .csv", out_pq.name)
    except Exception as exc:
        logger.warning("Could not save parquet/csv: %s", exc)

    return df


# ---------------------------------------------------------------------------
# Full pipeline with hard timeout (weekly / smallcap)
# ---------------------------------------------------------------------------

def _full_pipeline_with_timeout(mode: str, report_dir: Path, timeout_seconds: int = 75 * 60):
    """
    Run the full run_pipeline() (real fundamentals refresh) with a SIGALRM
    hard timeout. On timeout we fall back to reading the latest parquet from
    disk (which was saved by run_pipeline before it reached the slow steps).
    """
    import pandas as pd

    def _alarm_handler(signum, frame):
        raise RuntimeError("pipeline_sigalrm_timeout")

    has_alarm = hasattr(signal, "SIGALRM")
    if has_alarm:
        signal.signal(signal.SIGALRM, _alarm_handler)
        signal.alarm(timeout_seconds)
        logger.info("SIGALRM set: %d-minute hard timeout on run_pipeline()", timeout_seconds // 60)

    try:
        from core.daily_pipeline import run_pipeline
        result = run_pipeline(mode)
        logger.info("run_pipeline('%s') returned normally", mode)
    except RuntimeError as exc:
        if "pipeline_sigalrm_timeout" in str(exc):
            logger.warning(
                "run_pipeline('%s') timed out after %d min — reading saved parquet from disk",
                mode, timeout_seconds // 60,
            )
            result = None
        else:
            raise
    finally:
        if has_alarm:
            signal.alarm(0)

    # run_pipeline returns None — read parquet it saved during the run
    if result is None or not (hasattr(result, "empty") and not result.empty):
        parquet_files = sorted(report_dir.glob("scored_universe_*.parquet"), reverse=True)
        csv_files     = sorted(report_dir.glob("scored_universe_*.csv"),     reverse=True)
        if parquet_files:
            result = pd.read_parquet(parquet_files[0])
            logger.info("Loaded %d rows from %s (post-run disk read)", len(result), parquet_files[0].name)
        elif csv_files:
            result = pd.read_csv(csv_files[0])
            logger.info("Loaded %d rows from %s (CSV fallback)", len(result), csv_files[0].name)

    return result if (result is not None and hasattr(result, "empty") and not result.empty) else None


# ---------------------------------------------------------------------------
# User-requested ticker supplement
# ---------------------------------------------------------------------------

def supplement_user_requested_tickers(dsn: str) -> None:
    """After the main pipeline, add basic Finnhub data for user-requested tickers."""
    finnhub_key = os.environ.get("FINNHUB_API_KEY", "")
    if not finnhub_key:
        logger.info("Skipping user-ticker supplement — FINNHUB_API_KEY not set")
        return

    try:
        import psycopg2
        import httpx
    except ImportError as exc:
        logger.warning("Cannot run user-ticker supplement — missing dependency: %s", exc)
        return

    try:
        conn = psycopg2.connect(dsn)
    except Exception as exc:
        logger.warning("Could not connect to DB for user-ticker supplement: %s", exc)
        return

    try:
        cur = conn.cursor()
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

                name       = profile.get("name") or ticker
                sector     = profile.get("finnhubIndustry")
                market_cap = profile.get("marketCapitalization")
                price      = quote.get("c")
                change_pct = quote.get("dp")
                segment    = _segment_from_market_cap(market_cap)

                if not price and not profile.get("name"):
                    logger.warning("Finnhub returned no data for %s — skipping", ticker)
                    continue

                cur.execute(
                    """
                    INSERT INTO scan_results
                        (ticker, name, segment, sector, price, change_pct, market_cap, scan_date)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, NOW()::date)
                    ON CONFLICT (ticker) DO NOTHING
                    """,
                    (
                        ticker, name, segment, sector, price, change_pct,
                        (market_cap * 1_000_000) if market_cap else None,
                    ),
                )
                cur.execute(
                    "UPDATE user_ticker_requests SET added_to_universe = true WHERE ticker = %s",
                    (ticker,),
                )
                conn.commit()
                logger.info("Added user-requested ticker %s (%s, %s)", ticker, name, segment)

            except Exception as exc:
                logger.warning("Failed to supplement ticker %s: %s", ticker, exc)
                try:
                    conn.rollback()
                except Exception:
                    pass
    finally:
        try:
            conn.close()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run(mode: str) -> None:
    from backend_worker.db_loader import load_scan, log_pipeline_run
    from backend_worker.r2_uploader import upload_score_snapshot

    dsn = os.environ["DATABASE_URL"]
    log_pipeline_run(mode, "running", dsn=dsn)

    t0 = time.time()
    tickers_ok = tickers_err = 0
    error_msg  = None

    try:
        import core as _core_pkg
        report_dir = Path(_core_pkg.__file__).parent.parent / "reports"

        if mode in ("morning", "evening", "manual"):
            # Fast path: prices + ML only, no news/AI/email
            result = _fast_pipeline(report_dir)
        else:
            # weekly / smallcap: full pipeline with hard timeout
            result = _full_pipeline_with_timeout(mode, report_dir, timeout_seconds=75 * 60)

        if result is not None and not result.empty:
            tickers_ok = load_scan(result, dsn)
            upload_score_snapshot(result)
        else:
            logger.warning("No scored data to load into scan_results")

    except Exception as exc:
        logger.exception("Pipeline failed")
        error_msg  = str(exc)[:500]
        tickers_err = 1
        raise
    finally:
        duration = round(time.time() - t0, 1)
        status   = "failed" if error_msg else "success"
        log_pipeline_run(mode, status, tickers_ok, tickers_err, duration, error_msg, dsn)
        logger.info("Pipeline %s finished in %ss", mode, duration)

    if not error_msg:
        try:
            supplement_user_requested_tickers(dsn)
        except Exception as exc:
            logger.warning("User-ticker supplement failed (non-fatal): %s", exc)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", default="morning",
                        choices=["morning", "evening", "weekly", "manual", "smallcap"])
    args = parser.parse_args()
    run(args.mode)
