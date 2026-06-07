#!/usr/bin/env python3
"""
seed_demo.py — fill scan_results with known stocks for local dev/testing.

Use when you need demo data without running the full pipeline:
  python scripts/seed_demo.py

Requires SUPABASE_URL + SUPABASE_SERVICE_KEY in .env.
"""
import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

DEMO_STOCKS = [
    {"ticker": "VOLV-B.ST", "name": "Volvo AB B", "sector": "Industri", "segment": "large_cap", "price": 285.5, "score_total": 72.0, "score_value": 68.0, "score_quality": 75.0, "score_momentum": 70.0, "score_growth": 65.0, "score_risk": 60.0, "score_dividend": 55.0, "pe_trailing": 12.5, "roe": 22.0, "entry_signal": "OK", "change_pct": 1.2, "market_cap": 580_000_000_000, "currency": "SEK"},
    {"ticker": "ERIC-B.ST", "name": "Ericsson B", "sector": "Teknik", "segment": "large_cap", "price": 82.0, "score_total": 58.0, "score_value": 72.0, "score_quality": 55.0, "score_momentum": 62.0, "score_growth": 48.0, "score_risk": 45.0, "score_dividend": 50.0, "pe_trailing": 18.0, "roe": 8.0, "entry_signal": "VÄNTA", "change_pct": -0.5, "market_cap": 270_000_000_000, "currency": "SEK"},
    {"ticker": "SEB-A.ST", "name": "Skandinaviska Enskilda Banken A", "sector": "Finans", "segment": "large_cap", "price": 165.0, "score_total": 76.0, "score_value": 70.0, "score_quality": 80.0, "score_momentum": 72.0, "score_growth": 68.0, "score_risk": 55.0, "score_dividend": 65.0, "pe_trailing": 10.2, "roe": 15.0, "entry_signal": "STARK", "change_pct": 2.1, "market_cap": 340_000_000_000, "currency": "SEK"},
    {"ticker": "HM-B.ST", "name": "Hennes & Mauritz B", "sector": "Konsument", "segment": "large_cap", "price": 175.0, "score_total": 62.0, "score_value": 74.0, "score_quality": 58.0, "score_momentum": 55.0, "score_growth": 45.0, "score_risk": 50.0, "score_dividend": 70.0, "pe_trailing": 15.8, "roe": 18.0, "entry_signal": "OK", "change_pct": 0.8, "market_cap": 280_000_000_000, "currency": "SEK"},
    {"ticker": "ATCO-A.ST", "name": "AstraZeneca (lokal notering)", "sector": "Hälsovård", "segment": "large_cap", "price": 1650.0, "score_total": 80.0, "score_value": 65.0, "score_quality": 85.0, "score_momentum": 78.0, "score_growth": 75.0, "score_risk": 50.0, "score_dividend": 45.0, "pe_trailing": 35.0, "roe": 28.0, "entry_signal": "STARK", "change_pct": 0.3, "market_cap": 2_000_000_000_000, "currency": "SEK"},
    {"ticker": "INVE-B.ST", "name": "Investor B", "sector": "Finans", "segment": "large_cap", "price": 285.0, "score_total": 78.0, "score_value": 72.0, "score_quality": 82.0, "score_momentum": 74.0, "score_growth": 70.0, "score_risk": 45.0, "score_dividend": 40.0, "pe_trailing": 14.0, "roe": 20.0, "entry_signal": "STARK", "change_pct": 1.5, "market_cap": 430_000_000_000, "currency": "SEK"},
    {"ticker": "TELIA.ST", "name": "Telia Company", "sector": "Telekom", "segment": "large_cap", "price": 32.0, "score_total": 55.0, "score_value": 68.0, "score_quality": 60.0, "score_momentum": 48.0, "score_growth": 35.0, "score_risk": 52.0, "score_dividend": 80.0, "pe_trailing": 20.0, "roe": 6.0, "entry_signal": "VÄNTA", "change_pct": -0.2, "market_cap": 125_000_000_000, "currency": "SEK"},
    {"ticker": "BOL.ST", "name": "Boliden", "sector": "Råvaror", "segment": "large_cap", "price": 380.0, "score_total": 68.0, "score_value": 72.0, "score_quality": 65.0, "score_momentum": 62.0, "score_growth": 55.0, "score_risk": 48.0, "score_dividend": 50.0, "pe_trailing": 11.0, "roe": 16.0, "entry_signal": "OK", "change_pct": 3.2, "market_cap": 105_000_000_000, "currency": "SEK"},
    {"ticker": "SAND.ST", "name": "Sandvik", "sector": "Industri", "segment": "large_cap", "price": 230.0, "score_total": 74.0, "score_value": 68.0, "score_quality": 78.0, "score_momentum": 70.0, "score_growth": 65.0, "score_risk": 55.0, "score_dividend": 55.0, "pe_trailing": 18.0, "roe": 24.0, "entry_signal": "OK", "change_pct": 0.9, "market_cap": 290_000_000_000, "currency": "SEK"},
    {"ticker": "SSAB-A.ST", "name": "SSAB A", "sector": "Råvaror", "segment": "mid_cap", "price": 55.0, "score_total": 65.0, "score_value": 78.0, "score_quality": 52.0, "score_momentum": 60.0, "score_growth": 42.0, "score_risk": 40.0, "score_dividend": 30.0, "pe_trailing": 5.0, "roe": 12.0, "entry_signal": "OK", "change_pct": -1.5, "market_cap": 55_000_000_000, "currency": "SEK"},
    {"ticker": "TSLA", "name": "Tesla Inc", "sector": "Konsument", "segment": "large_cap", "price": 248.0, "score_total": 52.0, "score_value": 35.0, "score_quality": 45.0, "score_momentum": 65.0, "score_growth": 70.0, "score_risk": 30.0, "score_dividend": 0.0, "pe_trailing": 50.0, "roe": 10.0, "entry_signal": "VÄNTA", "change_pct": 4.2, "market_cap": 8_000_000_000_000, "currency": "USD"},
]


def main():
    supabase_url = os.getenv("SUPABASE_URL", "")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY", "")
    if not supabase_url or not supabase_key:
        print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in .env")
        sys.exit(1)

    from supabase import create_client
    sb = create_client(supabase_url, supabase_key)

    # Check existing count
    existing = sb.table("scan_results").select("ticker", count="exact").execute()
    existing_count = existing.count or 0
    print(f"Existing scan_results rows: {existing_count}")

    if existing_count > 0:
        print("Database already has data. Skipping seed.")
        return

    inserted = 0
    for stock in DEMO_STOCKS:
        try:
            sb.table("scan_results").upsert(stock, on_conflict="ticker").execute()
            inserted += 1
            print(f"  + {stock['ticker']} — {stock['name']}")
        except Exception as e:
            print(f"  ! {stock['ticker']} — error: {e}")

    print(f"\nSeeded {inserted}/{len(DEMO_STOCKS)} stocks.")
    print("Start the API and frontend to see demo data.")


if __name__ == "__main__":
    main()
