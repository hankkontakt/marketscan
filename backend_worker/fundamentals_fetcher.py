"""
fundamentals_fetcher.py — Kvantitativ Fundamental- & Forensikmotor.

Hämtar och beräknar djupa balansräknings- och kassaflödesmått gratis via
kvartalsdata (yfinance quarterly_cashflow, quarterly_balance_sheet, quarterly_income_stmt):
  1. Fritt kassaflöde (FCF) & Operativt kassaflöde (OCF) TTM
  2. Sloan Accrual Anomaly: (Net Income - OCF) / Total Assets
  3. Cash Runway: Månader av likviditet kvar vid negativt kassaflöde
  4. Utspädningstakt (YoY % förändring i antal utestående aktier)
  5. Nettoskuld / EBITDA & Soliditet
  6. Bruttomarginaltrend (senaste 4 kvartalen)

Skriver till lokal cache i data/fundamentals_raw/ samt kan anropas av master_rank.py.
"""
from __future__ import annotations

import argparse
import json
import logging
import math
from datetime import date
from pathlib import Path
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

CACHE_DIR = Path(__file__).resolve().parent.parent / "data" / "fundamentals_raw"
CACHE_MAX_AGE_DAYS = 7


def _cache_path(ticker: str) -> Path:
    safe = ticker.replace("/", "_").replace(":", "_")
    return CACHE_DIR / f"{safe}.json"


# ═════════════════════════ PURE CORE (Testbar; ingen I/O) ═════════════════════

def _safe_float(val) -> Optional[float]:
    if val is None:
        return None
    try:
        f = float(val)
        return f if math.isfinite(f) else None
    except (TypeError, ValueError):
        return None


def extract_fundamentals(
    cf_df: Optional[pd.DataFrame],
    bs_df: Optional[pd.DataFrame],
    inc_df: Optional[pd.DataFrame],
    market_cap: Optional[float] = None
) -> dict:
    """Extraherar och beräknar TTM- och forensiska nyckeltal ur kvartalsdataframes.

    Ren funktion som inte gör några nätverksanrop.
    """
    res = {
        "fcf_ttm": None,
        "ocf_ttm": None,
        "capex_ttm": None,
        "net_income_ttm": None,
        "ebit_ttm": None,
        "ebitda_ttm": None,
        "revenue_ttm": None,
        "total_debt": None,
        "cash_and_equivalents": None,
        "net_debt": None,
        "total_assets": None,
        "common_equity": None,
        "shares_outstanding": None,
        "shares_outstanding_prev_year": None,
        "dilution_rate_pct": None,
        "sloan_accrual_ratio": None,
        "fcf_yield": None,
        "cash_runway_months": None,
        "gross_margin_latest": None,
        "gross_margin_trend_pct": None,
        "forensic_flags": []
    }

    # 1. Kassaflödesanalys (TTM = summa av upp till 4 senaste kvartal)
    if cf_df is not None and not cf_df.empty:
        # Hämta Free Cash Flow
        fcf_row = None
        for k in ["Free Cash Flow", "FreeCashFlow"]:
            if k in cf_df.index:
                fcf_row = cf_df.loc[k].dropna()
                break
        if fcf_row is not None and len(fcf_row) > 0:
            res["fcf_ttm"] = _safe_float(fcf_row.iloc[:4].sum())

        # Hämta Operating Cash Flow
        ocf_row = None
        for k in ["Operating Cash Flow", "OperatingCashFlow", "Cash Flow From Continuing Operating Activities"]:
            if k in cf_df.index:
                ocf_row = cf_df.loc[k].dropna()
                break
        if ocf_row is not None and len(ocf_row) > 0:
            res["ocf_ttm"] = _safe_float(ocf_row.iloc[:4].sum())

        # CapEx
        capex_row = None
        for k in ["Capital Expenditure", "CapitalExpenditure"]:
            if k in cf_df.index:
                capex_row = cf_df.loc[k].dropna()
                break
        if capex_row is not None and len(capex_row) > 0:
            res["capex_ttm"] = _safe_float(capex_row.iloc[:4].sum())

    # 2. Resultaträkningsanalys (TTM)
    if inc_df is not None and not inc_df.empty:
        # Net Income
        ni_row = None
        for k in ["Net Income", "NetIncome", "Net Income Common Stockholders", "Net Income From Continuing Operation Net Minority Interest"]:
            if k in inc_df.index:
                ni_row = inc_df.loc[k].dropna()
                break
        if ni_row is not None and len(ni_row) > 0:
            res["net_income_ttm"] = _safe_float(ni_row.iloc[:4].sum())

        # EBIT / EBITDA
        for k in ["EBIT", "Operating Income"]:
            if k in inc_df.index:
                ebit_row = inc_df.loc[k].dropna()
                if len(ebit_row) > 0:
                    res["ebit_ttm"] = _safe_float(ebit_row.iloc[:4].sum())
                    break
        for k in ["EBITDA", "Normalized EBITDA"]:
            if k in inc_df.index:
                ebitda_row = inc_df.loc[k].dropna()
                if len(ebitda_row) > 0:
                    res["ebitda_ttm"] = _safe_float(ebitda_row.iloc[:4].sum())
                    break

        # Omsättning & Bruttomarginal
        rev_row = None
        for k in ["Total Revenue", "Operating Revenue", "Revenue"]:
            if k in inc_df.index:
                rev_row = inc_df.loc[k].dropna()
                break
        if rev_row is not None and len(rev_row) > 0:
            res["revenue_ttm"] = _safe_float(rev_row.iloc[:4].sum())

        gp_row = None
        for k in ["Gross Profit", "GrossProfit"]:
            if k in inc_df.index:
                gp_row = inc_df.loc[k].dropna()
                break
        if gp_row is not None and rev_row is not None and len(gp_row) > 0 and len(rev_row) > 0:
            latest_gp = gp_row.iloc[0]
            latest_rev = rev_row.iloc[0]
            if latest_rev and latest_rev > 0:
                res["gross_margin_latest"] = _safe_float(latest_gp / latest_rev)
            
            # Trend över 4 kvartal om data finns
            if len(gp_row) >= 4 and len(rev_row) >= 4:
                old_gp = gp_row.iloc[3]
                old_rev = rev_row.iloc[3]
                if old_rev and old_rev > 0 and latest_rev and latest_rev > 0:
                    old_margin = old_gp / old_rev
                    curr_margin = latest_gp / latest_rev
                    res["gross_margin_trend_pct"] = _safe_float((curr_margin - old_margin) * 100.0)

    # 3. Balansräkningsanalys (Senaste kvartal + YoY jämförelse)
    if bs_df is not None and not bs_df.empty:
        # Total Debt
        for k in ["Total Debt", "TotalDebt", "Long Term Debt And Capital Lease Obligation"]:
            if k in bs_df.index:
                debt_row = bs_df.loc[k].dropna()
                if len(debt_row) > 0:
                    res["total_debt"] = _safe_float(debt_row.iloc[0])
                    break

        # Kassa
        for k in ["Cash And Cash Equivalents", "CashCashEquivalentsAndShortTermInvestments", "End Cash Position"]:
            if k in bs_df.index:
                cash_row = bs_df.loc[k].dropna()
                if len(cash_row) > 0:
                    res["cash_and_equivalents"] = _safe_float(cash_row.iloc[0])
                    break

        # Totala tillgångar & Eget kapital
        for k in ["Total Assets", "TotalAssets"]:
            if k in bs_df.index:
                ta_row = bs_df.loc[k].dropna()
                if len(ta_row) > 0:
                    res["total_assets"] = _safe_float(ta_row.iloc[0])
                    break
        for k in ["Common Stock Equity", "Stockholders Equity", "Total Equity Gross Minority Interest"]:
            if k in bs_df.index:
                eq_row = bs_df.loc[k].dropna()
                if len(eq_row) > 0:
                    res["common_equity"] = _safe_float(eq_row.iloc[0])
                    break

        # Antal aktier & Utspädning YoY
        for k in ["Ordinary Shares Number", "Share Issued"]:
            if k in bs_df.index:
                shares_row = bs_df.loc[k].dropna()
                if len(shares_row) > 0:
                    res["shares_outstanding"] = _safe_float(shares_row.iloc[0])
                    if len(shares_row) >= 4:
                        res["shares_outstanding_prev_year"] = _safe_float(shares_row.iloc[3])
                        if res["shares_outstanding_prev_year"] and res["shares_outstanding_prev_year"] > 0:
                            dilution = (res["shares_outstanding"] - res["shares_outstanding_prev_year"]) / res["shares_outstanding_prev_year"] * 100.0
                            res["dilution_rate_pct"] = _safe_float(dilution)
                    break

    # 4. Beräkna Sammansatta Nyckeltal & Forensiska Signaler
    # Nettoskuld
    if res["total_debt"] is not None and res["cash_and_equivalents"] is not None:
        res["net_debt"] = res["total_debt"] - res["cash_and_equivalents"]

    # FCF Yield
    if res["fcf_ttm"] is not None and market_cap and market_cap > 0:
        res["fcf_yield"] = _safe_float(res["fcf_ttm"] / market_cap)

    # Sloan Accrual Anomaly: (Net Income - Operating Cash Flow) / Total Assets
    if res["net_income_ttm"] is not None and res["ocf_ttm"] is not None and res["total_assets"] and res["total_assets"] > 0:
        accrual = (res["net_income_ttm"] - res["ocf_ttm"]) / res["total_assets"]
        res["sloan_accrual_ratio"] = _safe_float(accrual)

    # Cash Burn Runway (Månader): Kassa / (Kvartalsvis FCF-burn)
    if res["fcf_ttm"] is not None and res["fcf_ttm"] < 0 and res["cash_and_equivalents"] is not None:
        quarterly_burn = abs(res["fcf_ttm"]) / 4.0
        if quarterly_burn > 0:
            runway_months = (res["cash_and_equivalents"] / quarterly_burn) * 3.0
            res["cash_runway_months"] = _safe_float(runway_months)

    # 5. Generera Forensiska Varningsflaggor
    flags = []
    if res["sloan_accrual_ratio"] is not None and res["sloan_accrual_ratio"] > 0.10:
        flags.append("ACCRUAL_WARNING")  # Vinsten syns inte i kassaflödet
    
    if res["cash_runway_months"] is not None and res["cash_runway_months"] < 6.0:
        flags.append("DILUTION_EMISSION_RISK")  # Kassan räcker < 6 månader
    
    if res["dilution_rate_pct"] is not None and res["dilution_rate_pct"] > 10.0:
        flags.append("SHARE_DILUTION_WARNING")  # >10% fler aktier YoY
        
    if res["gross_margin_trend_pct"] is not None and res["gross_margin_trend_pct"] < -3.0:
        flags.append("MARGIN_EROSION")  # Bruttomarginalen faller >3 procentenheter

    if res["fcf_yield"] is not None and res["fcf_yield"] > 0.08:
        flags.append("HIGH_FCF_YIELD")  # Fritt kassaflöde > 8% av börsvärdet

    res["forensic_flags"] = flags
    return res


# ═════════════════════════ HÄMTNING & CACHE ═══════════════════════════════════

def fetch_and_extract_fundamentals(ticker: str, force_refresh: bool = False) -> dict:
    """Hämtar kvartalsbokslut från yfinance med lokal JSON-cache."""
    cache_file = _cache_path(ticker)
    if not force_refresh and cache_file.exists():
        try:
            cached = json.loads(cache_file.read_text(encoding="utf-8"))
            fetched_at = cached.get("fetched_at")
            if fetched_at:
                age_days = (date.today() - date.fromisoformat(fetched_at)).days
                if age_days < CACHE_MAX_AGE_DAYS:
                    return cached.get("data", {})
        except Exception:
            pass

    try:
        import yfinance as yf
        tk = yf.Ticker(ticker)
        fast_inf = tk.fast_info or {}
        mcap = fast_inf.get("marketCap")

        cf_df = tk.quarterly_cashflow
        bs_df = tk.quarterly_balance_sheet
        inc_df = tk.quarterly_income_stmt

        metrics = extract_fundamentals(cf_df, bs_df, inc_df, market_cap=mcap)
        
        # Spara till cache
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "ticker": ticker,
            "fetched_at": date.today().isoformat(),
            "data": metrics
        }
        cache_file.write_text(json.dumps(payload, default=str), encoding="utf-8")
        return metrics
    except Exception as e:
        logger.warning("Fundamentals fetch failed for %s: %s", ticker, e)
        return {"forensic_flags": [], "error": str(e)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticker", type=str, default="PLEJD.ST")
    args = parser.parse_args()
    print(f"Fetching fundamentals for {args.ticker}...")
    res = fetch_and_extract_fundamentals(args.ticker, force_refresh=True)
    print(json.dumps(res, indent=2))
