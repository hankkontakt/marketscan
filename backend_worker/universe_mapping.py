"""
universe_mapping.py — Leverantörsagnostiskt nordiskt universumsregister.

FI:s marknadssök (insynsregister) är SANNINGEN om vilka bolag som är listade;
Yahoo-tickern är bara en derivat-nyckel (ZinZino-fallet: Yahoo säger delisted
medan bolaget fortfarande står i FI-registret).

Verifierad källväg (2026-08-28): marknadssök.fi.se GET /Search ger HTML med
insynstabellen — DET ÄR DEN ENDA FUNGERANDE VÄGEN (format=json-parametern
ignoreras; GetSearchResult = 404). Endpointen rate-limitar hårt → sleeps.
Ingen separat "Emittent"-lista finns — emittenthärledning sker via unika
(ISIN, Emittent)-par ur insynstabellen (90 dagars fönster).

Användning:
    python -m backend_worker.universe_mapping --dry-run   # hämta/analysera utan DB
    python -m backend_worker.universe_mapping             # skriv till DB
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
import time
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

import requests

logger = logging.getLogger(__name__)

FI_SEARCH_URL = "https://marknadssok.fi.se/publiceringsklient/sv/Search"
FI_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "sv-SE,sv;q=0.9,en;q=0.8",
}

RAW_ARCHIVE_DIR = Path(__file__).resolve().parent.parent / "data" / "fi_raw"
PROBE_CACHE_PATH = RAW_ARCHIVE_DIR / "yahoo_probe_cache.json"
PROBE_MAX_AGE_DAYS = 7
VERIFY_TO_DELISTED_DAYS = 14
WINDOW_DAYS = 180         # insynsfönster för emittenthärledning (bredare täckning)
PAGE_SIZE = 100
MAX_PAGES = 80            # 90 d fönster gav ~39 sidor; 180 d kan ge fler
PAGE_DELAY = 1.5          # sekunder — marknadssök är aggressivt rate-limitad

# Manuell seed för kända gap i ISIN→ticker-mappningen (utökas vid behov).
SEED_TICKERS: dict[str, str] = {}

_PAGE_RE = None  # lazy


def _archive_raw(filename: str, payload) -> None:
    RAW_ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    path = RAW_ARCHIVE_DIR / filename
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str),
                    encoding="utf-8")
    logger.info("Rått arkiv sparat: %s", path.name)


def _norm_name(name: str) -> str:
    n = (name or "").lower()
    n = re.sub(r"[^a-zåäö0-9 ]+", " ", n)
    n = n.replace("aktiebolag", " ").replace(" ab ", " ").replace(" publ ", " ")
    n = re.sub(r"\b(publ|holding|group)\b", " ", n)
    return re.sub(r"\s+", " ", n).strip()


def _parse_insyn_table(html: str) -> list[dict]:
    """Parse marknadssök-insynstabellen → råa rader (Emittent, ISIN, Person, ...)."""
    try:
        from bs4 import BeautifulSoup as BS
    except ImportError:
        logger.warning("BeautifulSoup saknas — kan inte parsea marknadssök")
        return []

    soup = BS(html, "html.parser")
    table = soup.find("table")
    if not table:
        return []

    headers = [th.get_text(strip=True) for th in table.find_all("th")]
    if not headers:
        return []

    rows = []
    for tr in table.find_all("tr"):
        cells = [td.get_text(strip=True) for td in tr.find_all("td")]
        if len(cells) != len(headers):
            continue
        rows.append(dict(zip(headers, cells)))
    return rows


def fetch_emittent_candidates() -> list[dict]:
    """Härled emittentkandidater ur FI-insynstabellen (90 d fönster, paginerad).

    Returnerar [{isin, name, source: 'insyn'}]. Tombet → [] (kalla är 0-rader-
    larm i main: formatändring).
    """
    from_date = (date.today() - timedelta(days=WINDOW_DAYS)).isoformat()
    candidates: dict[str, dict] = {}
    seen_rows: set[tuple] = set()
    empty_pages = 0

    for page in range(1, MAX_PAGES + 1):
        rows: list[dict] = []
        for attempt in range(3):   # marknadssök kastar ofta connectionen — backoff-retry
            try:
                resp = requests.get(
                    FI_SEARCH_URL,
                    params={
                        "SearchFunctionType": "Insyn",
                        "FromDate": from_date,
                        "ToDate": date.today().isoformat(),
                        "Page": page,
                        "PageSize": PAGE_SIZE,
                    },
                    headers=FI_HEADERS, timeout=40,
                )
                rows = _parse_insyn_table(resp.text)
                break
            except requests.RequestException as e:
                logger.warning("FI-anrop misslyckades (page %d, försök %d): %s", page, attempt + 1, e)
                time.sleep(backoff := 3 * (attempt + 1))
            except Exception as e:
                logger.warning("FI-parse fel (page %d): %s", page, e)
                time.sleep(backoff := 3 * (attempt + 1))

        if not rows:
            empty_pages += 1
            if empty_pages >= 5:
                logger.warning("5 tomma sidor i rad — avbryter paginering (delvis täckning OK)")
                break
            time.sleep(PAGE_DELAY)
            continue
        empty_pages = 0

        # Dedup-detektor: sidan återupprepar rader → slut
        page_keys = {
            (r.get("Publiceringsdatum", ""), r.get("ISIN", ""), r.get("Person", ""))
            for r in rows
        }
        if page_keys <= seen_rows:
            logger.info("Sida %d är en dubblett av tidigare rader — avslutar paginering", page)
            break
        seen_rows |= page_keys

        for r in rows:
            isin = (r.get("ISIN") or "").upper().strip()
            name = (r.get("Emittent") or "").strip()
            if not isin or not name:
                continue
            if isin not in candidates:
                candidates[isin] = {"isin": isin, "name": name, "source": "insyn"}

        logger.info("Sida %d: %d rader (unika emittenter hittills: %d)",
                    page, len(rows), len(candidates))
        time.sleep(PAGE_DELAY)

    return list(candidates.values())


# ─── Yahoo-probe (delisting-detektor, cachad 7 d) ─────────────────────────────

def _load_probe_cache() -> dict:
    try:
        if PROBE_CACHE_PATH.exists():
            return json.loads(PROBE_CACHE_PATH.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def _save_probe_cache(cache: dict) -> None:
    RAW_ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    PROBE_CACHE_PATH.write_text(json.dumps(cache, indent=2, ensure_ascii=False),
                                encoding="utf-8")


def probe_yahoo_ticker(ticker: str, cache: dict | None = None) -> bool:
    """True = Yahoo har priser (levande). Cachad 7 dagar."""
    cache = cache if cache is not None else _load_probe_cache()
    cutoff = (date.today() - timedelta(days=PROBE_MAX_AGE_DAYS)).isoformat()
    entry = cache.get(ticker)
    if entry and entry.get("probed_at", "") >= cutoff:
        return bool(entry.get("alive"))

    try:
        import yfinance as yf
        hist = yf.Ticker(ticker).history(period="5d")
        alive = bool(hist is not None and not hist.empty)
    except Exception:
        alive = False

    cache[ticker] = {"alive": alive, "probed_at": date.today().isoformat()}
    _save_probe_cache(cache)
    return alive


# ─── DB ───────────────────────────────────────────────────────────────────────

def _connect():
    import psycopg2
    return psycopg2.connect(os.environ["DATABASE_URL"])


def _map_isin_to_ticker(cur, isin: str) -> Optional[str]:
    if not isin:
        return None
    if isin.upper() in SEED_TICKERS:
        return SEED_TICKERS[isin.upper()]
    try:
        cur.execute("SELECT ticker FROM company_profiles WHERE isin = %s", (isin,))
        row = cur.fetchone()
        return row[0] if row else None
    except Exception:
        return None


def seed_from_existing(cur) -> list[dict]:
    """Seed-registerrader ur befintliga källor (company_profiles.isin + alla kända tickers).

    Tickers utan ISIN får syntetisk nyckel 'TXT:<ticker>' (ingen riktig ISIN
    existerar för den raden; dokumenteras i source='ticker_only').
    """
    rows: list[dict] = []
    try:
        cur.execute("SELECT ticker, isin FROM company_profiles WHERE isin IS NOT NULL AND isin <> ''")
        for ticker, isin in cur.fetchall():
            if isin and not isin.upper().startswith(("TXT:", "X-")):
                rows.append({"isin": isin.upper(), "ticker": ticker,
                             "name": ticker, "source": "company_profiles"})
    except Exception:
        pass

    try:
        cur.execute("SELECT DISTINCT ticker FROM scan_results WHERE ticker IS NOT NULL")
        for (ticker,) in cur.fetchall():
            if ticker and not ticker.startswith("X-"):
                rows.append({"isin": f"X-{ticker.upper()}", "ticker": ticker,
                             "name": ticker, "source": "ticker_only"})
    except Exception:
        pass

    try:
        cur.execute("SELECT DISTINCT ticker FROM smallcap_results WHERE ticker IS NOT NULL")
        for (ticker,) in cur.fetchall():
            if ticker and not ticker.startswith("X-"):
                rows.append({"isin": f"X-{ticker.upper()}", "ticker": ticker,
                             "name": ticker, "source": "ticker_only"})
    except Exception:
        pass
    return rows


def upsert_registry(candidates: list[dict]) -> dict:
    """Upsert kandidater + seed från befintliga källor."""
    conn = _connect()
    cur = conn.cursor()

    # 1. FI-härledda emittenter
    inserted = updated = unmapped = 0
    for c in candidates:
        isin = (c.get("isin") or "").upper()
        if not isin:
            continue
        ticker = _map_isin_to_ticker(cur, isin)
        if not ticker:
            unmapped += 1
        cur.execute("""
            INSERT INTO universe_registry (isin, ticker, orgnr, lei, name, source, updated_at)
            VALUES (%s, %s, NULL, NULL, %s, %s, NOW())
            ON CONFLICT (isin) DO UPDATE SET
                name = EXCLUDED.name,
                ticker = COALESCE(universe_registry.ticker, EXCLUDED.ticker),
                source = EXCLUDED.source,
                updated_at = NOW()
        """, (isin, ticker, c.get("name"), c.get("source", "insyn")))
        if cur.rowcount == 1:
            inserted += 1
        else:
            updated += 1

    # 2. Seed från befintliga källor (ticker-only → syntetisk nyckel)
    for s in seed_from_existing(cur):
        cur.execute("""
            INSERT INTO universe_registry (isin, ticker, orgnr, lei, name, source, updated_at)
            VALUES (%s, %s, NULL, NULL, %s, %s, NOW())
            ON CONFLICT (isin) DO UPDATE SET
                ticker = COALESCE(EXCLUDED.ticker, universe_registry.ticker),
                name = COALESCE(universe_registry.name, EXCLUDED.name),
                source = EXCLUDED.source,
                updated_at = NOW()
        """, (s["isin"], s.get("ticker"), s.get("name", s.get("ticker", "")), s["source"]))

    conn.commit()
    conn.close()
    return {"inserted": inserted, "updated": updated, "unmapped": unmapped}


def run_delisting_detector() -> dict:
    """Yahoo-presence för registry-tickers → listed/verify/delisted."""
    conn = _connect()
    cur = conn.cursor()
    cur.execute("SELECT isin, ticker, status, updated_at FROM universe_registry WHERE ticker IS NOT NULL")
    rows = cur.fetchall()

    cache = _load_probe_cache()
    stats = {"checked": 0, "listed_ok": 0, "to_verify": 0, "to_delist": 0}

    for isin, ticker, status, updated_at in rows:
        try:
            alive = probe_yahoo_ticker(ticker, cache)
        except Exception as e:
            logger.warning("Probe failed %s: %s", ticker, e)
            continue
        stats["checked"] += 1

        if alive:
            if status != "listed":
                cur.execute(
                    "UPDATE universe_registry SET status='listed', delisted_date=NULL WHERE isin=%s",
                    (isin,),
                )
                stats["listed_ok"] += 1
            continue

        if status == "listed":
            cur.execute("UPDATE universe_registry SET status='verify', updated_at=NOW() WHERE isin=%s", (isin,))
            stats["to_verify"] += 1
        elif status == "verify":
            since = updated_at or (date.today() - timedelta(days=VERIFY_TO_DELISTED_DAYS + 1))
            if isinstance(since, str):
                since = date.fromisoformat(since[:10])
            if (date.today() - since).days >= VERIFY_TO_DELISTED_DAYS:
                cur.execute(
                    "UPDATE universe_registry SET status='delisted', delisted_date=%s WHERE isin=%s",
                    (date.today().isoformat(), isin),
                )
                stats["to_delist"] += 1
                logger.warning("Delisted (verify > %d d): %s (%s)", VERIFY_TO_DELISTED_DAYS, ticker, isin)

    conn.commit()
    _save_probe_cache(cache)
    conn.close()
    return stats


def main():
    parser = argparse.ArgumentParser(description="Universe registry sync (FI truth + Yahoo mapping)")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    candidates = fetch_emittent_candidates()
    result = {
        "emittenter": len(candidates),
        "with_isin": sum(1 for c in candidates if c.get("isin")),
        "dry_run": args.dry_run,
    }
    logger.info("Hämtade %d emittentkandidater (%d med ISIN)", result["emittenter"], result["with_isin"])

    if not candidates:
        logger.error("0 emittenter — marknadssök-formatet kan ha ändrats; kontrollera rått arkiv.")
        print(json.dumps({"status": "error", **result}))
        sys.exit(1)

    _archive_raw("emittent_candidates.json", candidates)

    if args.dry_run:
        print(json.dumps({"status": "ok", "preview": candidates[:3], **result}))
        return

    if not os.environ.get("DATABASE_URL"):
        logger.warning("DATABASE_URL saknas — hoppar över DB-steg")
        print(json.dumps({"status": "ok-no-db", **result}))
        return

    try:
        ups = upsert_registry(candidates)
        det = run_delisting_detector()
        result.update({"registry": ups, "delisting": det})
        print(json.dumps({"status": "ok", **result}))
    except Exception as e:
        logger.error("DB-steg misslyckades: %s", e)
        print(json.dumps({"status": "error", "message": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
