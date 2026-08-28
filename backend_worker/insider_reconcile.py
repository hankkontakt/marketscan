"""
insider_reconcile.py — FI↔Finnhub kvalitetsgrind (coverage-first).

Jämför FI:s insynsregister (sanningskälla, marknadssok.fi.se) mot Finnhub
(korskälla) för de senaste 7 dagarna. FI-rader via fi_insider_bulk (fixad
CSV-export); Finnhub-rader via insider_fetcher._fetch_finnhub_insider per
ticker (universum = universe_registry status='listed').

Nyckel-normalisering (PURE, testbar):
    (isin, trade_date, abs(round(shares)), type_class)
där type_class = 'buy'|'sell' (FI-karaktärs-mappning → köp/sälj; Finnhub
change-koders mappning läses ur insider_fetcher). Rader aggregeras per
(isin, trade_date, type_class) → SUM(shares) innan jämförelse (delad volym
= en rad).

COVERAGE-FIRST:
    finnhub_coverage = tickers med ≥1 Finnhub-rad i fönstret / totalt.
    Suspicious-flagga sätts ENDAST vid PÅVISAD Finnhub-täckning: en
    finnhub_only-rad flaggas bara om tickern har ≥1 Finnhub-rad som INTE är
    finnhub_only (dvs. Finnhub-data för tickern överensstämmer med FI minst
    en gång i fönstret). Tickers utan Finnhub-rader flaggas aldrig.

Användning:
    python -m backend_worker.insider_reconcile --dry-run   # ingen DB-skrivning
    python -m backend_worker.insider_reconcile
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from datetime import date, timedelta

from backend_worker.fi_insider_bulk import (
    _BUY_KEYWORDS,
    _SELL_KEYWORDS,
    _parse_date as parse_fi_date,
    _parse_float as parse_fi_number,
    fetch_register,
)
from backend_worker.insider_fetcher import _fetch_finnhub_insider, _FINNHUB_DELAY

logger = logging.getLogger(__name__)

WORKER_STATE_KEY = "insider_reconcile_last_run"


# ─── PURE: normalisering ──────────────────────────────────────────────────────

def classify_fi_karaktar(karaktar: str) -> str:
    """FI-karaktär → 'buy'|'sell'|'unknown' (sv + en MAR-kategorier)."""
    k = (karaktar or "").lower()
    for kw in _BUY_KEYWORDS:
        if kw in k:
            return "buy"
    for kw in _SELL_KEYWORDS:
        if kw in k:
            return "sell"
    return "unknown"


def normalize_fi_row(row: dict) -> dict | None:
    """FI CSV/HTML-rad → {isin, trade_date, shares, type_class}.

    History-rader skippas. None om raden inte är nyckelbar (saknar isin,
    datum, volym eller klassificerbar karaktär).
    """
    status = (row.get("status") or "").strip().lower()
    if status in ("history", "historik"):
        return None
    isin = row.get("isin") or ""
    trade_date = parse_fi_date(row.get("trade_date"))
    shares = parse_fi_number(row.get("shares"))
    tc = classify_fi_karaktar(row.get("karaktar") or "")
    if not isin or not trade_date or shares is None or tc not in ("buy", "sell"):
        return None
    return {"isin": isin, "trade_date": trade_date, "shares": shares, "type_class": tc}


def normalize_finnhub_row(row: dict, isin_by_ticker: dict) -> dict | None:
    """Finnhub-rad (från insider_fetcher._fetch_finnhub_insider) → nyckelbar rad.

    Finnhub-rader saknar isin — ticker → isin via universe_registry-mappen.
    None om tickern saknar isin eller raden inte är nyckelbar.
    """
    ticker = row.get("ticker")
    isin = isin_by_ticker.get(ticker)
    trade_date = (row.get("trade_date") or "")[:10]
    shares = row.get("shares")
    tc = row.get("type")
    if not isin or not trade_date or shares is None or tc not in ("buy", "sell"):
        return None
    return {"isin": isin, "trade_date": trade_date, "shares": float(shares), "type_class": tc}


# ─── PURE: aggregering + jämförelse ───────────────────────────────────────────

def aggregate_shares(rows: list[dict]) -> dict[tuple, float]:
    """Aggregera per (isin, trade_date, type_class) → SUM(shares).

    Delad volym (samma person, flera rader samma dag) → en rad.
    """
    agg: dict[tuple, float] = {}
    for r in rows:
        key = (r["isin"], r["trade_date"], r["type_class"])
        agg[key] = agg.get(key, 0.0) + (r["shares"] or 0.0)
    return agg


def reconcile_key(isin: str, trade_date: str, shares: float, type_class: str) -> tuple:
    """Normaliserad jämförelsenyckel: (isin, trade_date, abs(round(shares)), type_class)."""
    return (isin, trade_date, abs(round(shares)), type_class)


def compare(fi_agg: dict[tuple, float], fh_agg: dict[tuple, float]) -> dict:
    """Jämför aggregerade FI- och Finnhub-rader.

    Returnerar {both, fi_only, finnhub_only, mismatches}:
      - both:         nyckel i BÅDA källorna
      - fi_only:      nyckel bara i FI
      - finnhub_only: nyckel bara i Finnhub
      - mismatches:   (isin, trade_date, type_class)-grupper i båda källorna
                      med olika abs(round(shares)) — samma transaktion,
                      volymavvikelse (listor av dicts med fi/finnhub-shares)
    """
    fi_keys = {reconcile_key(isin, d, s, tc) for (isin, d, tc), s in fi_agg.items()}
    fh_keys = {reconcile_key(isin, d, s, tc) for (isin, d, tc), s in fh_agg.items()}

    both = sorted(fi_keys & fh_keys)
    fi_only = sorted(fi_keys - fh_keys)
    finnhub_only = sorted(fh_keys - fi_keys)

    mismatches = []
    for g in sorted(fi_agg.keys() & fh_agg.keys()):
        if fi_agg[g] != fh_agg[g]:
            mismatches.append({
                "group": g,
                "fi_shares": fi_agg[g],
                "finnhub_shares": fh_agg[g],
            })

    return {"both": both, "fi_only": fi_only, "finnhub_only": finnhub_only,
            "mismatches": mismatches}


# ─── PURE: coverage-first ─────────────────────────────────────────────────────

def compute_coverage(fh_rows: list[dict], tickers: list[str]) -> tuple[int, int]:
    """(covered, total): tickers med ≥1 Finnhub-rad i fönstret / totalt."""
    covered = {r.get("ticker") for r in fh_rows if r.get("ticker")}
    return len(covered), len(tickers)


def proven_covered_tickers(compare_result: dict, isin_by_ticker: dict) -> set[str]:
    """Tickers med PÅVISAD Finnhub-täckning.

    En ticker har påvisad täckning om Finnhub har ≥1 rad som INTE är
    finnhub_only (dvs. en both- eller mismatch-rad — Finnhub-data för
    tickern överensstämmer med FI minst en gång i fönstret). En ticker vars
    enda Finnhub-rader är finnhub_only har ingen påvisad täckning.
    """
    ticker_by_isin = {v: k for k, v in isin_by_ticker.items()}
    proven_isins = {k[0] for k in compare_result["both"]}
    proven_isins |= {m["group"][0] for m in compare_result["mismatches"]}
    return {ticker_by_isin[i] for i in proven_isins if i in ticker_by_isin}


def flag_suspicious(compare_result: dict, covered_tickers: set[str],
                    isin_by_ticker: dict) -> list[dict]:
    """Suspicious-flaggor — ENDAST vid påvisad Finnhub-täckning.

    - finnhub_only-rad: flaggas om tickern har påvisad täckning (Finnhub
      täcker tickern men har en transaktion FI saknar).
    - mismatch: flaggas (volymavvikelse på täckt ticker).
    """
    ticker_by_isin = {v: k for k, v in isin_by_ticker.items()}
    # finnhub_only-rader som tillhör en mismatch-grupp täcks redan av
    # mismatch-flaggan (samma diskrepans ska inte flaggas två gånger).
    mismatch_groups = {m["group"] for m in compare_result["mismatches"]}
    flags: list[dict] = []
    for key in compare_result["finnhub_only"]:
        isin, d, shares, tc = key
        if (isin, d, tc) in mismatch_groups:
            continue
        ticker = ticker_by_isin.get(isin)
        if ticker in covered_tickers:
            flags.append({
                "kind": "finnhub_only",
                "isin": isin,
                "trade_date": d,
                "shares": shares,
                "type": tc,
                "ticker": ticker,
            })
    for m in compare_result["mismatches"]:
        isin, d, tc = m["group"]
        ticker = ticker_by_isin.get(isin)
        if ticker in covered_tickers:
            flags.append({
                "kind": "mismatch",
                "isin": isin,
                "trade_date": d,
                "type": tc,
                "ticker": ticker,
                "fi_shares": m["fi_shares"],
                "finnhub_shares": m["finnhub_shares"],
            })
    return flags


# ─── Orkestrering ─────────────────────────────────────────────────────────────

def run(from_date: str, to_date: str, api_key: str, dsn: str | None = None,
        dry_run: bool = False) -> dict:
    """Kör FI↔Finnhub-rekonciliering för fönstret [from_date, to_date].

    dry_run=True → ingen DB-skrivning (inte ens worker_state).
    """
    # 1. Universum: listed tickers + isin (universe_registry)
    tickers: list[str] = []
    isin_by_ticker: dict[str, str] = {}
    if dsn:
        import psycopg2
        conn = psycopg2.connect(dsn)
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT isin, ticker FROM universe_registry "
                "WHERE status = 'listed' AND ticker IS NOT NULL"
            )
            for isin, ticker in cur.fetchall():
                isin_by_ticker[ticker] = isin
                tickers.append(ticker)
        finally:
            conn.close()
    logger.info("Universum: %d listed tickers", len(tickers))

    # 2. FI-rader via fixad insamling (CSV-export primär)
    fi_result = fetch_register(from_date, to_date)
    fi_rows = [n for n in (normalize_fi_row(r) for r in fi_result["trades"]) if n]
    logger.info("FI: %d nyckelbara rader (via %s)", len(fi_rows), fi_result["path"])

    # 3. Finnhub-rader per ticker
    fh_raw: list[dict] = []
    for ticker in tickers:
        rows = _fetch_finnhub_insider(ticker, api_key, from_date)
        fh_raw.extend(rows)
        time.sleep(_FINNHUB_DELAY)
    fh_rows = [n for n in (normalize_finnhub_row(r, isin_by_ticker) for r in fh_raw) if n]
    logger.info("Finnhub: %d nyckelbara rader från %d tickers",
                len(fh_rows), len({r.get("ticker") for r in fh_raw}))

    # 4. Aggregera + jämför
    fi_agg = aggregate_shares(fi_rows)
    fh_agg = aggregate_shares(fh_rows)
    cmp = compare(fi_agg, fh_agg)

    # 5. Coverage-first
    covered, total = compute_coverage(fh_raw, tickers)
    proven = proven_covered_tickers(cmp, isin_by_ticker)
    suspicious = flag_suspicious(cmp, proven, isin_by_ticker)

    report = {
        "status": "ok",
        "window": {"from": from_date, "to": to_date},
        "fi_total": len(fi_agg),
        "finnhub_total": len(fh_agg),
        "both": len(cmp["both"]),
        "fi_only": len(cmp["fi_only"]),
        "finnhub_only": len(cmp["finnhub_only"]),
        "mismatches": len(cmp["mismatches"]),
        "finnhub_coverage": f"{covered}/{total}",
        "tickers_covered": covered,
        "tickers_total": total,
        "suspicious_count": len(suspicious),
        "suspicious": suspicious,
    }

    # 6. worker_state-sammanfattning (inte vid --dry-run)
    if dsn and not dry_run:
        import psycopg2
        conn = psycopg2.connect(dsn)
        try:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO worker_state (key, value, updated_at)
                VALUES (%s, %s, NOW())
                ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = NOW()
            """, (WORKER_STATE_KEY, json.dumps(report, ensure_ascii=False, default=str)))
            conn.commit()
        finally:
            conn.close()

    return report


def main():
    parser = argparse.ArgumentParser(description="FI↔Finnhub insider-rekonciliering")
    parser.add_argument("--days", type=int, default=7, help="Fönster i dagar (default: 7)")
    parser.add_argument("--from-date", type=str, help="Startdatum (YYYY-MM-DD)")
    parser.add_argument("--to-date", type=str, help="Slutdatum (YYYY-MM-DD)")
    parser.add_argument("--dry-run", action="store_true", help="Ingen DB-skrivning")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    to_date = args.to_date or date.today().isoformat()
    from_date = args.from_date or (date.today() - timedelta(days=args.days)).isoformat()

    api_key = os.environ.get("FINNHUB_API_KEY", "")
    if not api_key:
        logger.error("FINNHUB_API_KEY saknas")
        print(json.dumps({"status": "error", "message": "FINNHUB_API_KEY not set"}))
        sys.exit(1)

    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        logger.error("DATABASE_URL saknas")
        print(json.dumps({"status": "error", "message": "DATABASE_URL not set"}))
        sys.exit(1)

    try:
        report = run(from_date, to_date, api_key, dsn, dry_run=args.dry_run)
    except Exception as e:
        logger.error("Rekonciliering misslyckades: %s", e)
        print(json.dumps({"status": "error", "message": str(e)}))
        sys.exit(1)

    print(json.dumps(report, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()