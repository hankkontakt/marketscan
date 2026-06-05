"""
READ-ONLY DuckDB queries against Cloudflare R2.
Used ONLY for historical/cold data — never on the hot screener path.
Cold start ~2s: acceptable for history/backtest views.
"""
import duckdb
from apps.api.core.config import settings


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


def query_score_history(ticker: str, limit: int = 52) -> list[dict]:
    """Return weekly score snapshots for a ticker (for Betygstrend chart)."""
    con = _init_con()
    try:
        rows = con.execute(f"""
            SELECT scan_date, score_total, entry_signal
            FROM read_parquet('s3://{settings.R2_BUCKET}/history/scored_*.parquet')
            WHERE ticker = ?
            ORDER BY scan_date DESC
            LIMIT ?
        """, [ticker, limit]).fetchall()
        return [{"date": str(r[0]), "score": r[1], "signal": r[2]} for r in rows]
    finally:
        con.close()


def query_price_history(ticker: str) -> list[dict]:
    """Return OHLCV data for TradingView Lightweight Charts."""
    safe_ticker = ticker.replace("/", "_")
    con = _init_con()
    try:
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
    finally:
        con.close()


def list_score_snapshots() -> list[str]:
    con = _init_con()
    try:
        rows = con.execute(f"""
            SELECT DISTINCT scan_date
            FROM read_parquet('s3://{settings.R2_BUCKET}/history/scored_*.parquet')
            ORDER BY scan_date DESC
            LIMIT 100
        """).fetchall()
        return [str(r[0]) for r in rows]
    finally:
        con.close()
