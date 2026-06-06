"""Options chain and Greeks scanner."""
import os
import sys
import json
import logging
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "stock-scanner"))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("options_scanner")


def scan_options(ticker):
    """Fetch options chain and calculate Greeks for a ticker.

    Parameters
    ----------
    ticker : str
        Stock ticker symbol.

    Returns
    -------
    list of dict
        Options contracts with price, IV, Greeks, and volume data.
    """
    try:
        from core.options_chain import OptionsChain
        from core.options_greeks import GreeksCalculator
    except ImportError as e:
        logger.error("Failed to import options modules: %s", e)
        logger.error("Ensure stock-scanner repo is available at: %s",
                     os.path.join(os.path.dirname(__file__), "..", "stock-scanner"))
        sys.exit(1)

    logger.info("Scanning options for %s...", ticker)

    chain = OptionsChain()
    try:
        options_data = chain.fetch(ticker)
    except Exception as e:
        logger.error("Failed to fetch options chain for %s: %s", ticker, e)
        sys.exit(1)

    calculator = GreeksCalculator()
    try:
        greeks = calculator.calculate(options_data)
    except Exception as e:
        logger.warning("Greeks calculation failed for some contracts: %s", e)
        greeks = {}

    output = []
    for opt in options_data:
        g = greeks.get(opt.get("id"), {})
        output.append({
            "ticker": ticker,
            "expiration": opt.get("expiration"),
            "strike": opt.get("strike"),
            "option_type": opt.get("type"),
            "last_price": opt.get("last_price"),
            "bid": opt.get("bid"),
            "ask": opt.get("ask"),
            "implied_volatility": opt.get("implied_volatility"),
            "delta": g.get("delta"),
            "gamma": g.get("gamma"),
            "theta": g.get("theta"),
            "vega": g.get("vega"),
            "open_interest": opt.get("open_interest"),
            "volume": opt.get("volume"),
        })

    result = {
        "ticker": ticker,
        "options": output,
        "count": len(output),
        "timestamp": datetime.now().isoformat(),
    }
    print(json.dumps(result))
    logger.info("Options scan for %s: %d contracts", ticker, len(output))


if __name__ == "__main__":
    ticker = sys.argv[1].upper() if len(sys.argv) > 1 else "AAPL"
    scan_options(ticker)
