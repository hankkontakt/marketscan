"""
fi_insider_bulk.py — Bulk-ingestion av FI:s insynsregister.

Hämtar HELA registret per datumintervall (inte per ticker).
Paginerad Search + HTML-fallback. Sparar rått arkiv + upsert till insider_trades.
Prioriterar robusthet: 0-rader-larm, dual parser, idempotent.

Användning:
    python -m backend_worker.fi_insider_bulk --days 7
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import Optional

import pandas as pd
import requests

logger = logging.getLogger(__name__)

# FI:s publika sök-URL
FI_SEARCH_URL = "https://marknadssok.fi.se/publiceringsklient/sv/Search"
FI_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json, text/html",
    "Accept-Language": "sv-SE,sv;q=0.9,en;q=0.8",
}

RAW_ARCHIVE_DIR = Path(__file__).resolve().parent.parent / "data" / "fi_raw"
_BATCH_SIZE = 100  # PageSize for pagination
_PAGE_DELAY = 0.4  # seconds between pages (rate limiting)

# Nyckelord för att klassificera köp vs sälj (från core/fi_insider_fetcher.py)
_BUY_KEYWORDS = ["förvärv", "köp", "tilldelning", "teckning", "konvertering"]
_SELL_KEYWORDS = ["avyttring", "försäljning", "sälj"]


def fetch_page(from_date: str, to_date: str, page: int = 1, page_size: int = _BATCH_SIZE) -> list[dict]:
    """Hämta en sida från FI-registret via Search API.

    Försöker JSON först, faller tillbaka till HTML-parsning.
    Returnerar lista med råa transaktions-dicts (tom om sidan saknar data).
    """
    params = {
        "SearchFunctionType": "Insyn",
        "FromDate": from_date,
        "ToDate": to_date,
        "Page": page,
        "PageSize": page_size,
        "Sort": "Transaktionsdatum desc",
    }

    # JSON-försök
    try:
        resp = requests.get(FI_SEARCH_URL, params={**params, "format": "json"}, headers=FI_HEADERS, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            rows = _parse_fi_json(data)
            if rows:
                return rows
    except Exception as e:
        logger.warning("FI JSON-försök misslyckades (page %d): %s", page, e)

    # HTML-fallback
    try:
        resp = requests.get(FI_SEARCH_URL, params=params, headers=FI_HEADERS, timeout=30)
        if resp.status_code == 200:
            rows = _parse_fi_html(resp.text)
            return rows
    except Exception as e:
        logger.warning("FI HTML-fallback misslyckades (page %d): %s", page, e)

    return []


def _parse_fi_json(data: dict) -> list[dict]:
    """Parse FI JSON-svar. Anpassad efter FI:s responsstruktur."""
    rows = []
    # FI returnerar ofta en lista under 'data' eller 'results'
    items = data.get("data") or data.get("results") or data.get("Items") or []
    if isinstance(items, list):
        for item in items:
            if isinstance(item, dict):
                rows.append(item)
    return rows


def _parse_fi_html(html: str) -> list[dict]:
    """Parse FI HTML-tabell som fallback om JSON misslyckas."""
    rows = []
    try:
        from bs4 import BeautifulSoup as BS
        soup = BS(html, "html.parser")
        table = soup.find("table")
        if not table:
            return rows
        headers = [th.get_text(strip=True) for th in table.find_all("th")]
        for tr in table.find_all("tr")[1:]:
            tds = tr.find_all("td")
            if len(tds) == len(headers):
                row = {}
                for i, h in enumerate(headers):
                    row[h] = tds[i].get_text(strip=True)
                rows.append(row)
    except ImportError:
        logger.warning("BeautifulSoup not installed for HTML fallback")
    except Exception as e:
        logger.warning("HTML parsing failed: %s", e)
    return rows


def _classify_transaction(karaktar: str) -> str:
    """Klassificera transaktionstyp baserat på FI:s karaktär."""
    karaktar_lower = (karaktar or "").lower()
    for kw in _BUY_KEYWORDS:
        if kw in karaktar_lower:
            return "buy"
    for kw in _SELL_KEYWORDS:
        if kw in karaktar_lower:
            return "sell"
    return "unknown"


def normalize_transaction(raw: dict) -> Optional[dict]:
    """Normalisera en FI-transaktion till vårt schema.

    Returnerar dict med isin, issuer, name, role, type, shares, price, amount, trade_date.
    """
    try:
        trade = {
            "isin": raw.get("ISIN") or raw.get("isin") or "",
            "issuer": raw.get("Emittent") or raw.get("issuer") or raw.get("CompanyName") or "",
            "name": raw.get("Person") or raw.get("name") or raw.get("PersonName") or "",
            "role": raw.get("Befattning") or raw.get("role") or raw.get("Position") or "",
            "type": _classify_transaction(
                raw.get("Karaktär") or raw.get("karaktar") or raw.get("TransactionType") or ""
            ),
            "shares": _parse_float(raw, ["Volym", "shares", "Volume", "Antal"]),
            "price": _parse_float(raw, ["Pris", "price", "Price"]),
            "amount": _parse_float(raw, ["Belopp", "amount", "Amount", "TotalValue"]),
            "trade_date": _parse_date(raw, ["Transaktionsdatum", "trade_date", "TransactionDate", "Datum"]),
        }
        # amount fallback: shares * price
        if (trade["amount"] is None or trade["amount"] == 0) and trade["shares"] and trade["price"]:
            trade["amount"] = trade["shares"] * trade["price"]
        if not trade["isin"] or not trade["trade_date"]:
            return None
        return trade
    except Exception as e:
        logger.debug("Skipping row due to parse error: %s", e)
        return None


def _parse_float(raw: dict, keys: list[str]) -> Optional[float]:
    for k in keys:
        val = raw.get(k)
        if val is not None:
            try:
                return float(str(val).replace(" ", "").replace(",", "."))
            except (ValueError, TypeError):
                pass
    return None


def _parse_date(raw: dict, keys: list[str]) -> Optional[str]:
    for k in keys:
        val = raw.get(k)
        if val and isinstance(val, str) and len(val) >= 10:
            try:
                return datetime.strptime(val[:10], "%Y-%m-%d").strftime("%Y-%m-%d")
            except ValueError:
                pass
    return None


def fetch_register(from_date: str, to_date: str) -> list[dict]:
    """Hämta alla transaktioner i ett datumintervall.

    Paginerar genom FI-registret. Returnerar normaliserade transaktioner.
    """
    all_trades = []
    page = 1

    while True:
        rows = fetch_page(from_date, to_date, page)
        if not rows:
            break  # Ingen mer data

        normalized = [normalize_transaction(r) for r in rows]
        normalized = [n for n in normalized if n is not None]
        all_trades.extend(normalized)

        logger.info("  Page %d: %d raw, %d normalized (total %d)", page, len(rows), len(normalized), len(all_trades))
        page += 1
        time.sleep(_PAGE_DELAY)

    return all_trades


def _map_isin_to_ticker(isin: str, conn) -> Optional[str]:
    """Mappa ISIN till ticker via company_profiles-tabellen."""
    if not isin:
        return None
    try:
        cur = conn.cursor()
        cur.execute("SELECT ticker FROM company_profiles WHERE isin = %s", (isin,))
        row = cur.fetchone()
        return row[0] if row else None
    except Exception:
        return None


def save_raw_archive(trades: list[dict], archive_date: str):
    """Spara rådata till arkiv för återspelning."""
    RAW_ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    path = RAW_ARCHIVE_DIR / f"{archive_date}.json"
    path.write_text(json.dumps(trades, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("Råarkiv sparat: %s (%d trades)", path.name, len(trades))


def upsert_trades(trades: list[dict], conn):
    """Upsert till insider_trades-tabellen.

    Mappar ISIN→ticker via company_profiles.
    """
    if not trades:
        logger.warning("Inga trades att upsert — 0-rader!")
        return 0

    cur = conn.cursor()
    inserted = 0
    unmapped = []

    for trade in trades:
        ticker = _map_isin_to_ticker(trade["isin"], conn)
        if not ticker and trade["issuer"]:
            # Fallback: försök mappa på issuer-namn
            try:
                cur.execute(
                    "SELECT ticker FROM company_profiles "
                    "WHERE LOWER(description) LIKE %s OR LOWER(industry) LIKE %s LIMIT 1",
                    (f"%{trade['issuer'].lower()}%", f"%{trade['issuer'].lower()}%"),
                )
                row = cur.fetchone()
                ticker = row[0] if row else None
            except Exception:
                pass

        if not ticker:
            unmapped.append(trade)
            continue

        try:
            cur.execute("""
                INSERT INTO insider_trades (ticker, name, trade_date, type, shares, price, amount, isin, role)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (ticker, name, trade_date, type) DO NOTHING
            """, (
                ticker, trade["name"], trade["trade_date"], trade["type"],
                trade["shares"], trade["price"], trade["amount"],
                trade["isin"], trade["role"],
            ))
            if cur.rowcount > 0:
                inserted += 1
        except Exception as e:
            logger.warning("Upsert failed for %s/%s: %s", ticker, trade["trade_date"], e)

    conn.commit()

    # Logga unmapped trades separat
    if unmapped:
        log_path = RAW_ARCHIVE_DIR / f"unmapped_{datetime.now().strftime('%Y%m%d')}.json"
        log_path.write_text(json.dumps(unmapped, indent=2, ensure_ascii=False), encoding="utf-8")
        logger.warning("%d unmapped trades logged to %s", len(unmapped), log_path.name)

    logger.info("Upserted %d/%d trades (%d unmapped)", inserted, len(trades), len(unmapped))
    return inserted


def main():
    parser = argparse.ArgumentParser(description="FI Insider Bulk Ingestion")
    parser.add_argument("--days", type=int, default=7, help="Antal dagar bakåt att hämta")
    parser.add_argument("--from-date", type=str, help="Startdatum (YYYY-MM-DD)")
    parser.add_argument("--to-date", type=str, help="Slutdatum (YYYY-MM-DD)")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    # Datumintervall
    to_date = args.to_date or date.today().strftime("%Y-%m-%d")
    from_date = args.from_date or (date.today() - timedelta(days=args.days)).strftime("%Y-%m-%d")

    logger.info("Hämtar FI-insynsregister %s → %s", from_date, to_date)

    # Hämta
    trades = fetch_register(from_date, to_date)

    # 0-rader-larm
    if not trades:
        logger.error(
            "FI-registret returnerade 0 transaktioner för %s → %s. "
            "Detta är misstänkt — FI kan ha ändrat endpoint eller HTML-struktur.",
            from_date, to_date,
        )
        print(json.dumps({"status": "error", "message": "0 trades fetched", "trades": 0}))
        sys.exit(1)

    logger.info("Hämtade %d transaktioner", len(trades))

    # Spara rått arkiv
    archive_key = f"{from_date}_{to_date}"
    save_raw_archive(trades, archive_key)

    # DB-uppladdning
    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        try:
            import psycopg2
            conn = psycopg2.connect(database_url)
            inserted = upsert_trades(trades, conn)
            conn.close()
        except Exception as e:
            logger.error("DB-uppladdning misslyckades: %s", e)
            print(json.dumps({"status": "error", "message": str(e), "trades": len(trades)}))
            sys.exit(1)
    else:
        logger.warning("DATABASE_URL not set — skipping DB upsert")
        inserted = 0

    result = {
        "status": "ok",
        "from_date": from_date,
        "to_date": to_date,
        "trades_fetched": len(trades),
        "trades_inserted": inserted,
    }
    print(json.dumps(result))
    logger.info("FI-bulk-ingestion klar: %d trades", len(trades))


if __name__ == "__main__":
    main()
