"""
news_discovery.py — Bred nyhetssökning (Google News RSS + DDGS) med tema-filter
och "mention-surge"-detektor (omtalande 24-48h vs 30-dagars baslinje).

Google News RSS är VERIFIERAD (2026-08-28): after:/site:/booleska filter fungerar
från valfri server, gratis, utan nyckel. Cap ~100 träffar per query → fönster-queries.

Användning:
    python -m backend_worker.news_discovery --dry-run
    python -m backend_worker.news_discovery --themes ipo,order
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
import xml.etree.ElementTree as ET
from datetime import date, timedelta

import requests

from backend_worker.news_common import (connect, load_registry, match_ticker,
                                        parse_pubdate, upsert_events)

logger = logging.getLogger(__name__)

GNEWS_URL = "https://news.google.com/rss/search"
DEDUP_WINDOW_DAYS = 7
SURGE_WINDOW_HOURS = 48
BASELINE_DAYS = 30

# Tema-queries — verifierade operatorer: after:, site:, booleska, -site: (ej intitle:)
THEMES = {
    "ipo": 'börsintroduktion OR notering OR "lista sig"',
    "order": '("order" OR "kontrakt" OR "avtal") och (börs OR aktie)',
    "vinstvarning": 'vinstvarning OR resultatvarning OR "vinstvarnar"',
    "ledning": '"vd avgår" OR "ny vd" OR "verkställande direktör"',
    "regulatorik": '(godkännande OR tillstånd) och (börs OR FDA OR EMA)',
    "sector-ai": '(AI OR "halvledare" OR semicons) och (börs OR aktie OR bolag)',
    "sector-forsvar": '(försvar OR "militär" OR säkerhet) och (börs OR order)',
    "dilution": '(emission OR "kapitalanskaffning" OR "företrädesemission") och börs',
}


def fetch_gnews(query: str, after_days: int = 2) -> list[dict]:
    after = (date.today() - timedelta(days=after_days)).isoformat()
    r = requests.get(
        GNEWS_URL,
        params={"q": f"{query} after:{after}", "hl": "sv", "gl": "SE", "ceid": "SE:sv"},
        timeout=30,
    )
    r.raise_for_status()
    root = ET.fromstring(r.content)
    out = []
    for it in root.findall(".//item")[:100]:
        title = (it.find("title").text or "").strip()
        link = (it.find("link").text or "").strip()
        pub = (it.find("pubDate").text or "") if it.find("pubDate") is not None else ""
        src = it.find("source").text if it.find("source") is not None else ""
        if not title or not link:
            continue
        out.append({
            "headline": title,
            "message_url": link,
            "published_at": parse_pubdate(pub),
            "company_raw": (src or "").strip(),
        })
    return out


def compute_surge(conn, ticker: str, now_hits: int) -> float | None:
    """(antal omtalade 48h) / max(1, per-dag-snitt 30d) → surge-faktor (>1 = förhöjd)."""
    if not ticker:
        return None
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT COUNT(*) FROM news_events
            WHERE ticker = %s AND published_at > NOW() - INTERVAL '%s days'
        """, (ticker, BASELINE_DAYS,))
        total_30d = cur.fetchone()[0]
        baseline_per_day = max(total_30d, 1) / BASELINE_DAYS
        return round(now_hits / baseline_per_day, 2)
    except Exception:
        return None


def main():
    parser = argparse.ArgumentParser(description="Bred nyhetsdiscovery + mention-surge")
    parser.add_argument("--themes", default=",".join(THEMES.keys()))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    theme_names = [t.strip() for t in args.themes.split(",") if t.strip()]
    rows = []
    matched = 0
    for name in theme_names:
        q = THEMES.get(name)
        if not q:
            logger.warning("Okänt tema: %s", name)
            continue
        try:
            items = fetch_gnews(q)
        except Exception as e:
            logger.warning("Tema %s misslyckades: %s", name, e)
            continue
        for it in items:
            it["source"] = "gnews"
            it["source_category"] = name
        rows.extend(items)
        logger.info("Tema %s: %d träffar", name, len(items))
        time.sleep(1.2)   # Google News är rate-känslig

    if not rows:
        logger.error("0 träffar — Google News svarade tomt")
        print(json.dumps({"status": "error", "rows": 0}))
        sys.exit(1)

    conn = None
    registry = {}
    if not args.dry_run:
        conn = connect()
        registry = load_registry(conn)

    # Namnmatch + surge
    norm_rows = []
    for r in rows:
        ticker = match_ticker(r["headline"], registry) if registry else None
        r["ticker"] = ticker
        if ticker:
            matched += 1
            r["mention_surge"] = compute_surge(conn, ticker, 1)
        else:
            r["mention_surge"] = None
        norm_rows.append(r)

    if conn:
        stats = upsert_events(conn, norm_rows)
        print(json.dumps({"status": "ok", "themes": theme_names, **stats,
                          "matched_tickers": matched}))
    else:
        teaser = [{"tema": r["source_category"], "rubrik": r["headline"][:60]}
                  for r in norm_rows[:4]]
        print(json.dumps({"status": "ok", "rows": len(norm_rows),
                          "matched_tickers": matched, "preview": teaser}))
    if conn:
        conn.close()


if __name__ == "__main__":
    main()
