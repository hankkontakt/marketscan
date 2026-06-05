"""
Uploads Parquet snapshots to Cloudflare R2.
Cold data: score history, OHLC price history, backtest snapshots.
"""
import io
import os
import logging
from datetime import date
import boto3
import pandas as pd

logger = logging.getLogger(__name__)


def _s3_client():
    return boto3.client(
        "s3",
        endpoint_url=os.environ["R2_ENDPOINT"],
        aws_access_key_id=os.environ["R2_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET"],
        region_name="auto",
    )


BUCKET = os.environ.get("R2_BUCKET", "marketscan-data")


def upload_score_snapshot(df: pd.DataFrame, run_date: date | None = None) -> str:
    """
    Upload today's scored results as Parquet to R2.
    Key: history/scored_{YYYY-MM-DD}.parquet
    """
    run_date = run_date or date.today()
    key = f"history/scored_{run_date.isoformat()}.parquet"

    buf = io.BytesIO()
    df.to_parquet(buf, index=False, engine="pyarrow", compression="snappy")
    buf.seek(0)

    _s3_client().put_object(Bucket=BUCKET, Key=key, Body=buf.getvalue())
    logger.info("Uploaded %s (%d rows)", key, len(df))
    return key


def upload_price_history(ticker: str, df: pd.DataFrame) -> str:
    """
    Upload OHLC price history for a ticker.
    Key: prices/{ticker}.parquet
    """
    key = f"prices/{ticker.replace('/', '_')}.parquet"
    buf = io.BytesIO()
    df.to_parquet(buf, index=False, engine="pyarrow", compression="snappy")
    buf.seek(0)
    _s3_client().put_object(Bucket=BUCKET, Key=key, Body=buf.getvalue())
    return key


def upload_backtest_snapshot(name: str, df: pd.DataFrame) -> str:
    key = f"backtest/{name}.parquet"
    buf = io.BytesIO()
    df.to_parquet(buf, index=False, engine="pyarrow", compression="snappy")
    buf.seek(0)
    _s3_client().put_object(Bucket=BUCKET, Key=key, Body=buf.getvalue())
    return key


def list_score_snapshots() -> list[str]:
    s3 = _s3_client()
    resp = s3.list_objects_v2(Bucket=BUCKET, Prefix="history/scored_")
    return sorted(o["Key"] for o in resp.get("Contents", []))
