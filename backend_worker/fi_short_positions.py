"""
fi_short_positions.py — Daglig hämtning av FI:s blankningsregister (net short positions).

Källa: https://www.fi.se/en/our-registers/net-short-positions/ — HTML-tabellen är
verifierat scrapbar (2026-08-28: 338 rader, LEI + total short %, realtid).
Excel-länkarna (Current/Historic/Aggregate) är JS-renderade — FALLBACK = HTML.

Varför: >0.1 % rapporteras till FI (aggregerat), >0.5 % publiceras med innehavare.
Jones m.fl. (2016): stora NYA disclosures → 90-d CAR ≈ −5 % → is_new_discovery.
Ashby (2024): naiva L/S-signaler har ingen edge → vi använder datan som
RISKFILTER, inte som standalone-signal.

Mappning: LEI → ISIN via per-emittentdetaljsida (verifierad 2026-08-28:
emittent?id=<LEI> innehåller ISIN). ISIN → ticker via universe_registry /
company_profiles. Lazy: max 25 detaljsidor/dag, cachad, prioritering på mest
blankade emittenter.

Cache-migrering 2026-08-29: LEI→ISIN-cachen flyttades från
data/fi_raw/lei_isin_cache.json till worker_state (key='lei_isin_cache',
JSONB). Lokalfilen var efemär i GH Actions (data/ är gitignored) → varje
körning började tom och ~300 LEI:s/körning fick ticker=NULL efter mappning
(radarn/QMJ-shortfiltret missade dem). Cachen ackumuleras nu över dagar;
lokalfilen läses fortfarande som read-only-fallback vid DB-fel.

Robusthet: 0-rader = formatändring → LARM (exit 1). Last-known-good behålls —
exklusioner rensas aldrig utifrån en tom fetch. Idempotent per (scan_date, lei).

Användning:
    python -m backend_worker.fi_short_positions --dry-run
    python -m backend_worker.fi_short_positions
"""
from __future__ import annotations

import argparse
import html as html_mod
import json
import logging
import os
import re
import sys
import time
from datetime import date
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

FI_REGISTER_URL = "https://www.fi.se/en/our-registers/net-short-positions/"
FI_DETAIL_URL = "https://www.fi.se/en/our-registers/net-short-positions/emittent"
FI_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-US,en;q=0.9,sv;q=0.8",
}

RAW_ARCHIVE_DIR = Path(__file__).resolve().parent.parent / "data" / "fi_raw"
LEI_ISIN_CACHE_PATH = RAW_ARCHIVE_DIR / "lei_isin_cache.json"
LEI_ISIN_CACHE_KEY = "lei_isin_cache"   # worker_state-nyckel (JSONB) sedan 2026-08-29
DETAIL_LIMIT_PER_RUN = 25      # detaljsidor (LEI→ISIN) per körning
DETAIL_DELAY = 1.2             # sekunder — fi.se rate-limitar
MAX_DAILY_ROWS = 2000
WORKER_STATE_KEY = "short_positions_last_ok"

# Seed-mappning för de MEST blankade emittenterna (riskfiltret behöver dessa NU;
# långsiktigt fylls mappningen av universe_registry/company_profiles).
_SEED_LEI_TICKER: dict[str, str] = {
    "5493008X1XZR4R5R0P66": "DYNVO.ST",   # Dynavox Group (9,7 % short, 2026-08-26)
    "549300BUD7ZPFPKM6856": "SMART.ST",   # Smart Eye (6,4 %)
    "254900UBKNY2EJ588J53": "SIVE.ST",    # Sivers Semiconductors (3,6 %)
}


# ─── Hämtning ─────────────────────────────────────────────────────────────────

def fetch_register_html() -> str:
    resp = requests.get(FI_REGISTER_URL, headers=FI_HEADERS, timeout=40)
    resp.raise_for_status()
    return resp.text


def _clean_cell(raw: str) -> str:
    txt = re.sub(r"<[^>]+>", "", raw)
    return html_mod.unescape(txt).strip()


def _to_float(val: str) -> float | None:
    """Robust float-parse: tusentalsavgränsare + decimal i sv- och en-format.

    - Mellanslag/NBSP tas bort ('1 234,56' → '1234,56').
    - Både komma och punkt → SISTA separatorn är decimalavgränsare (mönster
      från fi_insider_bulk._parse_float): '1,234.56' → 1234.56,
      '1.234,56' → 1234.56.
    - Annars nuvarande logik (komma → punkt, '%' tas bort).
    """
    v = val.strip().replace("%", "").replace("\u00a0", "").replace(" ", "")
    if "," in v and "." in v:
        if v.rfind(",") > v.rfind("."):
            v = v.replace(".", "").replace(",", ".")
        else:
            v = v.replace(",", "")
    else:
        v = v.replace(",", ".")
    v = re.sub(r"[^0-9.\-]", "", v)
    try:
        return float(v)
    except ValueError:
        return None


def _parse_date(val: str) -> str | None:
    m = re.search(r"(\d{4}-\d{2}-\d{2})", val)
    return m.group(1) if m else None


# Kolumnnamn (rubrikrad) → kanonisk nyckel (mönster från fi_insider_bulk.py).
# FI:s blankningsregister (en-GB, verifierat 2026-08-29): 'Issuer name',
# 'Issuer LEI code', 'Latest position date', 'Sum short %'. Svenska varianter
# som defensivt stöd (samma fyra kolumner).
_HEADER_ALIASES = {
    "issuer name": "issuer_name",
    "emittent": "issuer_name",
    "emittentnamn": "issuer_name",
    "issuer lei code": "lei",
    "lei": "lei",
    "lei code": "lei",
    "lei-kod": "lei",
    "latest position date": "latest_position_date",
    "position date": "latest_position_date",
    "datum": "latest_position_date",
    "date": "latest_position_date",
    "sum short %": "total_short_pct",
    "sum short": "total_short_pct",
    "total short %": "total_short_pct",
    "summa kort position": "total_short_pct",
    "summa kort position, %": "total_short_pct",
}


def _norm_header(h: str) -> str:
    """Normalisera rubrik för alias-matchning (lowercase, kollapsa mellanslag)."""
    return re.sub(r"\s+", " ", (h or "").strip().lower())


def _build_col_map(header_row: list[str]) -> dict[str, int]:
    """Rubrikrad → {kanonisk nyckel: kolumnindex} (okända kolumner skippas)."""
    col_map: dict[str, int] = {}
    for i, h in enumerate(header_row):
        key = _HEADER_ALIASES.get(_norm_header(h))
        if key:
            col_map[key] = i
    return col_map


def parse_register(html: str) -> list[dict]:
    """Parse FI-registret: rader [emittentnamn | LEI (20 tecken) | datum | summa short %].

    Kolumnmappning via rubrikradsnamn (header-aliaser, mönster från
    fi_insider_bulk.py). Positionellt index endast som fallback när
    rubrikraden saknas eller inte matchar kända alias.
    """
    rows: list[dict] = []
    row_re = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S | re.I)
    cell_re = re.compile(r"<t[dh][^>]*>(.*?)</t[dh]>", re.S | re.I)

    trs = row_re.findall(html)
    if not trs:
        return rows

    # Rubrikrad = första <tr> med <th>-celler → kolumnmappning på namn.
    col_map: dict[str, int] | None = None
    header_idx = -1
    for i, tr in enumerate(trs):
        if "<th" in tr.lower():
            header_cells = [_clean_cell(c) for c in cell_re.findall(tr)]
            col_map = _build_col_map(header_cells)
            header_idx = i
            break

    for i, tr in enumerate(trs):
        if i == header_idx:
            continue
        cells = [_clean_cell(c) for c in cell_re.findall(tr)]
        if col_map:
            keys = ("issuer_name", "lei", "latest_position_date", "total_short_pct")
            if any(k not in col_map for k in keys):
                continue
            if max(col_map[k] for k in keys) >= len(cells):
                continue
            name = cells[col_map["issuer_name"]]
            lei = cells[col_map["lei"]]
            date_val = cells[col_map["latest_position_date"]]
            pct_val = cells[col_map["total_short_pct"]]
        else:
            if len(cells) < 4:
                continue
            name, lei, date_val, pct_val = cells[0], cells[1], cells[2], cells[3]
        if not re.fullmatch(r"[A-Z0-9]{20}", lei.upper()):
            continue
        pct = _to_float(pct_val)
        if pct is None:
            continue
        rows.append({
            "issuer_name": name,
            "lei": lei.upper(),
            "latest_position_date": _parse_date(date_val),
            "total_short_pct": pct,
        })
    return rows[:MAX_DAILY_ROWS]


# ─── LEI→ISIN-anrikning (lazy, cachad) ────────────────────────────────────────

def _load_lei_isin_cache() -> dict:
    """Läs LEI→ISIN-cache från lokalfilen (READ-ONLY sedan 2026-08-29).

    Andra lagret — används som fallback vid DB-fel. Saknad/korrupt fil → {}.
    """
    try:
        if LEI_ISIN_CACHE_PATH.exists():
            return json.loads(LEI_ISIN_CACHE_PATH.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def _load_lei_cache(conn) -> dict:
    """Läs LEI→ISIN-cache från worker_state (key='lei_isin_cache').

    Primärt lager (migrerat från lokalfilen 2026-08-29 — data/ är gitignored
    och därmed efemär i GH Actions). Ingen rad → {} (standard). DB-fel →
    fallback till lokalfilen (read-only).
    """
    try:
        cur = conn.cursor()
        cur.execute("SELECT value FROM worker_state WHERE key = %s", (LEI_ISIN_CACHE_KEY,))
        row = cur.fetchone()
        if row:
            value = row[0]
            if isinstance(value, dict):
                return value
            if isinstance(value, str):
                parsed = json.loads(value)
                if isinstance(parsed, dict):
                    return parsed
        return {}
    except Exception as e:
        logger.warning("LEI-cache DB-läsning misslyckades — fallback till lokalfil: %s", e)
        return _load_lei_isin_cache()


def _save_lei_cache(conn, cache: dict) -> None:
    """Upsert LEI→ISIN-cache till worker_state (key='lei_isin_cache').

    Skrivs ALLTID till DB (lokalfilen är read-only sedan migreringen).
    """
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO worker_state (key, value, updated_at)
            VALUES (%s, %s, NOW())
            ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = NOW()
        """, (LEI_ISIN_CACHE_KEY, json.dumps(cache)))
        conn.commit()
    except Exception as e:
        logger.warning("LEI-cache DB-skrivning misslyckades: %s", e)


def fetch_lei_isin(lei: str) -> str | None:
    """Hämta ISIN för en LEI via FI:s emittentdetaljsida.

    ISIN:et kan vara uppdelat i flera elemenser — därför BeautifulSoup-text
    (verifierat 2026-08-28: detaljsidan innehåller 'SE0017769995').
    """
    try:
        resp = requests.get(FI_DETAIL_URL, params={"id": lei}, headers=FI_HEADERS, timeout=40)
        if resp.status_code != 200:
            return None
        from bs4 import BeautifulSoup as BS
        txt = BS(resp.text, "html.parser").get_text(" ")
        # ISIN = SE + 10 siffror (12 tecken totalt)
        m = re.search(r"\bSE\d{10}\b", txt)
        return m.group(0) if m else None
    except Exception:
        return None


def enrich_lei_to_isin(rows: list[dict], conn=None) -> dict:
    """Anrika rader utan känd ISIN: max DETAIL_LIMIT_PER_RUN detaljsidor, cachad.

    Prioriterar högst short % först — riskfiltret gäller de mest blankade.

    Cachen ligger i worker_state (key='lei_isin_cache'); lokalfilen är
    read-only-fallback vid DB-fel. conn=None → lokalfilen läses read-only
    (ingen skrivning sker — dry-run-vägen).
    """
    cache = _load_lei_cache(conn) if conn is not None else _load_lei_isin_cache()
    unknown = [r for r in rows if r["lei"] not in cache]
    unknown.sort(key=lambda r: r["total_short_pct"], reverse=True)

    fetched = 0
    for r in unknown:
        if fetched >= DETAIL_LIMIT_PER_RUN:
            break
        isin = fetch_lei_isin(r["lei"])
        cache[r["lei"]] = isin or ""
        time.sleep(DETAIL_DELAY)
        fetched += 1

    if conn is not None:
        _save_lei_cache(conn, cache)

    enriched = 0
    for r in rows:
        isin = cache.get(r["lei"]) or ""
        if isin:
            r["isin"] = isin
            enriched += 1
    return {"cached_known": len(cache), "fetched_now": fetched, "enriched": enriched}


# ─── DB ───────────────────────────────────────────────────────────────────────

def _connect():
    import psycopg2
    return psycopg2.connect(os.environ["DATABASE_URL"])


def _map_to_ticker(cur, lei: str, isin: str | None, issuer_name: str):
    """LEI→ticker (via registry.lei/seed), ISIN→ticker (registry/company_profiles),
    namn-fallback (normaliserad match). """
    if lei in _SEED_LEI_TICKER:
        return _SEED_LEI_TICKER[lei]
    try:
        cur.execute("SELECT ticker FROM universe_registry WHERE lei = %s", (lei,))
        row = cur.fetchone()
        if row and row[0]:
            return row[0]
        if isin:
            cur.execute("SELECT ticker FROM universe_registry WHERE isin = %s", (isin,))
            row = cur.fetchone()
            if row and row[0]:
                return row[0]
            cur.execute("SELECT ticker FROM company_profiles WHERE isin = %s", (isin,))
            row = cur.fetchone()
            if row and row[0]:
                return row[0]
    except Exception:
        pass

    # Namn-fallback mot registret (normaliserad)
    try:
        norm = _norm_name(issuer_name)
        if norm:
            cur.execute("SELECT ticker, name FROM universe_registry WHERE name IS NOT NULL AND ticker IS NOT NULL")
            for ticker, name in cur.fetchall():
                if _norm_name(name or "") == norm:
                    return ticker
    except Exception:
        pass

    # Nyckelfri yfinance-ISIN-lookup (samma kedja som universe_mapping)
    try:
        if isin:
            from backend_worker.universe_mapping import lookup_isin_via_yfinance
            symbol = lookup_isin_via_yfinance(isin)
            if symbol:
                return symbol
    except Exception:
        pass
    return None


def _norm_name(name: str) -> str:
    n = (name or "").lower()
    n = re.sub(r"[^a-zåäö0-9 ]+", " ", n)
    n = n.replace("aktiebolag", " ").replace(" ab ", " ").replace(" publ ", " ")
    n = re.sub(r"\b(publ|holding|group)\b", " ", n)
    return re.sub(r"\s+", " ", n).strip()


def upsert_positions(rows: list[dict], baseline_ok: bool = True) -> dict:
    conn = _connect()
    cur = conn.cursor()

    inserted = new_discoveries = mapped = 0

    for r in rows:
        cur.execute(
            "SELECT total_short_pct, scan_date FROM short_positions "
            "WHERE lei = %s AND scan_date < %s ORDER BY scan_date DESC LIMIT 1",
            (r["lei"], date.today().isoformat()),
        )
        prev = cur.fetchone()

        delta_pp = None
        is_new = False
        if prev:
            delta_pp = round(float(r["total_short_pct"]) - float(prev[0]), 3)
            prev_date = prev[1]
            if isinstance(prev_date, str):
                prev_date = date.fromisoformat(prev_date[:10])
            if (r["total_short_pct"] >= 0.5 and delta_pp >= 0.5
                    and (date.today() - prev_date).days <= 90):
                is_new = True
        else:
            # Ny LEI sedan vi började spåra (efter baslinje) → äkta "ny disclosure".
            # Baslinjen (första körningen någonsin) flaggas ALDRIG som ny —
            # den kontrolleras av worker_state-markören i main().
            is_new = bool(baseline_ok) and r["total_short_pct"] >= 0.5

        ticker = _map_to_ticker(cur, r["lei"], r.get("isin"), r["issuer_name"])
        if ticker:
            mapped += 1

        cur.execute("""
            INSERT INTO short_positions (
                scan_date, lei, ticker, issuer_name, total_short_pct,
                latest_position_date, is_new_discovery, delta_pp
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (scan_date, lei) DO UPDATE SET
                ticker = COALESCE(EXCLUDED.ticker, short_positions.ticker),
                total_short_pct = EXCLUDED.total_short_pct,
                latest_position_date = EXCLUDED.latest_position_date,
                is_new_discovery = EXCLUDED.is_new_discovery,
                delta_pp = EXCLUDED.delta_pp
        """, (
            date.today().isoformat(), r["lei"], ticker, r["issuer_name"],
            r["total_short_pct"], r["latest_position_date"], is_new, delta_pp,
        ))
        inserted += 1
        if is_new:
            new_discoveries += 1

    cur.execute("""
        INSERT INTO worker_state (key, value, updated_at)
        VALUES (%s, %s, NOW())
        ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = NOW()
    """, (WORKER_STATE_KEY, json.dumps({
        "scan_date": date.today().isoformat(),
        "rows": len(rows),
        "new_discoveries": new_discoveries,
    })))

    conn.commit()
    conn.close()
    return {"written": inserted, "new_discoveries": new_discoveries, "tickers_mapped": mapped}


def _has_prior_baseline() -> bool:
    """True om worker_state redan har en 'short_positions_last_ok'-markör från FÖREGÅENDE körning.

    Första körningen någonsin = baslinje → inga av dess rader är 'new discoveries'.
    """
    try:
        conn = _connect()
        cur = conn.cursor()
        cur.execute("SELECT updated_at FROM worker_state WHERE key = %s", (WORKER_STATE_KEY,))
        row = cur.fetchone()
        conn.close()
        if not row:
            return False
        ts = row[0]
        if isinstance(ts, str):
            ts = date.fromisoformat(ts[:10])
        elif hasattr(ts, "date"):          # TIMESTAMPTZ → datetime
            ts = ts.date()
        # Markören skrevs idag (samma körning eller manuell återkörning) → baslinje
        first_run_today = ts >= date.today()
        return not first_run_today
    except Exception:
        return True   # DB oåtkomlig → optimistisk (vi vill inte blockera allt)


def main():
    parser = argparse.ArgumentParser(description="FI net short position snapshot")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    html = fetch_register_html()
    rows = parse_register(html)

    if not rows:
        logger.error(
            "FI-blankningsregistret returnerade 0 rader — MISSTÄNKT (formatändring?). "
            "Last-known-good behålls; inga skrivningar utförs."
        )
        print(json.dumps({"status": "error", "message": "0 rows parsed", "rows": 0}))
        sys.exit(1)

    # LEI→ISIN-cache: DB (worker_state) på riktiga körningar; dry-run = read-only.
    conn = None
    if not args.dry_run and os.environ.get("DATABASE_URL"):
        try:
            conn = _connect()
        except Exception as e:
            logger.warning("DB-anslutning misslyckades — LEI-cache faller tillbaka till lokalfil: %s", e)

    try:
        enrich = enrich_lei_to_isin(rows, conn=conn)
    finally:
        if conn is not None:
            conn.close()

    logger.info("Parsade %d emittentrader; %s", len(rows),
                json.dumps({k: v for k, v in enrich.items()}))

    if args.dry_run:
        print(json.dumps({
            "status": "ok", "rows": len(rows), "enrichment": enrich,
            "preview": rows[:3],
        }))
        return

    if not os.environ.get("DATABASE_URL"):
        logger.warning("DATABASE_URL saknas — hoppar över DB-steg")
        print(json.dumps({"status": "ok-no-db", "rows": len(rows), "enrichment": enrich}))
        return

    try:
        stats = upsert_positions(rows, baseline_ok=_has_prior_baseline())
        print(json.dumps({"status": "ok", **stats}))
    except Exception as e:
        logger.error("DB-steg misslyckades: %s", e)
        print(json.dumps({"status": "error", "message": str(e), "rows": len(rows)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
