"""
outcome_filler.py — Fyller i realized_return_30d för prediction_outcomes
=========================================================================

Körs som ett nattligt jobb (GitHub Actions cron / manuellt).
Hittar prediktioner äldre än 30 dagar utan utfall,
hämtar nuvarande pris via Yahoo Finance (httpx, samma som prices.py),
beräknar faktisk avkastning och sparar till databasen.

Det är grunden för "AI lär sig av sina fel": ackumulerade utfall
möjliggör walk-forward-omträning på faktiska utfall.

Anrop:
    python -m backend_worker.outcome_filler
    python -m backend_worker.outcome_filler --dry-run      (inga DB-skrivningar)
    python -m backend_worker.outcome_filler --batch 50     (begränsa per körning)
"""

from __future__ import annotations

import argparse
import logging
import os
import time
from datetime import date, timedelta
from typing import Optional

import httpx
import psycopg2

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

_YAHOO_URL   = "https://query1.finance.yahoo.com/v8/finance/chart/{sym}"
_YAHOO_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; MarketScan/1.0; outcome-filler)",
    "Accept":     "application/json",
}
_REQUEST_TIMEOUT = 8.0
_RATE_LIMIT_DELAY = 0.15  # sekunder mellan Yahoo-anrop


def _fetch_price(client: httpx.Client, ticker: str) -> Optional[float]:
    """Hämtar senaste stängningskurs från Yahoo Finance (httpx, ingen yfinance)."""
    try:
        resp = client.get(
            _YAHOO_URL.format(sym=ticker),
            headers=_YAHOO_HEADERS,
            timeout=_REQUEST_TIMEOUT,
        )
        if not resp.is_success:
            return None
        data = resp.json()
        meta = data.get("chart", {}).get("result", [{}])[0].get("meta", {})
        price = meta.get("regularMarketPrice") or meta.get("previousClose")
        return float(price) if price else None
    except Exception as e:
        logger.debug("Yahoo-hämtning misslyckades för %s: %s", ticker, e)
        return None


def fill_outcomes(
    dsn: str,
    max_days_old: int = 35,
    min_days_old: int = 30,
    batch_size: int = 200,
    dry_run: bool = False,
) -> dict:
    """Hittar och fyller in utfall för prediction_outcomes.

    Args:
        dsn:          PostgreSQL DSN (DATABASE_URL).
        max_days_old: Hämta bara prediktioner yngre än X dagar (undviker jättegammal data).
        min_days_old: Prediktioner måste vara minst X dagar gamla (30d-horisont).
        batch_size:   Max antal prediktioner per körning (rate-limit skydd).
        dry_run:      Om True: hämtar priser men skriver inte till DB.

    Returns:
        Dict med filled, skipped, errors, elapsed_s.
    """
    cutoff_min = date.today() - timedelta(days=min_days_old)
    cutoff_max = date.today() - timedelta(days=max_days_old)

    t0 = time.time()
    filled = skipped = errors = 0

    try:
        conn = psycopg2.connect(dsn)
    except Exception as e:
        logger.error("DB-anslutning misslyckades: %s", e)
        return {"filled": 0, "skipped": 0, "errors": 1, "elapsed_s": 0}

    try:
        with conn.cursor() as cur:
            # Hämta pending rows: gamla nog + saknar utfall + har ett ingångspris
            cur.execute(
                """
                SELECT id, ticker, predicted_at, price_at
                FROM prediction_outcomes
                WHERE evaluated_at IS NULL
                  AND predicted_at <= %s
                  AND predicted_at >= %s
                  AND price_at IS NOT NULL
                ORDER BY predicted_at
                LIMIT %s
                """,
                (cutoff_min, cutoff_max, batch_size),
            )
            rows = cur.fetchall()

        if not rows:
            logger.info("Inga pending prediction_outcomes att fylla i")
            return {"filled": 0, "skipped": 0, "errors": 0, "elapsed_s": round(time.time() - t0, 1)}

        logger.info("Fyller i %d prediction_outcomes (dry_run=%s)...", len(rows), dry_run)

        with httpx.Client(timeout=_REQUEST_TIMEOUT) as client:
            for row_id, ticker, pred_date, price_at in rows:
                time.sleep(_RATE_LIMIT_DELAY)

                current_price = _fetch_price(client, ticker)
                if current_price is None:
                    logger.debug("Ingen kurs för %s — hoppar över", ticker)
                    skipped += 1
                    continue

                realized_return = (current_price - float(price_at)) / float(price_at)

                if not dry_run:
                    try:
                        with conn.cursor() as cur:
                            cur.execute(
                                """
                                UPDATE prediction_outcomes
                                SET realized_return_30d = %s,
                                    price_30d           = %s,
                                    evaluated_at        = %s
                                WHERE id = %s
                                """,
                                (realized_return, current_price, date.today(), row_id),
                            )
                        conn.commit()
                        filled += 1
                        logger.debug("✅ %s: %.1f%% avkastning (%.2f → %.2f)",
                                     ticker, realized_return * 100, price_at, current_price)
                    except Exception as e:
                        logger.warning("DB-uppdatering misslyckades för %s: %s", ticker, e)
                        errors += 1
                        try:
                            conn.rollback()
                        except Exception:
                            pass
                else:
                    logger.info("[DRY-RUN] %s: %.1f%% (%.2f → %.2f)",
                                ticker, realized_return * 100, price_at, current_price)
                    filled += 1

    finally:
        try:
            conn.close()
        except Exception:
            pass

    elapsed = round(time.time() - t0, 1)
    logger.info("Klar: %d fyllda, %d hoppade, %d fel (%ss)", filled, skipped, errors, elapsed)
    return {"filled": filled, "skipped": skipped, "errors": errors, "elapsed_s": elapsed}


def log_predictions(df, dsn: str) -> int:
    """Loggar ML-prediktioner från en scored DataFrame till prediction_outcomes.

    Anropas från entrypoint.py efter load_scan().
    Idempotent: ON CONFLICT DO NOTHING (säker att köra flera gånger).

    Returns:
        Antal loggade rader.
    """
    import pandas as pd

    required_cols = {"ticker", "predicted_return", "ml_rank"}
    if not required_cols.issubset(df.columns):
        logger.debug("log_predictions: saknar kolumner %s — hoppar över", required_cols - set(df.columns))
        return 0

    # Filtrera bort rader utan prediktion (ML kördes inte)
    ml_df = df.dropna(subset=["predicted_return"]).copy()
    if ml_df.empty:
        logger.info("Inga ML-prediktioner att logga (predicted_return är NaN för alla)")
        return 0

    today = date.today().isoformat()
    rows_to_insert = []

    # Dynamisk model_version: om df har attrs, använd det; annars auto
    model_version = getattr(df, "attrs", {}).get("model_version", "ranker_v1")

    for _, row in ml_df.iterrows():
        ticker = str(row.get("ticker", "")).strip()
        if not ticker:
            continue
        rows_to_insert.append((
            ticker,
            today,
            model_version,
            _safe_float(row.get("predicted_return")),
            _safe_int(row.get("ml_rank")),
            _safe_float(row.get("score_total")),
            _safe_float(row.get("price")),
        ))

    if not rows_to_insert:
        return 0

    inserted = 0
    try:
        conn = psycopg2.connect(dsn)
        with conn.cursor() as cur:
            # Batch-insert, idempotent
            for chunk_start in range(0, len(rows_to_insert), 500):
                chunk = rows_to_insert[chunk_start:chunk_start + 500]
                from psycopg2.extras import execute_values
                execute_values(
                    cur,
                    """
                    INSERT INTO prediction_outcomes
                        (ticker, predicted_at, model_version, predicted_return,
                         ml_rank, score_total, price_at)
                    VALUES %s
                    ON CONFLICT (ticker, predicted_at, model_version) DO NOTHING
                    """,
                    chunk,
                )
                inserted += cur.rowcount
        conn.commit()
        conn.close()
        logger.info("Loggade %d ML-prediktioner till prediction_outcomes", inserted)
    except Exception as e:
        logger.warning("log_predictions DB-fel (non-fatal): %s", e)
        try:
            conn.rollback()
            conn.close()
        except Exception:
            pass

    return inserted


def _safe_float(v) -> Optional[float]:
    try:
        f = float(v)
        return None if (f != f) else f  # NaN check
    except (TypeError, ValueError):
        return None


def _safe_int(v) -> Optional[int]:
    try:
        f = float(v)
        return None if (f != f) else int(round(f))
    except (TypeError, ValueError):
        return None


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fyller i realized_return_30d")
    parser.add_argument("--dry-run",   action="store_true")
    parser.add_argument("--batch",     type=int, default=200)
    parser.add_argument("--min-days",  type=int, default=30)
    parser.add_argument("--max-days",  type=int, default=365)
    args = parser.parse_args()

    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        logger.error("DATABASE_URL saknas")
        raise SystemExit(1)

    result = fill_outcomes(
        dsn,
        min_days_old=args.min_days,
        max_days_old=args.max_days,
        batch_size=args.batch,
        dry_run=args.dry_run,
    )
    print(result)
