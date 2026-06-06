"""Sector rotation analysis using momentum and score data."""
import os
import sys
import json
import logging
from datetime import datetime
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "stock-scanner"))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sector_rotation")


def run_sector_rotation():
    """Calculate sector momentum and strength rankings."""
    try:
        from core.daily_pipeline import load_scored_universe
        from core.sector_momentum import SectorMomentum
    except ImportError as e:
        logger.error("Failed to import core modules: %s", e)
        logger.error("Ensure stock-scanner repo is available at: %s",
                     os.path.join(os.path.dirname(__file__), "..", "stock-scanner"))
        sys.exit(1)

    logger.info("Loading universe...")
    try:
        df = load_scored_universe()
    except Exception as e:
        logger.error("Failed to load universe data: %s", e)
        sys.exit(1)

    if df is None or df.empty:
        logger.warning("Universe data is empty — no sectors to analyze.")
        print(json.dumps({"sectors": [], "timestamp": datetime.now().isoformat()}))
        return

    engine = SectorMomentum()
    try:
        rotation = engine.calculate(df)
    except Exception as e:
        logger.error("Sector rotation calculation failed: %s", e)
        sys.exit(1)

    output = []
    for sector_data in rotation:
        output.append({
            "sector": sector_data["sector"],
            "momentum_rank": sector_data.get("rank"),
            "strength_score": sector_data.get("strength_score"),
            "trend_direction": sector_data.get("trend", "neutral"),
            "avg_score": sector_data.get("avg_score"),
            "top_tickers": sector_data.get("top_tickers", [])[:5],
        })

    print(json.dumps({
        "sectors": output,
        "timestamp": datetime.now().isoformat(),
    }))
    logger.info("Sector rotation: %d sectors analyzed", len(output))


if __name__ == "__main__":
    run_sector_rotation()
