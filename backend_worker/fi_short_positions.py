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
from datetime import date, timedelta
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
DETAIL_LIMIT_PER_RUN = 25      # detaljsidor (LEI→ISIN) per körning
DETAIL_DELAY = 1.2             # sekunder — fi.se rate-limitar
MAX_DAILY_ROWS = 2000
WORKER_STATE_KEY = "short_positions_last_ok"


# ─── Hämtning ─────────────────────────────────────────────────────────────────

def fetch_register_html() -> str:
    resp = requests.get(FI_REGISTER_URL, headers=FI_HEADERS, timeout=40)
    resp.raise_for_status()
    return resp.text


def _clean_cell(raw: str) -> str:
    txt = re.sub(r"<[^>]+>", "", raw)
    return html_mod.unescape(txt).strip()


def _to_float(val: str) -> float | None:
    v = val.strip().replace("%", "").replace(",", ".").replace("\u00a0", "")
    v = re.sub(r"[^0-9.\-]", "", v)
    try:
        return float(v)
    except ValueError:
        return None


def _parse_date(val: str) -> str | None:
    m = re.search(r"(\d{4}-\d{2}-\d{2})", val)
    return m.group(1) if m else None


def parse_register(html: str) -> list[dict]:
    """Parse FI-registret: rader [emittentnamn | LEI (20 tecken) | datum | summa short %]."""
    rows: list[dict] = []
    row_re = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S | re.I)
    cell_re = re.compile(r"<t[dh][^>]*>(.*?)</t[dh]>", re.S | re.I)

    for tr in row_re.findall(html):
        cells = [_clean_cell(c) for c in cell_re.findall(tr)]
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
    try:
        if LEI_ISIN_CACHE_PATH.exists():
            return json.loads(LEI_ISIN_CACHE_PATH.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def _save_lei_isin_cache(cache: dict) -> None:
    RAW_ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    LEI_ISIN_CACHE_PATH.write_text(json.dumps(cache, indent=2, ensure_ascii=False),
                                   encoding="utf-8")


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


def enrich_lei_to_isin(rows: list[dict]) -> dict:
    """Anrika rader utan känd ISIN: max DETAIL_LIMIT_PER_RUN detaljsidor, cachad.

    Prioriterar högst short % först — riskfiltret gäller de mest blankade.
    """
    cache = _load_lei_isin_cache()
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

    _save_lei_isin_cache(cache)

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
    """LEI→ticker (via registry.lei), ISIN→ticker (registry/company_profiles),
    namn-fallback (normaliserad match). """
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

    enrich = enrich_lei_to_isin(rows)
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
