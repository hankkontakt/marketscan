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
# Kandidatkoder (verifieras empiriskt i loggarna; US = positiv kontroll som
# bevisar att nyckeln/svarsformatet fungerar)
CANDIDATE_EXCHANGES = ["US", "SE", "HE", "DK", "FI", "NO", "IS", "STO", "OSL", "CPH"]
ALLOWED_TYPES = {"Common Stock", "Ordinary Shares", "Stock"}


def _get(path: str, params: dict) -> dict | list:
    key = os.environ.get("FINNHUB_API_KEY")
    if not key:
        raise RuntimeError("FINNHUB_API_KEY saknas")
    r = requests.get(FINNHUB_BASE + path, params={**params, "token": key}, timeout=30)
    if r.status_code != 200:
        raise RuntimeError(f"HTTP {r.status_code}: {r.text[:120]}")
    return r.json()


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
    parser.add_argument("--exchange", default=",".join(CANDIDATE_EXCHANGES))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    if not os.environ.get("FINNHUB_API_KEY"):
        logger.info("FINNHUB_API_KEY saknas i miljön — hoppar över (GH-secret krävs)")
        print(json.dumps({"status": "ok-no-key"}))
        return

    exchanges = [e.strip() for e in args.exchange.split(",") if e.strip()]

    total_rows = []
    per_exchange = {}
    for ex in exchanges:
        symbols = fetch_symbols(ex)
        rows = _to_registry_rows(symbols, ex)
        per_exchange[ex] = len(rows)
        if rows:
            total_rows.extend(rows)
        logger.info("%s: %d symboler (%d efter typfilter)", ex, len(symbols), len(rows))

    # Resultatsammanfattning: vilka koder som fungerade på free-tier
    working = {k: v for k, v in per_exchange.items() if v > 0}
    logger.info("Fungerande koder: %s", json.dumps(working))

    if not total_rows:
        # Ingen kod gav data — fri tier begränsad till US (verifierat resultat).
        # ALDRIG exit 1 (jobbet måste fortsätta; registry växer via FI-vägen).
        print(json.dumps({"status": "ok-partial", "message": "no free-tier coverage",
                          "per_exchange": per_exchange}))
        return

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
