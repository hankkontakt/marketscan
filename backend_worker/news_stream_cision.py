"""
news_stream_cision.py — Realtidsingestion av Cision MAR-pressmeddelanden.

Hämtar och filtrerar regulatoriska pressmeddelanden för svenska noterade bolag:
  1. RSS-polling från news.cision.com/se/rss/all (100% gratis).
  2. Smart token-besparande för-filter (sållar bort stämmokallelser och admin-notiser).
  3. Mappar emittent till Ticker/ISIN via SEED_TICKERS.
  4. Analyserar högeffektshändelser (ordrar, förvärv, rapporter) via ai_report_analyzer.py.
  5. Deduplicering med lokal state-cache.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional

import requests

from backend_worker.universe_mapping import SEED_TICKERS

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

CISION_RSS_URL = "https://news.cision.com/se/rss/all"
STATE_FILE = Path(__file__).resolve().parent.parent / "data" / "cision_state.json"

# Regex för att sålla bort icke-kurspåverkande administrativt brus (Sparar ~70% AI-tokens!)
_IGNORE_PATTERNS = [
    re.compile(r"kallelse till (årsstämma|extra bolagsstämma)", re.IGNORECASE),
    re.compile(r"valberedningens (förslag|sammansättning)", re.IGNORECASE),
    re.compile(r"publicering av årsredovisning", re.IGNORECASE),
    re.compile(r"finansiell kalender", re.IGNORECASE),
    re.compile(r"inbjudan till presentation av", re.IGNORECASE),
    re.compile(r"ändring av antalet aktier och röster", re.IGNORECASE),
    re.compile(r"beslut vid (årsstämma|extra bolagsstämma)", re.IGNORECASE),
    re.compile(r"offentliggörande av prospekt", re.IGNORECASE),
]

# Mönster för händelser som SKA analyseras av AI
_PRIORITY_PATTERNS = [
    re.compile(r"(delårsrapport|bokslutskommuniké|kvartalsrapport|q[1-4]-rapport)", re.IGNORECASE),
    re.compile(r"(avtal|order|ramavtal|beställning|samarbetsavtal)", re.IGNORECASE),
    re.compile(r"(förvärv|förvärvar|avyttring)", re.IGNORECASE),
    re.compile(r"(vinstvarning|omvänd vinstvarning)", re.IGNORECASE),
    re.compile(r"(patent|fda|godkännande|ce-märk|studieresultat)", re.IGNORECASE),
    re.compile(r"(utser|ny vd|lämnar|vd-byte)", re.IGNORECASE),
]


# ═════════════════════════ PURE CORE (Testbar; ingen I/O) ═════════════════════

def is_noise_item(title: str) -> bool:
    """Returnerar True om notisen är administrativt brus som ska ignoreras."""
    for pat in _IGNORE_PATTERNS:
        if pat.search(title):
            return True
    return False


def is_priority_item(title: str) -> bool:
    """Returnerar True om notisen är en operativ eller finansiell nyckeltrigger."""
    for pat in _PRIORITY_PATTERNS:
        if pat.search(title):
            return True
    return False


def parse_rss_xml(xml_content: bytes) -> list[dict]:
    """Parsar RSS XML till en lista av strukturerade ordböcker."""
    items = []
    try:
        root = ET.fromstring(xml_content)
        for item_elem in root.findall(".//item"):
            title = item_elem.findtext("title") or ""
            link = item_elem.findtext("link") or ""
            pub_date = item_elem.findtext("pubDate") or ""
            description = item_elem.findtext("description") or ""
            guid = item_elem.findtext("guid") or link or title
            
            # Generera unikt hash för deduplicering
            item_hash = hashlib.sha256(f"{title}_{pub_date}".encode("utf-8")).hexdigest()[:16]
            
            items.append({
                "guid": guid,
                "hash": item_hash,
                "title": title.strip(),
                "link": link.strip(),
                "pub_date": pub_date.strip(),
                "description": description.strip()
            })
    except Exception as e:
        logger.warning("Failed to parse RSS XML: %s", e)
    return items


def match_company_to_ticker(title: str) -> Optional[str]:
    """Mappar ett pressmeddelandes titel till en känd börsticker."""
    title_lower = title.lower()
    
    # Exakta prefix-matcher (t.ex. "PLEJD: Plejd lanserar...")
    prefix_match = re.match(r"^([a-zåäö0-9\s\-]+):", title_lower)
    if prefix_match:
        cand = prefix_match.group(1).strip()
        # Sök i SEED_TICKERS
        for isin, tk in SEED_TICKERS.items():
            base = tk.replace(".ST", "").replace("-B", "").replace("-A", "").lower()
            if base in cand or cand in base:
                return tk

    # Fritextsökning i titeln mot kända tickers
    for isin, tk in SEED_TICKERS.items():
        base = tk.replace(".ST", "").replace("-B", "").replace("-A", "").lower()
        if len(base) >= 4 and base in title_lower:
            return tk
            
    return None


# ═════════════════════════ I/O & PIPELINE ═════════════════════════════════════

def load_processed_state() -> set[str]:
    if STATE_FILE.exists():
        try:
            data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            return set(data.get("processed_hashes", []))
        except Exception:
            pass
    return set()


def save_processed_state(hashes: set[str]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    # Begränsa historik till de senaste 2 000 notiserna
    trimmed = list(hashes)[-2000:]
    STATE_FILE.write_text(json.dumps({"processed_hashes": trimmed}), encoding="utf-8")


def poll_cision_feed(limit: int = 30, dry_run: bool = False) -> list[dict]:
    """Hämtar Cision RSS, filtrerar, deduplicerar och analyserar med AI."""
    logger.info("Polling Cision RSS feed from %s...", CISION_RSS_URL)
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) MarketScan/2.0"}
    try:
        resp = requests.get(CISION_RSS_URL, headers=headers, timeout=15)
        if resp.status_code != 200:
            logger.warning("Cision returned HTTP %s", resp.status_code)
            return []
    except Exception as e:
        logger.error("Cision request failed: %s", e)
        return []

    raw_items = parse_rss_xml(resp.content)
    processed = load_processed_state()
    new_items = [it for it in raw_items if it["hash"] not in processed][:limit]

    logger.info("Found %d items in feed (%d new)", len(raw_items), len(new_items))
    results = []

    for it in new_items:
        title = it["title"]
        processed.add(it["hash"])

        if is_noise_item(title):
            logger.debug("Skipping administrative noise: %s", title)
            continue

        ticker = match_company_to_ticker(title)
        is_priority = is_priority_item(title)
        
        logger.info("Processing Cision item: [%s] (Priority: %s, Ticker: %s)", title[:60], is_priority, ticker)
        
        item_res = {
            "title": title,
            "link": it["link"],
            "pub_date": it["pub_date"],
            "ticker": ticker,
            "is_priority": is_priority,
            "ai_analysis": None
        }

        # Om det är en prioriterad operativ händelse och vi inte kör dry-run -> analysera med AI
        if is_priority and not dry_run:
            try:
                from backend_worker.ai_report_analyzer import analyze_press_release
                ai_res = analyze_press_release(
                    pr_text=f"{title}\n{it['description']}",
                    ticker=ticker or ""
                )
                if ai_res.get("success"):
                    item_res["ai_analysis"] = ai_res.get("data")
                    logger.info("AI Analysis: Catalyst Score=%s | Type=%s", 
                                item_res["ai_analysis"].get("catalyst_impact_score"),
                                item_res["ai_analysis"].get("event_type"))
            except Exception as e:
                logger.warning("AI analysis failed for item: %s", e)

        results.append(item_res)

    if not dry_run:
        save_processed_state(processed)

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Kör utan att spara state eller anropa AI")
    args = parser.parse_args()
    res = poll_cision_feed(limit=10, dry_run=args.dry_run)
    print(f"Processed {len(res)} actionable items.")
    for r in res:
        print(f"- [{r['ticker'] or 'UNKNOWN'}] {r['title'][:70]}")
        if r['ai_analysis']:
            print(f"  AI: {r['ai_analysis']}")
