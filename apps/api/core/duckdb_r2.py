"""
READ-ONLY DuckDB queries against Cloudflare R2.
Used ONLY for historical/cold data — never on the hot screener path.
Cold start ~2s: acceptable for history/backtest views.
"""
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
import duckdb
from apps.api.core.config import settings

logger = logging.getLogger(__name__)

_duckdb_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="duckdb")
_con: duckdb.DuckDBPyConnection | None = None


def _init_con() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect(":memory:")
    con.execute("INSTALL httpfs; LOAD httpfs;")
    con.execute(f"""
        CREATE SECRET r2 (
          TYPE S3,
          KEY_ID '{settings.R2_KEY_ID}',
          SECRET '{settings.R2_SECRET}',
          ENDPOINT '{settings.R2_ENDPOINT}',
          URL_STYLE 'path',
          REGION 'auto'
        );
    """)
    con.execute("SET max_memory='768MB';")
    con.execute("SET threads=2;")
    return con


def _get_con() -> duckdb.DuckDBPyConnection:
    global _con
    if _con is None:
        logger.info("Initializing DuckDB connection (cold start ~2s)")
        _con = _init_con()
    return _con


def _query_score_history(ticker: str, limit: int = 52) -> list[dict]:
    """Synchronous DuckDB query for score history."""
    con = _get_con()
    rows = con.execute(f"""
        SELECT scan_date, score_total, entry_signal
        FROM read_parquet('s3://{settings.R2_BUCKET}/history/scored_*.parquet')
        WHERE ticker = ?
        ORDER BY scan_date DESC
        LIMIT ?
    """, [ticker, limit]).fetchall()
    return [{"date": str(r[0]), "score": r[1], "signal": r[2]} for r in rows]


def _query_price_history(ticker: str) -> list[dict]:
    """Synchronous DuckDB query for price history."""
    safe_ticker = ticker.replace("/", "_")
    con = _get_con()
    rows = con.execute(f"""
        SELECT date, open, high, low, close, volume
        FROM read_parquet('s3://{settings.R2_BUCKET}/prices/{safe_ticker}.parquet')
        ORDER BY date
    """).fetchall()
    return [
        {"time": str(r[0]), "open": r[1], "high": r[2],
         "low": r[3], "close": r[4], "volume": r[5]}
        for r in rows
    ]


def _list_score_snapshots() -> list[str]:
    con = _get_con()
    rows = con.execute(f"""
        SELECT DISTINCT scan_date
        FROM read_parquet('s3://{settings.R2_BUCKET}/history/scored_*.parquet')
        ORDER BY scan_date DESC
        LIMIT 100
    """).fetchall()
    return [str(r[0]) for r in rows]


async def query_score_history(ticker: str, limit: int = 52) -> list[dict]:
    """Return weekly score snapshots for a ticker (async, non-blocking)."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(_duckdb_executor, _query_score_history, ticker, limit)


async def query_price_history(ticker: str) -> list[dict]:
    """Return OHLCV data (async, non-blocking)."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(_duckdb_executor, _query_price_history, ticker)


async def list_score_snapshots() -> list[str]:
    """List available score snapshot dates (async, non-blocking)."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(_duckdb_executor, _list_score_snapshots)
