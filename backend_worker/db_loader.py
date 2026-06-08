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
    "large_cap":  10_000_000_000,   # USD
    "mid_cap":    2_000_000_000,    # USD
    "small_cap":  300_000_000,      # USD
}

# Static FX rates → USD.  Updated 2026-06; refresh periodically.
# Used to normalise market_cap values before applying USD thresholds.
_FX_TO_USD: dict[str, float] = {
    "USD": 1.0,
    "SEK": 0.093,   # 1 SEK ≈ 0.093 USD
    "EUR": 1.08,
    "GBP": 1.27,
    "NOK": 0.092,
    "DKK": 0.145,
    "CHF": 1.12,
    "CAD": 0.74,
    "AUD": 0.65,
    "JPY": 0.0066,
}


def _to_usd(market_cap: float | None, currency: str | None) -> float | None:
    """Return market_cap in USD. Falls back to 1:1 if currency is unknown."""
    if market_cap is None or market_cap <= 0:
        return market_cap
    rate = _FX_TO_USD.get((currency or "USD").upper(), 1.0)
    return market_cap * rate


def _derive_segment(market_cap_usd: float | None) -> str:
    """Map USD market cap to segment string."""
    if market_cap_usd is None or market_cap_usd <= 0:
        return "micro_cap"
    if market_cap_usd >= SEGMENT_THRESHOLDS["large_cap"]:
        return "large_cap"
    if market_cap_usd >= SEGMENT_THRESHOLDS["mid_cap"]:
        return "mid_cap"
    if market_cap_usd >= SEGMENT_THRESHOLDS["small_cap"]:
        return "small_cap"
    return "micro_cap"


def _prepare_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["scan_date"] = date.today().isoformat()

    if "segment" not in df.columns:
        # Normalise market_cap to USD before applying thresholds — parquet stores
        # Swedish stocks in SEK, US stocks in USD, etc.  Without this almost all
        # SEK-denominated companies end up classified as large_cap.
        currency_col = df.get("currency", pd.Series(dtype=str))
        df["segment"] = [
            _derive_segment(_to_usd(mc, cur))
            for mc, cur in zip(
                df.get("market_cap", pd.Series(dtype=float)),
                currency_col,
            )
        ]

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
    prepared.to_csv(buf, index=False, header=False, na_rep="", encoding="utf-8")
    buf.seek(0)

    with psycopg2.connect(dsn, client_encoding="UTF8") as con:
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
