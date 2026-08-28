"""
news_events.py — Officiella börsmeddelanden från Nasdaq Nordics öppna API.

Källa: https://api.news.eu.nasdaq.com/news/query.action?type=json&market=SSE
(verifierat 2026-08-28: meddelanden med cnsCategory, disclosureId, exakt tid).

Regelbaserade bäringar appliceras direkt vid ingest (fria, deterministiska):
  - 'Changes in company's own shares' → positive (buyback-evidens +0.9-1.6 %)
  - 'Prospectus/Announcement of Prospectus' → negative (emission/villkor)
  - 'Tender offer' → conditional
  - Finansrapporter / stämma / calender → neutral (informativ)
  - 'Inside information' / 'Company Announcement' / 'Investor News' → LLM-klassificeras
    (news_classifier.py) eftersom riktningen kräver kontext.

Användning:
    python -m backend_worker.news_events --dry-run
    python -m backend_worker.news_events --market SSE
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import sys
from datetime import date, timedelta

import requests

from backend_worker.news_common import connect, load_registry, match_ticker, upsert_events

logger = logging.getLogger(__name__)

NASDAQ_URL = "https://api.news.eu.nasdaq.com/news/query.action"
DEFAULT_LIMIT = 200

# Regelbaserade bäringar per cnsCategory (ingår evidens-PROXIES; källkod kommenterad)
RULE_BEARINGS = {
    "Changes in company's own shares": ("positive", 0.6, "buyback/återköp"),
    "Prospectus/Announcement of Prospectus": ("negative", 0.5, "prospectus/emission"),
    "Tender offer": ("conditional", 0.5, "tender offer"),
    "Managers' Transactions": ("neutral", 1.0, "insider-transaktion (informativ)"),
    "Half Year financial report": ("neutral", 1.0, "rapport (informativ)"),
    "Half year financial report": ("neutral", 1.0, "rapport (informativ)"),
    "Interim report (Q1 and Q3)": ("neutral", 1.0, "rapport (informativ)"),
    "Quarterly report": ("neutral", 1.0, "rapport (informativ)"),
    "Financial Calendar": ("neutral", 1.0, "finanskalender"),
    "Decisions of general meeting": ("neutral", 0.9, "stämmobeslut"),
    "Notice to general meeting": ("neutral", 0.9, "stämmokallelse"),
    "Annual Financial Report": ("neutral", 1.0, "årsrapport"),
    "Financial Statement Release": ("neutral", 1.0, "rapport (informativ)"),
    "Financial statement release": ("neutral", 1.0, "rapport (informativ)"),
    "Half-Yearly information": ("neutral", 1.0, "rapport (informativ)"),
    "Other information disclosed according to the rules of the Exchange":
        ("neutral", 0.6, "övrig information"),
}


def fetch_nasdaq(market: str = "SSE", limit: int = DEFAULT_LIMIT) -> list[dict]:
    r = requests.get(
        NASDAQ_URL,
        params={"type": "json", "market": market, "limit": limit, "offset": 0},
        timeout=40,
    )
    r.raise_for_status()
    data = r.json()
    items = (
        data.get("results", {}).get("item")
        or data.get("item") or data.get("items") or []
    )
    if isinstance(items, dict):
        items = [items]
    return items


def apply_rule_bearings(conn, source_category: str, bearing: str, confidence: float,
                        direction: str) -> None:
    """Markera regelklassade meddelanden (klassificeraren skippar dem sedan)."""
    cur = conn.cursor()
    cur.execute("""
        UPDATE news_events SET bearing = %s, confidence = %s, direction = %s,
               classified_at = NOW()
        WHERE source = 'nasdaq' AND source_category = %s AND bearing IS NULL
    """, (bearing, confidence, direction, source_category))
    conn.commit()


def main():
    parser = argparse.ArgumentParser(description="Nasdaq Nordic officiella meddelanden")
    parser.add_argument("--market", default="SSE")
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    items = fetch_nasdaq(args.market, args.limit)
    if not items:
        logger.error("Nasdaq-API:t gav 0 meddelanden")
        print(json.dumps({"status": "error", "rows": 0}))
        sys.exit(1)

    conn = None
    registry = {}
    if not args.dry_run:
        conn = connect()
        registry = load_registry(conn)

    rows = []
    for it in items:
        published = (it.get("published") or it.get("releaseTime") or "").strip()
        url = it.get("messageUrl") or ""
        if not url or not it.get("headline"):
            continue
        ticker = None
        if registry:
            ticker = match_ticker(it.get("headline", ""), registry)
        rows.append({
            "source": "nasdaq",
            "source_category": it.get("cnsCategory") or "UNCATEGORIZED",
            "headline": it.get("headline", "").strip(),
            "company_raw": (it.get("company") or "").strip(),
            "ticker": ticker,
            "published_at": published,
            "message_url": url,
        })

    try:
        if conn:
            stats = upsert_events(conn, rows)
            # Regelbaserade bäringar
            for cat, (bearing, conf, direction) in RULE_BEARINGS.items():
                apply_rule_bearings(conn, cat, bearing, conf, direction)
            logger.info("Nasdaq: %s (regel-klassade via RULE_BEARINGS)", json.dumps(stats))
            print(json.dumps({"status": "ok", **stats}))
        else:
            print(json.dumps({"status": "ok", "rows": len(rows),
                              "preview": rows[:3]}))
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    main()
