"""
ml_trainer.py — ML-model training with retraining from realized outcomes.

Utökad version: bygger träningsdataset från prediction_outcomes + score_history
för veckovis omträning av ranker-modellen.
"""
from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

# Add stock-scanner to path for importing core modules
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

# Lägg till stock-scanner-fix sökväg
STOCK_SCANNER_PATH = REPO_ROOT.parent / "stock-scanner-fix"
if STOCK_SCANNER_PATH.exists():
    sys.path.insert(0, str(STOCK_SCANNER_PATH))

logger = logging.getLogger("ml_trainer")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


def _get_db_connection():
    """Skapa DB-anslutning via psycopg2."""
    import psycopg2
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL environment variable required")
    return psycopg2.connect(database_url)


def build_training_dataset(min_rows: int = 500, lookback_days: int = 365) -> pd.DataFrame:
    """Bygg träningsdataset från prediction_outcomes + score_history.

    Använder realiserade utfall (realized_return_30d) som target.
    Joinar mot score_history för att få features vid prediktionstillfället.
    Detta ger survivorship-säker data (avlistade bolag finns kvar).

    Returns:
        DataFrame med kolumner: date, ticker, forward_return_30d, score_*, ...
    """
    conn = _get_db_connection()

    # Hämta prediction_outcomes med realiserade utfall
    query = """
        SELECT
            po.ticker,
            po.predicted_at::date as date,
            po.predicted_return,
            po.ml_rank,
            po.score_total,
            po.price_at,
            po.realized_return_30d,
            po.price_30d
        FROM prediction_outcomes po
        WHERE po.realized_return_30d IS NOT NULL
          AND po.predicted_at >= NOW() - INTERVAL '%d days'
        ORDER BY po.predicted_at DESC
    """ % lookback_days

    outcomes = pd.read_sql(query, conn)

    # Hämta score_history för features (faktor-delscorer)
    try:
        score_hist = pd.read_sql("""
            SELECT ticker, scan_date::date as date,
                   score_value, score_quality, score_momentum, score_growth,
                   score_risk, score_size, score_dividend, score_sentiment,
                   score_total
            FROM score_history
            ORDER BY scan_date DESC
        """, conn)
        # Join outcomes med score_history på (ticker, date)
        merged = outcomes.merge(
            score_hist,
            on=["ticker", "date"],
            how="left",
            suffixes=("", "_hist"),
        )
    except Exception:
        logger.warning("score_history not available, using prediction_outcomes only")
        merged = outcomes

    conn.close()

    if merged.empty:
        logger.warning("Inga realiserade utfall funna i prediction_outcomes")
        return pd.DataFrame()

    # Rensa
    merged = merged.dropna(subset=["realized_return_30d"])
    merged = merged[merged["realized_return_30d"].between(-0.9, 5.0)]

    # Skapa forward_return_30d alias
    merged["forward_return_30d"] = merged["realized_return_30d"]

    logger.info("Byggde träningsdataset: %d rader, %d tickers",
                len(merged), merged["ticker"].nunique() if "ticker" in merged.columns else 0)
    return merged


def train_and_predict():
    """Train or retrain model and predict 30-day returns."""
    try:
        from core.daily_pipeline import load_scored_universe
        from core.ml_ranker import train_ranker, save_ranker, load_ranker, predict_ranker
    except ImportError as e:
        logger.error("Failed to import stock-scanner modules: %s", e)
        sys.exit(1)

    logger.info("Loading universe data...")
    try:
        df = load_scored_universe()
    except Exception as e:
        logger.error("Failed to load universe data: %s", e)
        sys.exit(1)

    # Försök bygga träningsdataset från realiserade utfall
    training_df = build_training_dataset()
    if len(training_df) >= 500:
        logger.info("Training on %d realized outcomes", len(training_df))
        ranker = train_ranker(None, "universe", df=training_df)
        if ranker:
            save_ranker(ranker, "universe")
            logger.info("Retrained ranker from realized outcomes, IC=%.4f",
                        ranker.test_metrics.get("ic", 0))

    # Predict using existing ranker (or fallback)
    logger.info("Loaded %d tickers. Predicting...", len(df))
    try:
        result = predict_ranker(df)
    except Exception as e:
        logger.error("ML prediction failed: %s", e)
        sys.exit(1)

    predictions = []
    for _, row in result.iterrows():
        predictions.append({
            "ticker": row.get("ticker"),
            "predicted_return": round(float(row.get("predicted_return", 0)), 4),
            "ml_rank": int(row.get("ml_rank", 999)),
            "model_version": "ranker_v2",
            "sector": row.get("sector", ""),
        })

    output = {
        "predictions": predictions,
        "model_version": "ranker_v2",
        "timestamp": datetime.now().isoformat(),
    }
    print(json.dumps(output))
    logger.info("Generated %d predictions", len(predictions))


if __name__ == "__main__":
    train_and_predict()
