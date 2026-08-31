"""
macro_fetcher.py — Riksbanken SWEA REST API & Live Yield Curve Extractor.

Hämtar officiell realtidsdata från Sveriges Riksbank (api.riksbank.se):
  - SECBREPOEFF: Reporänta (Styrränta)
  - SEGVB10YC: 10-årig statsobligation (Benchmark)
  - SEGVB5YC: 5-årig statsobligation
  - SEGVB2YC: 2-årig statsobligation
  - SETB3MBENCH: 3-månaders statsskuldväxel (Riskfri kort ränta)
  - SEKUSDPMI: USD/SEK valutakurs
  - SEKEURPMI: EUR/SEK valutakurs

Funktioner:
  1. Rate-limit guard (0.2s mikropaus mellan anrop för att undvika HTTP 429).
  2. Beräknar Yield Curve Slope (10Y - 2Y) och ränteregim.
  3. Formaterar diskonteringsräntor för DCF & Black-Litterman.
"""
from __future__ import annotations

import json
import logging
import time
import urllib.request
import urllib.error
from datetime import date, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

SWEA_BASE_URL = "https://api.riksbank.se/swea/v1/Observations"

SERIES_MAP = {
    "repo_rate": "SECBREPOEFF",
    "gov_bond_10y": "SEGVB10YC",
    "gov_bond_5y": "SEGVB5YC",
    "gov_bond_2y": "SEGVB2YC",
    "tbill_3m": "SETB3MBENCH",
    "usd_sek": "SEKUSDPMI",
    "eur_sek": "SEKEURPMI",
}


def fetch_swea_series(series_id: str, from_date: Optional[str] = None, timeout: int = 10) -> list[dict]:
    """Hämtar tidsserie från Riksbanken SWEA API."""
    if not from_date:
        from_date = (date.today() - timedelta(days=60)).isoformat()
    
    url = f"{SWEA_BASE_URL}/{series_id}/{from_date}"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "MarketScan-MacroEngine/2.0 (admin@marketscan.app)"}
    )
    
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
        data = json.loads(resp.read().decode("utf-8"))
        if isinstance(data, list):
            return data
        return []
    except urllib.error.HTTPError as e:
        logger.warning("Riksbanken SWEA HTTP %d för serie %s: %s", e.code, series_id, e)
        return []
    except Exception as e:
        logger.warning("Riksbanken SWEA fel för serie %s: %s", series_id, e)
        return []


def get_live_macro_snapshot(from_date: Optional[str] = None) -> dict:
    """Hämtar komplett live makro-snapshot med räntekurva och spridning."""
    snapshot = {
        "as_of_date": date.today().isoformat(),
        "repo_rate": None,
        "gov_bond_10y": None,
        "gov_bond_5y": None,
        "gov_bond_2y": None,
        "tbill_3m": None,
        "usd_sek": None,
        "eur_sek": None,
        "yield_curve_slope_10_2": None,
        "yield_curve_state": "NORMAL", # NORMAL, INVERTED, FLAT
        "risk_free_rate": 0.025, # Default fallback
    }

    # Hämta serier sekventiellt med mikropaus för att respektera Riksbankens rate limit
    for key, series_id in SERIES_MAP.items():
        data = fetch_swea_series(series_id, from_date=from_date)
        if data:
            latest = data[-1]
            snapshot[key] = latest.get("value")
        time.sleep(0.15) # Rate limit guard mot HTTP 429

    # Beräkna yield curve slope (10Y - 2Y)
    y10 = snapshot.get("gov_bond_10y")
    y2 = snapshot.get("gov_bond_2y")
    
    if y10 is not None and y2 is not None:
        slope = round(float(y10) - float(y2), 3)
        snapshot["yield_curve_slope_10_2"] = slope
        if slope < -0.10:
            snapshot["yield_curve_state"] = "INVERTED"
        elif abs(slope) <= 0.10:
            snapshot["yield_curve_state"] = "FLAT"
        else:
            snapshot["yield_curve_state"] = "NORMAL"
    
    # Riskfri ränta = 10y statsobligation (eller reporänta fallback)
    if y10 is not None:
        snapshot["risk_free_rate"] = round(float(y10) / 100.0, 4)
    elif snapshot.get("repo_rate") is not None:
        snapshot["risk_free_rate"] = round(float(snapshot["repo_rate"]) / 100.0, 4)

    return snapshot
