"""
fi_insider_bulk.py — Bulk-ingestion av FI:s insynsregister.

Källa: marknadssok.fi.se CSV-export (verifierad live 2026-08-28):
    GET https://marknadssok.fi.se/publiceringsklient/sv/Search/Search
        ?SearchFunctionType=Insyn
        &Publiceringsdatum.From=YYYY-MM-DD
        &Publiceringsdatum.To=YYYY-MM-DD
        &button=export&Page=1
    → 200 text/csv, UTF-16-LE, semikolonseparerad, HELA fönstret i ett svar
      (Page-parametern ignoreras av exporten).

GAMLA parametrarna (FromDate/ToDate + format=json på /sv/Search) IGNORERAR
datumfiltret (bevisat live 2026-08-28: hela 166 978-raders registret
returnerades) — ersatta. HTML-sök (button=search) = ENDAST fallback vid
transportfel; vilken väg som användes loggas alltid.

Upsert-semantik (migration 049, insider_trades_reconcile_key):
  - aggregera pre-insert per (COALESCE(isin, ticker), name, trade_date, type)
    → SUM(shares), SUM(amount)  (delad volym = en rad)
  - Status='History' → skip (aldrig upsertad)
  - Revised → DO UPDATE (överskriv värden, isin=EXCLUDED.isin)
  - ON CONFLICT (COALESCE(isin, ticker), name, trade_date, type) — träffar
    insider_trades_reconcile_key-indexet (annars: 'no unique or exclusion
    constraint matching the ON CONFLICT specification').

0-rader: varning + {"status":"ok","rows":0,"empty_ok":true} + ping söksidan
utan filter (bevis på levande endpoint). Hårdfel ENDAST vid exceptions.

Användning:
    python -m backend_worker.fi_insider_bulk --days 7
    python -m backend_worker.fi_insider_bulk --from-date 2026-08-01 --to-date 2026-08-28
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import logging
import os
import re
import sys
import time
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import Optional

import requests

logger = logging.getLogger(__name__)

# FI:s publika sök-URL:er (verifierade live 2026-08-28)
# CSV-exporten kräver sökvägen /Search/Search (inte /Search) + button=export.
FI_SEARCH_URL = "https://marknadssok.fi.se/publiceringsklient/sv/Search/Search"
FI_SEARCH_URL_HTML = "https://marknadssok.fi.se/publiceringsklient/sv/Search"
FI_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/csv, text/html, */*",
    "Accept-Language": "sv-SE,sv;q=0.9,en;q=0.8",
}

RAW_ARCHIVE_DIR = Path(__file__).resolve().parent.parent / "data" / "fi_raw"
_RETRY_ATTEMPTS = 3          # retry+backoff (repo-mönster, se universe_mapping)
_RETRY_BACKOFF = 3           # sekunder × försöksnummer
_PAGE_DELAY = 0.4            # sekunder mellan HTML-fallback-sidor (rate limiting)

# Nyckelord för att klassificera köp vs sälj (sv + en MAR-kategorier).
# Verifierade karaktärer i CSV-exporten 2026-08-28: Acquisition, Allotment,
# Disposal, Exercise decrease, Exercise increase, Internal transaction –
# Acquisition/Disposal, Subscription (+ svenska motsvarigheter).
_BUY_KEYWORDS = [
    "förvärv", "köp", "tilldelning", "teckning", "konvertering",
    "acquisition", "allotment", "subscription", "exercise increase",
    "internal transaction – acquisition", "internal transaction - acquisition",
]
_SELL_KEYWORDS = [
    "avyttring", "försäljning", "sälj",
    "disposal", "exercise decrease",
    "internal transaction – disposal", "internal transaction - disposal",
]

# Kolumnnamn → kanonisk nyckel (hanterar både sv och en-GB CSV/HTML).
_HEADER_ALIASES = {
    "publiceringsdatum": "pub_date",
    "publication date": "pub_date",
    "emittent": "issuer",
    "issuer": "issuer",
    "lei-kod": "lei",
    "lei-code": "lei",
    "anmälningsskyldig": "notifier",
    "notifier": "notifier",
    "person i ledande ställning": "name",
    "person discharging managerial responsibilities": "name",
    "befattning": "role",
    "position": "role",
    "närstående": "closely_associated",
    "closely associated": "closely_associated",
    "korrigering": "amendment",
    "amendment": "amendment",
    "karaktär": "karaktar",
    "nature of transaction": "karaktar",
    "instrumenttyp": "instrument_type",
    "instrument type": "instrument_type",
    "intrument type": "instrument_type",   # FI:s stavfel i en-GB-exporten
    "instrumentnamn": "instrument_name",
    "instrument name": "instrument_name",
    "isin": "isin",
    "transaktionsdatum": "trade_date",
    "transaction date": "trade_date",
    "volym": "shares",
    "volume": "shares",
    "volymsenhet": "unit",
    "unit": "unit",
    "pris": "price",
    "price": "price",
    "valuta": "currency",
    "currency": "currency",
    "handelsplats": "venue",
    "trading venue": "venue",
    "status": "status",
}


def _norm_header(h: str) -> str:
    """Normalisera rubrik för alias-matchning (lowercase, kollapsa mellanslag)."""
    return re.sub(r"\s+", " ", (h or "").strip().lower())


# ─── Parsning ─────────────────────────────────────────────────────────────────

def parse_fi_csv(content: bytes) -> list[dict]:
    """Parse FI CSV-export (UTF-16-LE, semikolonseparerad) → råa rader.

    Returnerar dicts med kanoniska nycklar (isin, name, karaktar, shares,
    trade_date, status, …). shares/price konverteras till float med rätt
    decimalformat per språk (sv CSV = komma-decimal, en-GB = punkt-decimal).
    Tomt fönster → header-only → [].
    """
    text = content.decode("utf-16-le", errors="replace")
    if text.startswith("\ufeff"):
        text = text[1:]
    try:
        dialect = csv.Sniffer().sniff(text[:2000], delimiters=";,\t")
    except csv.Error:
        dialect = csv.excel
        dialect.delimiter = ";"
    rows = list(csv.reader(io.StringIO(text), dialect))
    if not rows:
        return []
    header = [_norm_header(h) for h in rows[0]]
    col_map = _build_col_map(header)
    # sv-exporten använder komma som decimalavgränsare ('20000,0', '7,00926');
    # en-GB-exporten punkt ('20000.0'). Detekteras på rubrikspråket.
    decimal_comma = "publiceringsdatum" in header
    data: list[dict] = []
    for r in rows[1:]:
        if not any(c.strip() for c in r):
            continue
        rec = {}
        for key, i in col_map.items():
            if i < len(r):
                val = r[i].strip()
                if key in ("shares", "price"):
                    val = _parse_float(val, decimal_comma=decimal_comma)
                rec[key] = val
        data.append(rec)
    return data


def _parse_fi_html(html: str) -> list[dict]:
    """Parse FI HTML-tabell (fallback) → råa rader (kanoniska nycklar)."""
    rows: list[dict] = []
    try:
        from bs4 import BeautifulSoup as BS
        soup = BS(html, "html.parser")
        table = soup.find("table")
        if not table:
            return rows
        col_map = _build_col_map([th.get_text(strip=True) for th in table.find_all("th")])
        for tr in table.find_all("tr")[1:]:
            tds = tr.find_all("td")
            if not tds:
                continue
            row = {}
            for key, i in col_map.items():
                if i < len(tds):
                    val = tds[i].get_text(strip=True)
                    # sv HTML-tabellen: NBSP-tusentalsavgränsare ('20 000')
                    # + komma-decimal ('2,79') — samma format som sv-CSV.
                    if key in ("shares", "price"):
                        val = _parse_float(val, decimal_comma=True)
                    row[key] = val
            if row:
                rows.append(row)
    except ImportError:
        logger.warning("BeautifulSoup not installed for HTML fallback")
    except Exception as e:
        logger.warning("HTML parsing failed: %s", e)
    return rows


def _build_col_map(header_row: list[str]) -> dict[str, int]:
    """Rubrikrad → {kanonisk nyckel: kolumnindex} (okända kolumner skippas)."""
    col_map: dict[str, int] = {}
    for i, h in enumerate(header_row):
        key = _HEADER_ALIASES.get(_norm_header(h))
        if key:
            col_map[key] = i
    return col_map


# ─── Hämtning ─────────────────────────────────────────────────────────────────

def fetch_csv_export(from_date: str, to_date: str) -> list[dict]:
    """Hämta FI-registret via CSV-export (primär väg, verifierad live).

    Retry+backoff (3 försök). Kastar RuntimeError om exporten inte går att
    hämta (transportfel/formatändring) — anroparen faller tillbaka till HTML.
    """
    params = {
        "SearchFunctionType": "Insyn",
        "Publiceringsdatum.From": from_date,
        "Publiceringsdatum.To": to_date,
        "button": "export",
        "Page": 1,
    }
    last_err: Exception | None = None
    for attempt in range(_RETRY_ATTEMPTS):
        try:
            resp = requests.get(FI_SEARCH_URL, params=params, headers=FI_HEADERS, timeout=60)
            if resp.status_code != 200:
                raise requests.RequestException(f"HTTP {resp.status_code}")
            ctype = resp.headers.get("Content-Type", "")
            if "text/csv" not in ctype:
                raise requests.RequestException(
                    f"oväntad Content-Type {ctype!r} — CSV-exporten ändrad?"
                )
            return parse_fi_csv(resp.content)
        except requests.RequestException as e:
            last_err = e
            logger.warning("FI CSV-export misslyckades (försök %d/%d): %s",
                           attempt + 1, _RETRY_ATTEMPTS, e)
            time.sleep(_RETRY_BACKOFF * (attempt + 1))
    raise RuntimeError(f"FI CSV-export misslyckades efter {_RETRY_ATTEMPTS} försök: {last_err}")


def fetch_html_search(from_date: str, to_date: str) -> list[dict]:
    """Hämta FI-registret via HTML-sök (ENDAST fallback vid transportfel).

    Paginerad (10 rader/sida; PageSize ignoreras av FI). Avbryter vid tom
    sida eller upprepad sida (dedup-detektor).
    """
    params = {
        "SearchFunctionType": "Insyn",
        "Publiceringsdatum.From": from_date,
        "Publiceringsdatum.To": to_date,
        "button": "search",
    }
    all_rows: list[dict] = []
    seen_keys: set[tuple] = set()
    page = 1
    while True:
        try:
            resp = requests.get(FI_SEARCH_URL_HTML, params={**params, "Page": page},
                                headers=FI_HEADERS, timeout=40)
            if resp.status_code != 200:
                raise requests.RequestException(f"HTTP {resp.status_code}")
            rows = _parse_fi_html(resp.text)
        except requests.RequestException as e:
            logger.warning("FI HTML-sök misslyckades (page %d): %s", page, e)
            break
        if not rows:
            break
        page_keys = {(r.get("pub_date", ""), r.get("isin", ""), r.get("name", "")) for r in rows}
        if page_keys <= seen_keys:
            break
        seen_keys |= page_keys
        all_rows.extend(rows)
        page += 1
        time.sleep(_PAGE_DELAY)
    return all_rows


def fetch_register(from_date: str, to_date: str) -> dict:
    """Hämta alla transaktioner i ett datumintervall.

    CSV-export primär; HTML-sök ENDAST fallback vid transportfel.
    Returnerar {"trades": [råa rader], "path": "csv"|"html"}.
    """
    try:
        rows = fetch_csv_export(from_date, to_date)
        logger.info("FI CSV-export: %d råa rader (%s → %s)", len(rows), from_date, to_date)
        return {"trades": rows, "path": "csv"}
    except Exception as e:
        logger.warning("CSV-export misslyckades — faller tillbaka till HTML-sök: %s", e)
        rows = fetch_html_search(from_date, to_date)
        logger.info("FI HTML-sök (fallback): %d råa rader (%s → %s)", len(rows), from_date, to_date)
        return {"trades": rows, "path": "html"}


def ping_search_page() -> bool:
    """Pinga FI-söksidan utan filter — bevis på levande endpoint (0-rader-fallet)."""
    try:
        resp = requests.get(FI_SEARCH_URL_HTML,
                            params={"SearchFunctionType": "Insyn", "button": "search"},
                            headers=FI_HEADERS, timeout=40)
        ok = resp.status_code == 200
        logger.info("FI-söksidan ping: HTTP %d (%s)", resp.status_code,
                    "levande" if ok else "avvikande")
        return ok
    except Exception as e:
        logger.warning("FI-söksidan ping misslyckades: %s", e)
        return False


# ─── Normalisering ────────────────────────────────────────────────────────────

def _classify_transaction(karaktar: str) -> str:
    """Klassificera transaktionstyp baserat på FI:s karaktär (sv + en)."""
    karaktar_lower = (karaktar or "").lower()
    for kw in _BUY_KEYWORDS:
        if kw in karaktar_lower:
            return "buy"
    for kw in _SELL_KEYWORDS:
        if kw in karaktar_lower:
            return "sell"
    return "unknown"


def _parse_float(val, decimal_comma: bool = False) -> Optional[float]:
    """Parse numeriskt fält.

    decimal_comma=True (sv CSV): komma = decimalavgränsare ('20000,0',
    '7,00926'). decimal_comma=False (en-GB CSV / HTML): punkt = decimal,
    komma = tusentalsavgränsare ('20,000'). Redan numeriska värden (från
    parsern) returneras oförändrade.
    """
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip().replace("\u00a0", "").replace(" ", "")
    if not s:
        return None
    if decimal_comma:
        s = s.replace(",", ".")
    elif "," in s and "." in s:
        # sista separatorn är decimalavgränsare
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        s = s.replace(",", "")   # tusentalsavgränsare (HTML)
    try:
        return float(s)
    except (ValueError, TypeError):
        return None


def _parse_date(val) -> Optional[str]:
    """Parse datumfält — hanterar sv ISO ('2026-08-25 00:00:00') och
    en-GB ('25/08/2026 00:00:00' / '25/08/2026')."""
    if not val:
        return None
    s = str(val).strip()
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    m = re.match(r"(\d{2})/(\d{2})/(\d{4})", s)
    if m:
        return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
    return None


def _normalize_status(val) -> str:
    """Status → 'current'|'revised'|'history' (sv + en)."""
    v = (val or "").strip().lower()
    if v in ("historik", "history"):
        return "history"
    if v in ("reviderad", "revised"):
        return "revised"
    return "current"


def normalize_transaction(raw: dict) -> Optional[dict]:
    """Normalisera en FI-transaktion (CSV/HTML-rad) till vårt schema.

    History-rader → None (skippas). Returnerar dict med isin, issuer, name,
    role, type, shares, price, amount, trade_date, status.
    """
    try:
        status = _normalize_status(raw.get("status"))
        if status == "history":
            return None
        trade = {
            "isin": raw.get("isin") or "",
            "issuer": raw.get("issuer") or "",
            "name": raw.get("name") or "",
            "role": raw.get("role") or "",
            "type": _classify_transaction(raw.get("karaktar") or ""),
            "shares": _parse_float(raw.get("shares")),
            "price": _parse_float(raw.get("price")),
            "amount": None,
            "trade_date": _parse_date(raw.get("trade_date")),
            "status": status,
        }
        # FI-exporten har inget beloppsfält — amount = volym × pris
        if trade["amount"] is None and trade["shares"] and trade["price"]:
            trade["amount"] = trade["shares"] * trade["price"]
        if not trade["isin"] or not trade["trade_date"]:
            return None
        return trade
    except Exception as e:
        logger.debug("Skipping row due to parse error: %s", e)
        return None


def aggregate_trades(trades: list[dict]) -> list[dict]:
    """Aggregera per (COALESCE(isin, ticker), name, trade_date, type).

    - History-rader skippas (aldrig aggregerade/upsertade)
    - Revised-rader överskriver Current-rader för samma nyckel (korrigering)
    - Delad volym → SUM(shares), SUM(amount)
    """
    groups: dict[tuple, list[dict]] = {}
    for t in trades:
        if (t.get("status") or "").lower() in ("history", "historik"):
            continue
        key = (
            t.get("isin") or t.get("ticker") or "",
            (t.get("name") or "").strip(),
            t.get("trade_date"),
            t.get("type"),
        )
        groups.setdefault(key, []).append(t)

    out: list[dict] = []
    for rows in groups.values():
        revised = [r for r in rows if (r.get("status") or "").lower() in ("revised", "reviderad")]
        chosen = revised if revised else rows
        base = dict(chosen[0])
        base["shares"] = sum(r.get("shares") or 0 for r in chosen) or None
        base["amount"] = sum(r.get("amount") or 0 for r in chosen) or None
        out.append(base)
    return out


# ─── DB ───────────────────────────────────────────────────────────────────────

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


def upsert_trades(trades: list[dict], conn) -> dict:
    """Upsert till insider_trades (migration-049-semantik).

    Mappar ISIN→ticker via company_profiles (unmapped → loggas, skippas),
    aggregerar per (COALESCE(isin, ticker), name, trade_date, type), och
    upsertar med ON CONFLICT på insider_trades_reconcile_key-indexet.
    Revised-rader överskriver (DO UPDATE); History skippas i normalize.
    """
    if not trades:
        logger.warning("Inga trades att upsert — 0-rader!")
        return {"inserted": 0, "unmapped": 0, "aggregated": 0}

    cur = conn.cursor()
    unmapped: list[dict] = []
    mapped: list[dict] = []

    for trade in trades:
        ticker = _map_isin_to_ticker(trade["isin"], conn)
        if not ticker and trade.get("issuer"):
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
        t = dict(trade)
        t["ticker"] = ticker
        mapped.append(t)

    aggregated = aggregate_trades(mapped)

    inserted = 0
    for trade in aggregated:
        try:
            cur.execute("""
                INSERT INTO insider_trades (ticker, name, trade_date, type, shares, price, amount, isin, role)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (COALESCE(isin, ticker), name, trade_date, type) DO UPDATE SET
                    shares = EXCLUDED.shares,
                    price = EXCLUDED.price,
                    amount = EXCLUDED.amount,
                    isin = EXCLUDED.isin,
                    role = EXCLUDED.role,
                    name = EXCLUDED.name
            """, (
                trade["ticker"], trade["name"], trade["trade_date"], trade["type"],
                trade["shares"], trade["price"], trade["amount"],
                trade["isin"], trade["role"],
            ))
            inserted += 1
        except Exception as e:
            logger.warning("Upsert failed for %s/%s: %s",
                           trade.get("ticker"), trade.get("trade_date"), e)

    conn.commit()

    if unmapped:
        log_path = RAW_ARCHIVE_DIR / f"unmapped_{datetime.now().strftime('%Y%m%d')}.json"
        log_path.write_text(json.dumps(unmapped, indent=2, ensure_ascii=False), encoding="utf-8")
        logger.warning("%d unmapped trades logged to %s", len(unmapped), log_path.name)

    logger.info("Upserted %d/%d trades (%d unmapped, %d aggregerade)",
                inserted, len(trades), len(unmapped), len(aggregated))
    return {"inserted": inserted, "unmapped": len(unmapped), "aggregated": len(aggregated)}


# ─── CLI ──────────────────────────────────────────────────────────────────────

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

    # Hämta (CSV primär, HTML fallback vid transportfel)
    try:
        result = fetch_register(from_date, to_date)
    except Exception as e:
        logger.error("FI-hämtning misslyckades (hårdfel): %s", e)
        print(json.dumps({"status": "error", "message": str(e)}))
        sys.exit(1)

    raw_trades = result["trades"]
    path = result["path"]
    logger.info("Hämtade %d råa rader via %s", len(raw_trades), path)

    # 0-rader: varning + empty_ok + ping (bevis på levande endpoint)
    if not raw_trades:
        logger.warning(
            "FI-registret returnerade 0 rader för %s → %s (via %s). "
            "Pingar söksidan utan filter för att bevisa levande endpoint.",
            from_date, to_date, path,
        )
        alive = ping_search_page()
        print(json.dumps({
            "status": "ok", "rows": 0, "empty_ok": True,
            "path": path, "endpoint_alive": alive,
        }))
        return

    # Spara rått arkiv (råa rader — återspelbara)
    archive_key = f"{from_date}_{to_date}"
    save_raw_archive(raw_trades, archive_key)

    # Normalisera → upsert
    trades = [n for n in (normalize_transaction(r) for r in raw_trades) if n is not None]
    logger.info("Normaliserade %d/%d rader", len(trades), len(raw_trades))

    # DB-uppladdning
    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        try:
            import psycopg2
            conn = psycopg2.connect(database_url)
            stats = upsert_trades(trades, conn)
            conn.close()
        except Exception as e:
            logger.error("DB-uppladdning misslyckades: %s", e)
            print(json.dumps({"status": "error", "message": str(e), "trades": len(trades)}))
            sys.exit(1)
    else:
        logger.warning("DATABASE_URL not set — skipping DB upsert")
        stats = {"inserted": 0, "unmapped": 0, "aggregated": 0}

    result_out = {
        "status": "ok",
        "from_date": from_date,
        "to_date": to_date,
        "path": path,
        "rows_fetched": len(raw_trades),
        "trades_normalized": len(trades),
        "trades_inserted": stats["inserted"],
        "unmapped": stats["unmapped"],
        "aggregated": stats["aggregated"],
    }
    print(json.dumps(result_out))
    logger.info("FI-bulk-ingestion klar: %d trades", len(trades))


if __name__ == "__main__":
    main()