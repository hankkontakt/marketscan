"""
Uploads Parquet snapshots to Cloudflare R2.
Cold data: score history, OHLC price history, backtest snapshots.

R2 is optional — all functions return early (with a warning) when
R2_ENDPOINT / R2_KEY_ID / R2_SECRET are not configured. This keeps the
pipeline non-fatal when R2 credentials haven't been set yet.
"""
import io
import os
import logging
from datetime import date
import boto3
import pandas as pd

logger = logging.getLogger(__name__)

BUCKET = os.environ.get("R2_BUCKET", "marketscan-data")


def _r2_configured() -> bool:
    """Return True only when all three required R2 env vars are non-empty."""
    return all(
        os.environ.get(k, "").strip()
        for k in ("R2_ENDPOINT", "R2_KEY_ID", "R2_SECRET")
    )


def _s3_client():
    return boto3.client(
        "s3",
        endpoint_url=os.environ["R2_ENDPOINT"],
        aws_access_key_id=os.environ["R2_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET"],
        region_name="auto",
    )


def upload_score_snapshot(df: pd.DataFrame, run_date: date | None = None) -> str | None:
    """
    Upload today's scored results as Parquet to R2.
    Key: history/scored_{YYYY-MM-DD}.parquet
    Returns the key, or None when R2 is not configured.
    """
    if not _r2_configured():
        logger.info("R2 not configured — skipping score snapshot upload")
        return None

    run_date = run_date or date.today()
    key = f"history/scored_{run_date.isoformat()}.parquet"

    buf = io.BytesIO()
    df.to_parquet(buf, index=False, engine="pyarrow", compression="snappy")
    buf.seek(0)

    _s3_client().put_object(Bucket=BUCKET, Key=key, Body=buf.getvalue())
    logger.info("Uploaded %s (%d rows)", key, len(df))
    return key


def upload_price_history(ticker: str, df: pd.DataFrame) -> str | None:
    """
    Upload OHLC price history for a ticker.
    Key: prices/{ticker}.parquet
    Returns the key, or None when R2 is not configured.
    """
    if not _r2_configured():
        logger.info("R2 not configured — skipping price history upload for %s", ticker)
        return None

    key = f"prices/{ticker.replace('/', '_')}.parquet"
    buf = io.BytesIO()
    df.to_parquet(buf, index=False, engine="pyarrow", compression="snappy")
    buf.seek(0)
    _s3_client().put_object(Bucket=BUCKET, Key=key, Body=buf.getvalue())
    return key


def upload_backtest_snapshot(name: str, df: pd.DataFrame) -> str | None:
    """Returns the key, or None when R2 is not configured."""
    if not _r2_configured():
        logger.info("R2 not configured — skipping backtest snapshot upload")
        return None

    key = f"backtest/{name}.parquet"
    buf = io.BytesIO()
    df.to_parquet(buf, index=False, engine="pyarrow", compression="snappy")
    buf.seek(0)
    _s3_client().put_object(Bucket=BUCKET, Key=key, Body=buf.getvalue())
    return key


def list_score_snapshots() -> list[str]:
    if not _r2_configured():
        logger.info("R2 not configured — returning empty snapshot list")
        return []

    s3 = _s3_client()
    resp = s3.list_objects_v2(Bucket=BUCKET, Prefix="history/scored_")
    return sorted(o["Key"] for o in resp.get("Contents", []))
