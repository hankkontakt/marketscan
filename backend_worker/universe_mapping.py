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
ISIN_SYMBOL_CACHE_PATH = RAW_ARCHIVE_DIR / "isin_symbol_cache.json"
PROBE_MAX_AGE_DAYS = 7
ISIN_SYMBOL_HIT_TTL = 60      # träff: 60 dagar (ticker byter sällan)
ISIN_SYMBOL_MISS_TTL = 14     # miss: 14 dagar (ny listning kan komma in senare)
VERIFY_TO_DELISTED_DAYS = 14
WINDOW_DAYS = 180         # insynsfönster för emittenthärledning (bredare täckning)
PAGE_SIZE = 100
MAX_PAGES = 80            # 90 d fönster gav ~39 sidor; 180 d kan ge fler
PAGE_DELAY = 1.5          # sekunder — marknadssök är aggressivt rate-limitad

# Manuell seed för kända gap i ISIN→ticker-mappningen (utökas vid behov).
# Verifierat 2026-08-28 med yfinance: "TAGM-B.ST" resolvar (TagMaster AB ser. B),
# "TAGM B.ST" gör det INTE ("possibly delisted"); "NCAB.ST" resolvar (NCAB Group AB).
SEED_TICKERS: dict[str, str] = {
    "SE0015671995": "NCAB.ST",
    "SE0015950399": "TAGM-B.ST",
}

SEED_NAMES: dict[str, str] = {
    "SE0015671995": "NCAB Group AB",
    "SE0015950399": "TagMaster AB",
}


def seed_ticker_for_isin(isin: Optional[str]) -> Optional[str]:
    """Pure seed-uppslag: ISIN (normaliserad till versaler) → ticker, eller None."""
    if not isin:
        return None
    return SEED_TICKERS.get(isin.upper())


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
                time.sleep(3 * (attempt + 1))
            except Exception as e:
                logger.warning("FI-parse fel (page %d): %s", page, e)
                time.sleep(3 * (attempt + 1))

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


# ─── Automatisk ISIN→ticker (keyless, via yfinance Lookup) ────────────────────
# NY:er linjer: IPO → insider-anmälan → ISIN i FI-registret → yf.Lookup(ISIN)
# → ticker → registry 'listed' → shorts/QMJ kedjan tar över automatiskt.

_NORDIC_VENUE_RE = re.compile(r"(\.ST|\.OL|\.HE|\.CO)$")


def _load_isin_symbol_cache() -> dict:
    try:
        if ISIN_SYMBOL_CACHE_PATH.exists():
            return json.loads(ISIN_SYMBOL_CACHE_PATH.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def _save_isin_symbol_cache(cache: dict) -> None:
    RAW_ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    ISIN_SYMBOL_CACHE_PATH.write_text(json.dumps(cache, indent=2, ensure_ascii=False),
                                      encoding="utf-8")


def lookup_finnhub_isin(isin: str) -> Optional[str]:
    """ISIN → ticker via Finnhub profile2?isin= (free tier; kräver FINNHUB_API_KEY).

    Verifierat i dokumentationen: 'You can input anything from symbol, security's
    name to ISIN and Cusip'. Guardad — utan nyckel returnerar den None.
    """
    key = os.environ.get("FINNHUB_API_KEY")
    if not key:
        return None
    try:
        r = requests.get(
            "https://finnhub.io/api/v1/profile2",
            params={"isin": isin, "token": key},
            timeout=15,
        )
        d = r.json()
        ticker = d.get("ticker") or d.get("symbol")
        return ticker if ticker else None
    except Exception:
        return None


def lookup_isin_via_yfinance(isin: str, cache: dict | None = None, force_refresh: bool = False) -> Optional[str]:
    """ISIN → Yahoo-ticker via yf.Lookup. Cachad (hit 60 d / miss 14 d). None vid miss.

    OBS: symbolen ligger i DataFrame-INDEX; shortName+industryName i kolumnerna
    (verifierat 2026-08-28: 'BioGaia AB ser. B' + 'Healthcare').
    """
    cache = cache if cache is not None else _load_isin_symbol_cache()
    now = date.today()
    entry = cache.get(isin)
    if entry and not force_refresh:
        # Gammalt format (utan 'name') är ofullständigt för backfill — behandla som miss.
        if not entry.get("name"):
            entry = None
        else:
            ttl = ISIN_SYMBOL_HIT_TTL if entry.get("symbol") else ISIN_SYMBOL_MISS_TTL
            if (now - date.fromisoformat(entry.get("ts", "2000-01-01"))).days <= ttl:
                return entry.get("symbol")

    symbol = name = sector = None
    try:
        import yfinance as yf
        df = yf.Lookup(isin).stock
        if df is not None and not df.empty:
            # Symbol i index (kolumnerna är t.ex. exchange/industryName)
            for sym in df.index:
                sym = str(sym)
                if sym and _NORDIC_VENUE_RE.search(sym):
                    symbol = sym
                    break
            if symbol:
                row = df.loc[symbol]
                if "shortName" in df.columns:
                    name = str(row.get("shortName")) if row.get("shortName") is not None else None
                if "industryName" in df.columns:
                    sector = str(row.get("industryName")) if row.get("industryName") is not None else None
    except Exception:
        pass

    cache[isin] = {"symbol": symbol, "name": name, "sector": sector,
                   "ts": now.isoformat()}
    _save_isin_symbol_cache(cache)
    return symbol


def _backfill_names_and_sectors(cur) -> int:
    """Namn/sektor-backfill ur yf.Lookup-cachen (X-rader har ticker som 'namn').

    Högvärdigt för namnmatch i nyhetskedjan + framtida sektorjämförelse.
    FORCERE FRESH: rader med sector IS NULL lyfts direkt via yf.Lookup
    (cache-uppdaterad) — annars når aldrig yf.Lookup pga gammal cache-format.
    """
    # 1) Sektornull-rader → forcereferesh cachen (kostar ~2-4 min en gång)
    # GH-runnern blockeras av Yahoo (query1-finance = 'possibly delisted'-fel);
    # hoppa över färska (<7 d) försök så vi inte bränner yf-anrop dagligen.
    try:
        cur.execute("SELECT isin FROM universe_registry WHERE sector IS NULL AND status = 'listed'")
        missing = [r[0] for r in cur.fetchall() if r[0]]
    except Exception:
        missing = []
    fresh_cache = _load_isin_symbol_cache()
    for isin in missing[:150]:
        entry = fresh_cache.get(isin)
        if entry and (date.today() - date.fromisoformat(entry.get("ts", "2000-01-01"))).days < 7:
            continue  # nyligen försökt (sannolikt Yahoo-block från GH) — spara minuter
        lookup_isin_via_yfinance(isin, force_refresh=True)
        fresh_cache = _load_isin_symbol_cache()
    # 2) Backfill ur (nu friskare) cachen
    cache = _load_isin_symbol_cache()
    filled = 0
    for isin, entry in cache.items():
        if not entry.get("name"):
            continue
        try:
            cur.execute("""
                UPDATE universe_registry
                SET name = %s, sector = COALESCE(sector, %s)
                WHERE isin = %s
                  AND (name IS NULL OR name ~ '^[A-Z0-9.\\-_]+$')
            """, (str(entry["name"]), entry.get("sector"), isin))
            filled += cur.rowcount or 0
        except Exception:
            continue
    return filled


def _connect():
    import psycopg2
    return psycopg2.connect(os.environ["DATABASE_URL"])


def _map_isin_to_ticker(cur, isin: str) -> Optional[str]:
    if not isin:
        return None
    seeded = seed_ticker_for_isin(isin)
    if seeded:
        return seeded
    try:
        cur.execute("SELECT ticker FROM company_profiles WHERE isin = %s", (isin,))
        row = cur.fetchone()
        if row and row[0]:
            return row[0]
    except Exception:
        pass
    # Nyckelfri fallback A: Finnhub (snabb, verifierad API-kontrakt; kräver GH-secret)
    sym_fh = lookup_finnhub_isin(isin)
    if sym_fh:
        return sym_fh
    # Nyckelfri fallback B: yfinance-ISIN-lookup ("ny listning"-kedjan)
    return lookup_isin_via_yfinance(isin)


# Nordic venue-suffixer — universumet är nordiska småbolag, inte finviz/US-skrapet
_NORDIC_SUFFIX_SQL = "(ticker LIKE '%.ST' OR ticker LIKE '%.OL' OR ticker LIKE '%.HE' OR ticker LIKE '%.CO')"


def seed_from_existing(cur) -> list[dict]:
    """Seed-registerrader ur befintliga källor — ENBART nordiska venue-suffix.

    Tickers utan ISIN får syntetisk nyckel 'TXT:<ticker>' (ingen riktig ISIN
    existerar för den raden; dokumenteras i source='ticker_only').
    """
    rows: list[dict] = []
    try:
        cur.execute("SELECT ticker, isin FROM company_profiles WHERE isin IS NOT NULL AND isin <> '' AND " + _NORDIC_SUFFIX_SQL)
        for ticker, isin in cur.fetchall():
            if isin and not isin.upper().startswith(("TXT:", "X-")):
                rows.append({"isin": isin.upper(), "ticker": ticker,
                             "name": ticker, "source": "company_profiles"})
    except Exception:
        pass

    try:
        cur.execute("SELECT DISTINCT ticker FROM scan_results WHERE ticker IS NOT NULL AND " + _NORDIC_SUFFIX_SQL)
        for (ticker,) in cur.fetchall():
            if ticker and not ticker.startswith("X-"):
                rows.append({"isin": f"X-{ticker.upper()}", "ticker": ticker,
                             "name": ticker, "source": "ticker_only"})
    except Exception:
        pass

    try:
        cur.execute("SELECT DISTINCT ticker FROM smallcap_results WHERE ticker IS NOT NULL AND " + _NORDIC_SUFFIX_SQL)
        for (ticker,) in cur.fetchall():
            if ticker and not ticker.startswith("X-"):
                rows.append({"isin": f"X-{ticker.upper()}", "ticker": ticker,
                             "name": ticker, "source": "ticker_only"})
    except Exception:
        pass

    # Seed-registerrader från SEED_TICKERS (användarens garanterade bolag, t.ex.
    # innehav som FI-poll-fönstret missat). Namn hämtas ur SEED_NAMES.
    for isin, ticker in SEED_TICKERS.items():
        rows.append({"isin": isin, "ticker": ticker,
                     "name": SEED_NAMES.get(isin, ticker), "source": "seed"})
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
            elif hasattr(since, "date"):          # TIMESTAMPTZ → datetime
                since = since.date()
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
        # Namn/sektor-backfill (X-rader → riktiga bolagsnamn från yf.Lookup-cachen)
        conn = _connect()
        cur = conn.cursor()
        backfilled = _backfill_names_and_sectors(cur)
        conn.commit()
        conn.close()
        det = run_delisting_detector()
        result.update({"registry": ups, "backfilled_names": backfilled,
                       "delisting": det})
        print(json.dumps({"status": "ok", **result}))
    except Exception as e:
        logger.error("DB-steg misslyckades: %s", e)
        print(json.dumps({"status": "error", "message": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
