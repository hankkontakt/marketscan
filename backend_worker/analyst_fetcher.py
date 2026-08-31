"""
analyst_fetcher.py — Analytikeruppsida (target price + rekommendation) per ticker.

KÄLLA (verifierad i .opencode/audit/datatest-yfinance.md):
  yfinance `.info`: targetMeanPrice (10/10), numberOfAnalystOpinions (10/10),
  recommendationMean (6/10), targetHighPrice, targetLowPrice, recommendationKey.
  Finnhub /stock/target-price + /recommend-trends är US-ONLY (audit
  datatest-nyckelberoende.md:97-98) — anropas därför bara som komplement för
  US-tickers (inget fallback för nordiska).

Skriver till analyst_estimates (migration 066). Körs fredag 04:15 UTC (efter QMJ).

Användning:
    python -m backend_worker.analyst_fetcher --limit-tickers 5
    python -m backend_worker.analyst_fetcher --dry-run
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import time
from datetime import date
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

FETCH_SLEEP = 1.2
TARGET_STALE_DAYS = 90      # target äldre än detta = STALE_TARGET-flagga
DEAD_TARGET_FACTOR = 2.0    # target > 2x spot = död riktkurs (DEAD_TARGET-flagga)


# ═════════════════════════ PURE CORE (testbar; ingen nätverk/DB) ══════════════

def extract_analyst(info: dict, price: Optional[float]) -> dict:
    """yfinance .info-dict → analyst_estimates-rad (råvärden, ingen DB).

    Riskanalys: värdet på upside percentilen gated av target_count — en enda
    analytiker får aldrig bära stor vikt. Död riktkurs (>2x spot) flaggas.
    """
    tgt_med = info.get("targetMeanPrice")
    tgt_high = info.get("targetHighPrice")
    tgt_low = info.get("targetLowPrice")
    cnt = info.get("numberOfAnalystOpinions")
    rec_mean = info.get("recommendationMean")
    rec_key = info.get("recommendationKey")

    if cnt is not None:
        try:
            cnt = int(cnt)
        except (TypeError, ValueError):
            cnt = None
    if tgt_med is not None:
        try:
            tgt_med = float(tgt_med)
        except (TypeError, ValueError):
            tgt_med = None
    if tgt_high is not None:
        try:
            tgt_high = float(tgt_high)
        except (TypeError, ValueError):
            tgt_high = None
    if tgt_low is not None:
        try:
            tgt_low = float(tgt_low)
        except (TypeError, ValueError):
            tgt_low = None
    if rec_mean is not None:
        try:
            rec_mean = float(rec_mean)
        except (TypeError, ValueError):
            rec_mean = None

    upside = None
    if tgt_med is not None and price and price > 0:
        upside = (tgt_med - price) / price

    flags: list[str] = []
    if cnt is not None and 0 < cnt < 3:
        flags.append("FEW_ANALYSTS")
    if upside is not None and upside > DEAD_TARGET_FACTOR:
        flags.append("DEAD_TARGET")
    if tgt_med is not None and price is not None and price > 0 and not (0.1 < tgt_med / price < DEAD_TARGET_FACTOR):
        flags.append("STALE_TARGET")

    rec_key_clean = rec_key if isinstance(rec_key, str) else None
    dispersion = None
    if tgt_med is not None and tgt_high is not None and tgt_low is not None and tgt_med > 0:
        dispersion = (tgt_high - tgt_low) / tgt_med
    return {
        "target_median": tgt_med,
        "target_high": tgt_high,
        "target_low": tgt_low,
        "target_count": cnt,
        "upside_pct": round(upside * 100, 2) if upside is not None else None,
        "recommendation_mean": rec_mean,
        "recommendation_key": rec_key_clean,
        "flags": flags,
        "target_dispersion": round(dispersion, 3) if dispersion is not None else None,
    }


def analyst_z(rec: dict) -> Optional[float]:
    """Analytiker-delscore 0-100. NULL om ingen data.

    Kernregel: vikt skalar med täckning (min(1, count/10)) — en analytiker ger
    max 10 % poäng. Upside percentilnormeras till 0-100 genom tanh med skala 0.35
    (35 % uppsida ≈ max utväxling) och kombineras med rekommendationen.
    """
    if not rec or (rec.get("upside_pct") is None and rec.get("recommendation_mean") is None):
        return None
    cnt = rec.get("target_count") or 0
    coverage = min(1.0, cnt / 10.0)
    upside = rec.get("upside_pct")
    rec_mean = rec.get("recommendation_mean")
    # psycopg2 NUMERIC → Decimal; casta till float för numpy-matematik
    try:
        upside = float(upside) if upside is not None else None
        rec_mean = float(rec_mean) if rec_mean is not None else None
    except (TypeError, ValueError):
        return None
    components: list[float] = []
    weights: list[float] = []
    if upside is not None:
        # tanh-skala: +35 % uppsida → ~0.75, -35 % nedside → ~-0.75.
        # OBS: negativa tanh-värden ** 1.1 blir komplexa — bevara tecken:
        # sign(x) * |x|^1.1 (x ∈ [-1,1]).
        t = float(np.tanh(upside / 35.0))
        components.append(np.sign(t) * (abs(t) ** 1.1))
        weights.append(0.6 * coverage)
    if rec_mean is not None:
        # yfinance recommendationMean: 1.0 (Strong Buy) - 5.0 (Strong Sell) → normera mot 3.0 (Hold/neutral)
        # 1.0 (Strong Buy) → +1.0, 2.0 (Buy) → +0.5, 3.0 (Hold) → 0.0, 4.0 (Underperform) → -0.5, 5.0 (Sell) → -1.0
        components.append((3.0 - rec_mean) / 2.0)
        weights.append(0.4 * coverage)
    if not weights or sum(weights) == 0:
        return None
    score = sum(c * w for c, w in zip(components, weights)) / sum(weights)
    return float(np.clip(50.0 + score * 50.0, 0.0, 100.0))


# ═════════════════════════ HÄMTNING + DB ═════════════════════════════════════

def fetch_analyst(ticker: str) -> Optional[dict]:
    """yfinance .info → analyst-data. None vid fel. Rate-limit sköts av anroparen."""
    try:
        import yfinance as yf
        y = yf.Ticker(ticker)
        info = y.info or {}
    except Exception as e:
        logger.debug("%s: .info misslyckades: %s", ticker, e)
        return None
    price = info.get("currentPrice") or info.get("regularMarketPrice")
    if price is None:
        price = info.get("previousClose")
    rec = extract_analyst(info, float(price) if price else None)
    if rec.get("target_median") is None and rec.get("recommendation_mean") is None:
        return None
    rec["ticker"] = ticker
    rec["currency"] = info.get("currency")
    return rec


def load_universe(cur) -> list[str]:
    """Listade tickers ur registret — samma query som qmj_scores."""
    cur.execute("""
        SELECT ticker FROM universe_registry
        WHERE ticker IS NOT NULL AND status = 'listed'
        ORDER BY ticker
    """)
    return [r[0] for r in cur.fetchall() if r[0]]


def upsert_analyst(cur, rows: list[dict], today: date):
    for r in rows:
        try:
            cur.execute("""
                INSERT INTO analyst_estimates (
                    ticker, fetched_at, target_median, target_high, target_low,
                    target_count, upside_pct, recommendation_mean, recommendation_key,
                    source, analyst_flags, currency, target_dispersion
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'yfinance', %s, %s, %s)
                ON CONFLICT (ticker, fetched_at) DO UPDATE SET
                    target_median = EXCLUDED.target_median,
                    target_high = EXCLUDED.target_high,
                    target_low = EXCLUDED.target_low,
                    target_count = EXCLUDED.target_count,
                    upside_pct = EXCLUDED.upside_pct,
                    recommendation_mean = EXCLUDED.recommendation_mean,
                    recommendation_key = EXCLUDED.recommendation_key,
                    source = EXCLUDED.source,
                    analyst_flags = EXCLUDED.analyst_flags,
                    currency = EXCLUDED.currency,
                    target_dispersion = EXCLUDED.target_dispersion
            """, (r["ticker"], today.isoformat(),
                  r.get("target_median"), r.get("target_high"), r.get("target_low"),
                  r.get("target_count"), r.get("upside_pct"),
                  r.get("recommendation_mean"), r.get("recommendation_key"),
                  json.dumps(r.get("flags", [])),
                  r.get("currency"), r.get("target_dispersion")))
        except Exception as e:
            logger.warning("upsert analyst %s misslyckades: %s", r.get("ticker"), e)
    return len(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Analytikeruppsida (target/recs) per ticker")
    parser.add_argument("--limit-tickers", type=int, default=0, help="0 = alla")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--print", action="store_true")
    args = parser.parse_args()

    if args.dry_run:
        # Demo-körning med mock .info (tester)
        mock = {"targetMeanPrice": 50.0, "targetHighPrice": 60.0, "targetLowPrice": 40.0,
                "numberOfAnalystOpinions": 7, "recommendationMean": 4.1,
                "recommendationKey": "buy", "currentPrice": 45.0}
        rec = extract_analyst(mock, 45.0)
        print(json.dumps(rec, indent=2, ensure_ascii=False, default=str))
        return

    if not os.environ.get("DATABASE_URL"):
        logger.error("DATABASE_URL saknas")
        return
    import psycopg2
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()
    tickers = load_universe(cur)
    if args.limit_tickers and args.limit_tickers > 0:
        tickers = tickers[:args.limit_tickers]

    rows: list[dict] = []
    errors = 0
    t0 = time.time()
    for t in tickers:
        rec = fetch_analyst(t)
        if rec:
            rows.append(rec)
        else:
            errors += 1
        time.sleep(FETCH_SLEEP)
    logger.info("Hämtade %d/%d analyst-rader (%d fel) på %.1f s",
                len(rows), len(tickers), errors, time.time() - t0)

    if args.print:
        for r in rows:
            print(f"{r['ticker']}: tgt={r['target_median']} upside={r['upside_pct']}% "
                  f"count={r['target_count']} rec={r['recommendation_mean']} {r['flags']}")

    today = date.today()
    written = upsert_analyst(cur, rows, today)
    conn.commit()
    conn.close()
    logger.info("Skrev %d analyst-rader för %s", written, today)


if __name__ == "__main__":
    main()
