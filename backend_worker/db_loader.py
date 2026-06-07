"""
Bulk-loads scored scan results into Supabase Postgres via COPY.
Uses copy_expert() (51s → 13s vs to_sql on 1200-row scans).
"""
import io
import os
import logging
import psycopg2
import pandas as pd
from datetime import date

logger = logging.getLogger(__name__)

SCAN_COLUMNS = [
    "ticker", "name", "segment", "sector", "country",
    "score_total", "score_value", "score_quality", "score_momentum",
    "score_growth", "score_risk", "score_size", "score_dividend", "score_sentiment",
    "entry_signal", "confidence_label", "trend_signal",
    "predicted_return", "ml_rank", "piotroski_f",
    "price", "change_pct", "market_cap", "pe_trailing", "pe_forward",
    "roe", "roa", "revenue_growth", "earnings_growth",
    "debt_to_equity", "current_ratio", "gross_margin", "operating_margin",
    "dividend_yield", "beta", "vol_20d",
    "low_liquidity", "has_holding", "scan_date",
]

SEGMENT_THRESHOLDS = {
    "large_cap":  10_000_000_000,
    "mid_cap":    2_000_000_000,
    "small_cap":  300_000_000,
}


def _derive_segment(market_cap: float | None) -> str:
    if market_cap is None or market_cap <= 0:
        return "micro_cap"
    if market_cap >= SEGMENT_THRESHOLDS["large_cap"]:
        return "large_cap"
    if market_cap >= SEGMENT_THRESHOLDS["mid_cap"]:
        return "mid_cap"
    if market_cap >= SEGMENT_THRESHOLDS["small_cap"]:
        return "small_cap"
    return "micro_cap"


def _prepare_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["scan_date"] = date.today().isoformat()

    if "segment" not in df.columns:
        df["segment"] = df.get("market_cap", pd.Series(dtype=float)).map(_derive_segment)

    if "has_holding" not in df.columns:
        df["has_holding"] = False

    # Clamp scores to [0, 100]
    for col in [c for c in df.columns if c.startswith("score_")]:
        df[col] = df[col].clip(0, 100)

    # Cast integer columns — parquet stores these as float (e.g. 12.8 → 13)
    # Postgres INTEGER columns reject non-integer strings from COPY.
    for int_col in ("ml_rank", "piotroski_f"):
        if int_col in df.columns:
            df[int_col] = (
                pd.to_numeric(df[int_col], errors="coerce")
                .round()
                .astype("Int64")   # nullable int — NaN stays NULL, not "nan"
            )

    # Map legacy entry_signal strings — must match CHECK constraint values
    signal_map = {
        "STARK": "STARK", "OK": "OK",
        "VÄNTA": "VÄNTA", "EJ AKTUELL": "EJ_AKTUELL",
        "EJ_AKTUELL": "EJ_AKTUELL",
    }
    if "entry_signal" in df.columns:
        df["entry_signal"] = df["entry_signal"].map(signal_map).fillna("EJ_AKTUELL")

    # P1-2: Normalize confidence_label — raw pipeline uses caps Swedish ('HÖG', 'MEDEL', 'LÅG')
    # CHECK constraint requires title-case ('Hög', 'Medel', 'Låg')
    confidence_map = {
        "HÖG": "Hög", "MEDEL": "Medel", "LÅG": "Låg",
        "Hög": "Hög", "Medel": "Medel", "Låg": "Låg",
    }
    if "confidence_label" in df.columns:
        df["confidence_label"] = df["confidence_label"].map(confidence_map)
        # NULL is allowed — leave unknown values as None (NaN)

    # P1-2: Normalize trend_signal — raw pipeline uses 'UPPTREND', 'NEDTREND', 'VARNING', 'SIDLED'
    # CHECK constraint requires 'Upptrend', 'Nedtrend', 'Sidled'; VARNING has no valid mapping → NULL
    trend_map = {
        "UPPTREND": "Upptrend", "NEDTREND": "Nedtrend",
        "SIDLED": "Sidled",
        "Upptrend": "Upptrend", "Nedtrend": "Nedtrend", "Sidled": "Sidled",
        "VARNING": None,  # No valid CHECK value — store as NULL
    }
    if "trend_signal" in df.columns:
        df["trend_signal"] = df["trend_signal"].map(trend_map)
        # Values not in map become NaN → NULL in Postgres (allowed by schema)

    # Keep only known columns; add missing ones as NULL
    for col in SCAN_COLUMNS:
        if col not in df.columns:
            df[col] = None

    return df[SCAN_COLUMNS]


def load_scan(df: pd.DataFrame, dsn: str | None = None) -> int:
    """
    Replace scan_results table with new data. Returns row count.
    dsn defaults to DATABASE_URL env var.
    """
    dsn = dsn or os.environ["DATABASE_URL"]
    prepared = _prepare_df(df)

    buf = io.StringIO()
    prepared.to_csv(buf, index=False, header=False, na_rep="")
    buf.seek(0)

    with psycopg2.connect(dsn) as con:
        con.autocommit = False
        with con.cursor() as cur:
            cur.execute("TRUNCATE scan_results;")
            cur.copy_expert(
                f"COPY scan_results ({','.join(SCAN_COLUMNS)}) FROM STDIN WITH (FORMAT csv, NULL '')",
                buf,
            )
        con.commit()
        with con.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM scan_results;")
            n = cur.fetchone()[0]

    logger.info("scan_results loaded: %d rows", n)
    return n


def log_pipeline_run(
    run_type: str,
    status: str,
    tickers_ok: int = 0,
    tickers_err: int = 0,
    duration_s: float = 0,
    error_msg: str | None = None,
    dsn: str | None = None,
) -> None:
    dsn = dsn or os.environ["DATABASE_URL"]
    with psycopg2.connect(dsn) as con, con.cursor() as cur:
        cur.execute(
            """
            UPDATE pipeline_runs SET status=%s, tickers_ok=%s, tickers_err=%s,
              duration_s=%s, error_msg=%s, finished_at=NOW()
            WHERE run_type=%s AND status='running'
              AND started_at = (
                SELECT MAX(started_at) FROM pipeline_runs WHERE run_type=%s AND status='running'
              )
            """,
            (status, tickers_ok, tickers_err, duration_s, error_msg, run_type, run_type),
        )
        if cur.rowcount == 0:
            cur.execute(
                """INSERT INTO pipeline_runs (run_type, status, tickers_ok, tickers_err,
                     duration_s, error_msg, finished_at)
                   VALUES (%s,%s,%s,%s,%s,%s,NOW())""",
                (run_type, status, tickers_ok, tickers_err, duration_s, error_msg),
            )
        con.commit()
