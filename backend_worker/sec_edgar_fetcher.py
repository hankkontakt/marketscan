"""
sec_edgar_fetcher.py — Officiell SEC EDGAR XBRL Fundamental-extraktor.

Hämtar 100% verifierade US-GAAP-bokslut direkt från amerikanska finansinspektionen
(data.sec.gov) för USA-noterade aktier:
  - Intäkter (Revenues / Sales)
  - Rörelseresultat (Operating Income)
  - Nettoresultat (Net Income)
  - Operativt kassaflöde & Capex
  - Fritt kassaflöde (FCF)
  - Antal utestående aktier

100% gratis och officiellt från SEC:s öppna API.
"""
from __future__ import annotations

import json
import logging
import urllib.request
import urllib.error
from typing import Optional

logger = logging.getLogger(__name__)

SEC_BASE_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
SEC_HEADERS = {
    "User-Agent": "MarketScan-FinancialAnalytics admin@marketscan.app",
    "Accept-Encoding": "gzip, deflate",
}

# Standard-mappning för vanliga CIK-nummer
KNOWN_CIKS = {
    "MU": "0000723125",
    "MSFT": "0000789019",
    "BMY": "0000014272",
    "AAPL": "0000320193",
    "NVDA": "0001045810",
    "GOOGL": "0001652044",
    "TSM": "0001046179",
}

REVENUE_TAGS = [
    "Revenues",
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "SalesRevenueNet",
    "SalesRevenueGoodsNet",
]

OP_INCOME_TAGS = [
    "OperatingIncomeLoss",
    "IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments",
]

NET_INCOME_TAGS = [
    "NetIncomeLoss",
    "ProfitLoss",
]

OP_CASHFLOW_TAGS = [
    "NetCashProvidedByUsedInOperatingActivities",
]

CAPEX_TAGS = [
    "PaymentsToAcquirePropertyPlantAndEquipment",
    "PaymentsToAcquireProductiveAssets",
]


def _extract_latest_annual(us_gaap: dict, tag_candidates: list[str]) -> Optional[dict]:
    """Extraherar det senaste 10-K-värdet ur en lista av potentiella US-GAAP-taggar."""
    for tag in tag_candidates:
        if tag in us_gaap:
            units = us_gaap[tag].get("units", {})
            usd_units = units.get("USD", [])
            # Filtrera på 10-K (helår) och sortera på slutdatum
            annual_units = [u for u in usd_units if u.get("form") == "10-K" and u.get("fy")]
            if annual_units:
                sorted_units = sorted(annual_units, key=lambda x: x.get("end", ""))
                latest = sorted_units[-1]
                return {
                    "tag_used": tag,
                    "val": latest.get("val"),
                    "val_musd": round(latest.get("val", 0) / 1_000_000, 2),
                    "fy": latest.get("fy"),
                    "period_end": latest.get("end"),
                }
    return None


def fetch_sec_company_facts(cik: str, timeout: int = 15) -> Optional[dict]:
    """Hämtar råa XBRL-fakta från SEC EDGAR."""
    import gzip
    clean_cik = str(cik).strip().zfill(10)
    url = SEC_BASE_URL.format(cik=clean_cik)
    req = urllib.request.Request(url, headers=SEC_HEADERS)
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
        content = resp.read()
        if content.startswith(b"\x1f\x8b"):
            content = gzip.decompress(content)
        return json.loads(content.decode("utf-8"))
    except urllib.error.HTTPError as e:
        logger.warning("SEC EDGAR HTTP %d för CIK %s: %s", e.code, cik, e)
        return None
    except Exception as e:
        logger.warning("SEC EDGAR fel för CIK %s: %s", cik, e)
        return None


def get_sec_financial_summary(ticker_or_cik: str) -> dict:
    """Extraherar en ren finansiell sammanställning ur SEC EDGAR."""
    cik = KNOWN_CIKS.get(ticker_or_cik.upper(), ticker_or_cik)
    raw = fetch_sec_company_facts(cik)
    if not raw:
        return {"success": False, "error": f"Ingen SEC EDGAR-data hittades för {ticker_or_cik}"}

    entity_name = raw.get("entityName", "")
    facts = raw.get("facts", {}).get("us-gaap", {})

    rev = _extract_latest_annual(facts, REVENUE_TAGS)
    op_inc = _extract_latest_annual(facts, OP_INCOME_TAGS)
    net_inc = _extract_latest_annual(facts, NET_INCOME_TAGS)
    op_cf = _extract_latest_annual(facts, OP_CASHFLOW_TAGS)
    capex = _extract_latest_annual(facts, CAPEX_TAGS)

    fcf_musd = None
    if op_cf and capex:
        fcf_musd = round(op_cf["val_musd"] - capex["val_musd"], 2)

    return {
        "success": True,
        "ticker_or_cik": ticker_or_cik,
        "company_name": entity_name,
        "fiscal_year": rev.get("fy") if rev else None,
        "period_end": rev.get("period_end") if rev else None,
        "revenue_musd": rev.get("val_musd") if rev else None,
        "operating_income_musd": op_inc.get("val_musd") if op_inc else None,
        "net_income_musd": net_inc.get("val_musd") if net_inc else None,
        "operating_cash_flow_musd": op_cf.get("val_musd") if op_cf else None,
        "capex_musd": capex.get("val_musd") if capex else None,
        "free_cash_flow_musd": fcf_musd,
    }
