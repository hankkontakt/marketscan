"""
finnhub_universe.py — Komplett ticker-universum via Finnhub /stock/symbol
(exchange-listor). Verifieras live i workflow-loggarna (FINNHUB_API_KEY finns
i GH-secrets).

Steg:
  1. Hämta stödda exchanges via /stock/exchange (listar kod + namn).
  2. Hämta symboler per nordisk exchange (SE/DK/FI/NO/IS + alternativkoder).
  3. Filtrera på typ (vanlig aktie), skriv som universe_registry-rader
     (syntetisk X-nyckel när ISIN saknas — mönstret finns sedan tidigare).

Användning:
    python -m backend_worker.finnhub_universe --dry-run          # räkna per exchange
    python -m backend_worker.finnhub_universe --exchange SE,DK,FI,NO
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys

import requests

logger = logging.getLogger(__name__)

FINNHUB_BASE = "https://finnhub.io/api/v1"
NORDIC_EXCHANGES = ["SE", "DK", "FI", "NO", "IS", "HE"]
ALLOWED_TYPES = {"Common Stock", "Ordinary Shares", "Stock"}


def _get(path: str, params: dict) -> dict:
    key = os.environ.get("FINNHUB_API_KEY")
    if not key:
        raise RuntimeError("FINNHUB_API_KEY saknas")
    r = requests.get(FINNHUB_BASE + path, params={**params, "token": key}, timeout=30)
    r.raise_for_status()
    return r.json()


def list_exchanges() -> list[dict]:
    try:
        return _get("/stock/exchange", {})
    except Exception as e:
        logger.warning("list_exchanges misslyckades: %s", e)
        return []


def fetch_symbols(exchange: str, limit: int = 5000) -> list[dict]:
    try:
        d = _get("/stock/symbol", {"exchange": exchange, "limit": limit})
        return d if isinstance(d, list) else []
    except Exception as e:
        logger.warning("fetch_symbols %s misslyckades: %s", exchange, e)
        return []


def _to_registry_rows(symbols: list[dict], exchange: str) -> list[dict]:
    rows = []
    for s in symbols:
        ttype = s.get("type") or ""
        if ttype and ttype not in ALLOWED_TYPES:
            continue
        ticker = s.get("symbol")
        desc = s.get("description") or s.get("name") or ""
        if not ticker:
            continue
        rows.append({
            "isin": s.get("isin") or f"X-{ticker.upper()}",
            "ticker": ticker,
            "name": desc,
            "source": f"finnhub:{exchange}",
        })
    return rows


def main():
    parser = argparse.ArgumentParser(description="Finnhub exchange-universum")
    parser.add_argument("--exchange", default=",".join(NORDIC_EXCHANGES))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    if not os.environ.get("FINNHUB_API_KEY"):
        logger.info("FINNHUB_API_KEY saknas i miljön — hoppar över (GH-secret krävs)")
        print(json.dumps({"status": "ok-no-key"}))
        return

    exchanges = [e.strip() for e in args.exchange.split(",") if e.strip()]
    available = {e.get("code"): e.get("name") for e in list_exchanges()}
    known = [e for e in exchanges if e in available]
    if not known:
        logger.warning("Inga kända exchange-koder bland: %s (tillgängliga: %s)",
                       exchanges, sorted(available.keys())[:40])
        print(json.dumps({"status": "error",
                          "message": "unknown exchanges",
                          "available": sorted(available.keys())[:40]}))
        sys.exit(1)

    total_rows = []
    per_exchange = {}
    for ex in known:
        symbols = fetch_symbols(ex)
        rows = _to_registry_rows(symbols, ex)
        per_exchange[ex] = len(rows)
        total_rows.extend(rows)
        logger.info("%s: %d symboler (%d efter typfilter)", ex, len(symbols), len(rows))

    if not total_rows:
        print(json.dumps({"status": "error", "message": "0 symboler",
                          "per_exchange": per_exchange}))
        sys.exit(1)

    if args.dry_run:
        print(json.dumps({
            "status": "ok", "per_exchange": per_exchange,
            "total": len(total_rows),
            "sample": total_rows[:3],
        }))
        return

    from backend_worker.universe_mapping import _connect
    conn = _connect()
    cur = conn.cursor()
    inserted = 0
    for r in total_rows:
        cur.execute("""
            INSERT INTO universe_registry (isin, ticker, name, source, updated_at)
            VALUES (%s, %s, %s, %s, NOW())
            ON CONFLICT (isin) DO UPDATE SET
                ticker = COALESCE(EXCLUDED.ticker, universe_registry.ticker),
                name = COALESCE(NULLIF(EXCLUDED.name, ''), universe_registry.name),
                source = EXCLUDED.source,
                updated_at = NOW()
        """, (r["isin"], r["ticker"], r["name"], r["source"]))
        inserted += 1
    conn.commit()
    conn.close()
    print(json.dumps({"status": "ok", "per_exchange": per_exchange,
                      "total": len(total_rows), "written": inserted}))


if __name__ == "__main__":
    main()
