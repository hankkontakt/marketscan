"""ML model training and prediction using XGBoost.
Mirrors core/ml_predictor.py from the old stock-scanner app.
"""
import os
import sys
import json
import logging
import numpy as np
from datetime import datetime, timedelta

# Add stock-scanner to path for importing core modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "stock-scanner"))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ml_trainer")


def train_and_predict():
    """Train XGBoost model on scan data and predict 30-day returns."""
    try:
        from core.daily_pipeline import load_scored_universe
        from core.ml_predictor import MLPredictor
    except ImportError as e:
        logger.error("Failed to import stock-scanner modules: %s", e)
        logger.error("Ensure stock-scanner repo is available at: %s",
                     os.path.join(os.path.dirname(__file__), "..", "stock-scanner"))
        sys.exit(1)

    logger.info("Loading universe data...")
    try:
        df = load_scored_universe()
    except Exception as e:
        logger.error("Failed to load universe data: %s", e)
        sys.exit(1)

    logger.info("Loaded %d tickers. Training model...", len(df))
    predictor = MLPredictor()
    try:
        result = predictor.predict(df)
    except Exception as e:
        logger.error("ML prediction failed: %s", e)
        sys.exit(1)

    predictions = []
    for _, row in result.iterrows():
        predictions.append({
            "ticker": row.get("ticker"),
            "predicted_return": round(float(row.get("predicted_return", 0)), 4),
            "ml_rank": int(row.get("ml_rank", 999)),
            "model_version": predictor.model_version,
            "sector": row.get("sector", ""),
        })

    # Write to stdout as JSON for GitHub Actions to capture
    output = {
        "predictions": predictions,
        "model_version": predictor.model_version,
        "timestamp": datetime.now().isoformat(),
    }
    print(json.dumps(output))
    logger.info("Generated %d predictions", len(predictions))


if __name__ == "__main__":
    train_and_predict()
