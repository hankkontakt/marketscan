"""Smallcap scanner for Nordic small-cap stocks.
Mirrors smallcap/scanner.py from the old app.
"""
import os
import sys
import json
import logging
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "stock-scanner"))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("smallcap_scanner")


def run_smallcap_scan():
    """Run the smallcap scanning pipeline and output JSON results."""
    try:
        from smallcap.scanner import SmallCapScanner
    except ImportError as e:
        logger.error("Failed to import smallcap.scanner: %s", e)
        logger.error("Ensure stock-scanner repo is available at: %s",
                     os.path.join(os.path.dirname(__file__), "..", "stock-scanner"))
        sys.exit(1)

    scanner = SmallCapScanner()
    try:
        results = scanner.run()
    except Exception as e:
        logger.error("Smallcap scan failed: %s", e)
        sys.exit(1)

    output = []
    for r in results:
        output.append({
            "ticker": r.get("ticker"),
            "name": r.get("name"),
            "sector": r.get("sector"),
            "score_total": r.get("score_total"),
            "score_insider": r.get("score_insider"),
            "score_fcf": r.get("score_fcf"),
            "score_piotroski": r.get("score_piotroski"),
            "score_growth": r.get("score_growth"),
            "score_balance": r.get("score_balance"),
            "score_valuation": r.get("score_valuation"),
            "score_momentum": r.get("score_momentum"),
            "score_liquidity": r.get("score_liquidity"),
            "market_cap": r.get("market_cap"),
            "price": r.get("price"),
            "cash_runway_months": r.get("cash_runway_months"),
            "insider_buying": r.get("insider_buying", False),
            "entry_signal": r.get("entry_signal"),
        })

    result = {
        "results": output,
        "count": len(output),
        "timestamp": datetime.now().isoformat(),
    }
    print(json.dumps(result))
    logger.info("Smallcap scan complete: %d results", len(output))


if __name__ == "__main__":
    run_smallcap_scan()
