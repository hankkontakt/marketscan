"""Discover new stock candidates for the universe."""
import os
import sys
import json
import logging
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "stock-scanner"))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("universe_discovery")


def run_discovery():
    """Find new stock candidates from multiple sources."""
    try:
        from core.universe_discovery import UniverseDiscovery
    except ImportError as e:
        logger.error("Failed to import UniverseDiscovery: %s", e)
        logger.error("Ensure stock-scanner repo is available at: %s",
                     os.path.join(os.path.dirname(__file__), "..", "stock-scanner"))
        sys.exit(1)

    discovery = UniverseDiscovery()
    try:
        candidates = discovery.run_discovery(sources=["finviz", "news", "ai"])
    except Exception as e:
        logger.error("Universe discovery failed: %s", e)
        sys.exit(1)

    output = []
    for c in candidates:
        output.append({
            "ticker": c.get("ticker"),
            "name": c.get("name"),
            "source": c.get("source"),
            "sector": c.get("sector"),
            "market_cap": c.get("market_cap"),
            "score_total": c.get("score_total"),
        })

    result = {
        "candidates": output,
        "count": len(output),
        "timestamp": datetime.now().isoformat(),
    }
    print(json.dumps(result))
    logger.info("Discovery complete: %d candidates found", len(output))


if __name__ == "__main__":
    run_discovery()
