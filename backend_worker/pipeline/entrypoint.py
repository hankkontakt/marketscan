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


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", default="morning",
                        choices=["morning", "evening", "weekly", "manual"])
    args = parser.parse_args()
    run(args.mode)
