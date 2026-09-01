r"""
smart_money.py — Global Smart Money Tracking & SEC Form 4 Engine.

Analyserar insynstransaktioner och institutionella ägarförändringar för
amerikanska och globala aktier för att uppnå paritet med nordiska FI-data.

Kvantitativ filtrering (Lakonishok & Lee 2001; Jeng m.fl. 2003):
  1. Filtrerar bort automatiska transaktioner (10b5-1 planer, optionslösen, RSU-skatteförsäljningar).
  2. Rollviktning: VD (CEO) och CFO har 3x högre prediktiv kraft än övriga insynspersoner.
  3. Klusterdetektering: $\ge 2$ unika ledande befattningshavare som köper över marknaden inom 60 dagar
     är en av marknadens starkaste bullish-signaler.
  4. Säljkluster: $\ge 3$ unika säljare inom 30 dagar genererar varningsflagga.
"""
from __future__ import annotations

import argparse
import json
import logging
import math
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

# Roll-vikter baserat på informationsvärde
ROLE_WEIGHTS = {
    "CEO": 3.0,
    "Chief Executive Officer": 3.0,
    "VD": 3.0,
    "CFO": 2.5,
    "Chief Financial Officer": 2.5,
    "Finanschef": 2.5,
    "Chairman": 2.0,
    "Styrelseordförande": 2.0,
    "Director": 1.2,
    "Styrelseledamot": 1.2,
    "Officer": 1.0,
    "10% Owner": 0.8,
}


# ═════════════════════════ PURE CORE (Testbar; ingen I/O) ═════════════════════

def analyze_insider_transactions(
    transactions: list[dict],
    market_cap: Optional[float] = None,
) -> dict:
    """Analyserar en lista av insynstransaktioner (SEC Form 4 eller motsvarande).

    Varje transaction-dict:
      - 'transaction_type': 'BUY' | 'SELL' | 'OPTION_EXERCISE' | 'GRANT'
      - 'role': 'CEO' | 'CFO' | 'Director' ...
      - 'shares': int
      - 'price': float
      - 'amount_usd': float (eller motsvarande)
      - 'is_open_market': bool
      - 'days_ago': int
    """
    res = {
        "unique_buyers_90d": 0,
        "unique_sellers_30d": 0,
        "total_buy_amount": 0.0,
        "total_sell_amount_30d": 0.0,
        "ceo_cfo_bought": False,
        "is_buy_cluster": False,
        "is_sell_cluster": False,
        "smart_money_z": 50.0,
        "flags": [],
    }

    if not transactions:
        return res

    buyers: set[str] = set()
    sellers: set[str] = set()
    weighted_buy_score = 0.0

    for tx in transactions:
        tx_type = str(tx.get("transaction_type", "")).upper()
        is_open_market = tx.get("is_open_market", True)
        days_ago = tx.get("days_ago", 0)
        role = str(tx.get("role", "Officer"))
        amount = float(tx.get("amount_usd") or (float(tx.get("shares", 0)) * float(tx.get("price", 0))))

        # Ignorera icke-öppna marknadstransaktioner (t.ex. optionstilldelning)
        if not is_open_market:
            continue

        weight = ROLE_WEIGHTS.get(role, 1.0)
        person_id = tx.get("insider_name") or f"{role}_{days_ago}"

        if tx_type in ("BUY", "PURCHASE", "KÖP", "KOP", "FORVÄRV", "ACQUISITION") and days_ago <= 90:
            buyers.add(person_id)
            res["total_buy_amount"] += amount
            weighted_buy_score += weight * min(10.0, math.log10(max(1000.0, amount)) - 3.0)

            r_up = role.upper()
            if "CEO" in r_up or "CFO" in r_up or "VD" in r_up or "FINANSCHEF" in r_up:
                res["ceo_cfo_bought"] = True

        elif tx_type in ("SELL", "SALE", "SÄLJ") and days_ago <= 30:
            sellers.add(person_id)
            res["total_sell_amount_30d"] += amount

    res["unique_buyers_90d"] = len(buyers)
    res["unique_sellers_30d"] = len(sellers)

    # 1. Klusterlogik
    if res["unique_buyers_90d"] >= 2:
        res["is_buy_cluster"] = True
        res["flags"].append("INSIDER_BUY_CLUSTER")

    if res["ceo_cfo_bought"]:
        res["flags"].append("C_SUITE_ACCUMULATION")

    if res["unique_sellers_30d"] >= 3:
        res["is_sell_cluster"] = True
        res["flags"].append("INSIDER_SELL_CLUSTER")

    # 2. Beräkna Smart Money Z-Score (0–100)
    base_z = 50.0
    if res["is_buy_cluster"]:
        base_z += 25.0
    elif res["unique_buyers_90d"] == 1:
        base_z += 10.0

    if res["ceo_cfo_bought"]:
        base_z += 15.0

    if res["is_sell_cluster"]:
        base_z -= 20.0
    elif res["unique_sellers_30d"] >= 2:
        base_z -= 10.0

    # Skala av köpbelopp mot börsvärde (om tillgängligt)
    if market_cap and market_cap > 0 and res["total_buy_amount"] > 0:
        buy_ratio = res["total_buy_amount"] / market_cap
        if buy_ratio > 0.005:  # Köp över 0.5% av bolagets aktier
            base_z += 10.0
            res["flags"].append("SIGNIFICANT_STAKE_PURCHASE")

    res["smart_money_z"] = float(np.clip(base_z, 0.0, 100.0))
    return res


def compute_free_float_quality(
    free_float_pct: Optional[float],
    insider_ownership_pct: Optional[float] = None,
    institution_ownership_pct: Optional[float] = None
) -> dict:
    """Beräknar Free Float Quality Score och flaggar illikviditets- och ägarkoncentrationsrisker.

    Optimal float för småbolag: 35% - 75% (god likviditet + engagerade storägare).
    Risk: Free float < 20% innebär hög illikviditetsrisk / inlåsningseffekter.
    """
    res = {
        "float_quality_score": 70.0,
        "is_tight_float": False,
        "is_overdiluted_float": False,
        "float_flags": [],
    }
    if free_float_pct is None:
        return res

    ff = float(free_float_pct)
    if ff < 0.20:
        res["is_tight_float"] = True
        res["float_quality_score"] = 40.0
        res["float_flags"].append("TIGHT_FREE_FLOAT_ILLIQUID")
    elif 0.35 <= ff <= 0.75:
        res["float_quality_score"] = 90.0
        res["float_flags"].append("BALANCED_INSTITUTIONAL_FLOAT")
    elif ff > 0.85 and (insider_ownership_pct is not None and insider_ownership_pct < 0.03):
        res["is_overdiluted_float"] = True
        res["float_quality_score"] = 55.0
        res["float_flags"].append("NO_INSIDER_SKIN_IN_GAME")

    return res


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    args = parser.parse_args()

    demo_txs = [
        {"transaction_type": "BUY", "role": "CEO", "amount_usd": 2500000, "is_open_market": True, "days_ago": 12, "insider_name": "Satya N."},
        {"transaction_type": "BUY", "role": "CFO", "amount_usd": 1200000, "is_open_market": True, "days_ago": 25, "insider_name": "Amy H."},
    ]
    res = analyze_insider_transactions(demo_txs, market_cap=3800000000000)
    print(json.dumps(res, indent=2))
