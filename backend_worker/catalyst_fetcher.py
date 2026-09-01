"""
catalyst_fetcher.py — Katalysatorfönster: kommande händelser per ticker.

KÄLLA (inget Finnhub — US-only enligt audit datatest-nyckelberoende.md:97-98):
  earnings_surprises (migration 051): yfinance earnings_dates skrivs redan varje
  måndag av earnings_surprise.py med PIT-snapshot-rader (estimate_source='snapshot',
  announce_at i framtiden). Dessa ÄR nästa rapportdatum — ingen ny hämtning.

Bygger catalyst_events (migration 067): earnings + dividend_ex/pay (ur
scan_results.dividend_yield som proxy — verkligt ex-datum kräver Finnhub/Börsdata,
markeras därför confidence='low'). Körs fredag 04:30 UTC (efter QMJ) och ska
även kunna köras standalone efter att earnings_surprise.py har kört.

Användning:
    python -m backend_worker.catalyst_fetcher --dry-run
"""
from __future__ import annotations

import argparse
import logging
import os
from datetime import date, timedelta
from typing import Optional

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# Katalysator-boost gäller events inom 45 dagar (händelser är tradeable)
CATALYST_WINDOW_DAYS = 45
# Earnings-snapshot äldre än detta anses osäker (yfinance-datum kan flyttas)
SNAPSHOT_MAX_AGE_DAYS = 120


# ═════════════════════════ PURE CORE (testbar; ingen nätverk/DB) ══════════════

def days_until(event_date: date, today: date) -> int:
    return (event_date - today).days


def collect_events(cur, today: date) -> list[dict]:
    """Slå ihop earnings-snapshots (hög konfidens) med dividend-proxys (låg konfidens)."""
    surprises = load_surprises(cur, today)
    dividends = load_dividends(cur)
    events: list[dict] = []
    for s in surprises:
        d = s["event_date"]
        events.append({
            "ticker": s["ticker"],
            "event_type": s.get("event_type", "earnings"),
            "event_date": d,
            "days_until": days_until(d, today),
            "confidence": s.get("confidence", "high"),
        })
    for d in dividends:
        # Utan ex-kursdata används grov uppskattning: nästkommande månadsskifte.
        # Markeras 'low' — verkligt datum kräver extern källa.
        approx = today.replace(day=15) + timedelta(days=32)
        if d.get("yield_pct") and d["yield_pct"] > 0:
            events.append({
                "ticker": d["ticker"],
                "event_type": "dividend_ex",
                "event_date": approx,
                "days_until": days_until(approx, today),
                "confidence": "low",
            })
    return events


def catalyst_z(events: list[dict], today: date) -> Optional[float]:
    """Katalysator-delscore 0-100. Ju närmare händelse, desto högre.

    NULL om inga events. Regelegen: earnings (high confidence) ger full boost,
    dividend (low) halv. Ingen boost för passerade händelser.
    Beräknar days_until själv från event_date (fallback om days_until saknas).
    """
    if not events:
        return None
    upcoming = []
    for e in events:
        du = e.get("days_until")
        if du is None and e.get("event_date") is not None:
            try:
                ed = e["event_date"].date() if hasattr(e["event_date"], "date") else date.fromisoformat(str(e["event_date"])[:10])
                du = (ed - today).days
            except Exception:
                du = None
        if du is not None and du >= 0:
            upcoming.append({**e, "days_until": du})
    if not upcoming:
        return None
    best = 0.0
    for e in upcoming:
        du = e.get("days_until", 999)
        conf = e.get("confidence", "medium")
        conf_mult = 1.0 if conf == "high" else (0.5 if conf == "medium" else 0.25)
        # linjär ramp: 0 dagar → 100, 45 dagar → 0 (men aldrig negativ)
        score = max(0.0, (CATALYST_WINDOW_DAYS - min(du, CATALYST_WINDOW_DAYS)) / CATALYST_WINDOW_DAYS * 100.0)
        best = max(best, score * conf_mult)
    return float(best)


def catalyst_boost(events: list[dict], today: date) -> float:
    """Master-poäng-boost: +5 för earnings ≤ 45 dagar (händelser tradeable)."""
    z = catalyst_z(events, today)
    if z is None:
        return 0.0
    return 5.0 * (z / 100.0)


def next_event(events: list[dict]) -> Optional[dict]:
    """Närmaste kommande händelse — 'YYYY-MM-DD:earnings' + days."""
    upcoming = [e for e in events if e.get("days_until") is not None and e["days_until"] >= 0]
    if not upcoming:
        return None
    best = min(upcoming, key=lambda e: e["days_until"])
    return best


# ═════════════════════════ DB ═════════════════════════════════════════════════

def load_surprises(cur, today: date) -> list[dict]:
    """Kommande earnings från earnings_surprises PIT-snapshots."""
    cur.execute("""
        SELECT ticker, announce_at, eps_estimate, captured_at
        FROM earnings_surprises
        WHERE estimate_source = 'snapshot' AND eps_actual IS NULL
          AND announce_at >= %s
        ORDER BY announce_at
    """, (today.isoformat(),))
    out: list[dict] = []
    for r in cur.fetchall():
        ticker, announce_at, eps_est, captured_at = r
        if announce_at is None:
            continue
        event_date = announce_at.date() if hasattr(announce_at, "date") else date.fromisoformat(str(announce_at)[:10])
        age = (today - (captured_at.date() if hasattr(captured_at, "date") else today)).days if captured_at else 999
        conf = "high" if age <= SNAPSHOT_MAX_AGE_DAYS else "medium"
        out.append({"ticker": ticker, "event_date": event_date, "confidence": conf, "event_type": "earnings"})
    return out


def load_dividends(cur) -> list[dict]:
    """Dividend-yield-proxy ur scan_results (ex-datum approximeras — confidence low)."""
    cur.execute("""
        SELECT ticker, dividend_yield FROM scan_results
        WHERE dividend_yield IS NOT NULL AND dividend_yield > 0 AND dividend_yield < 0.2
    """)
    return [{"ticker": r[0], "yield_pct": float(r[1]) * 100} for r in cur.fetchall()]


def upsert_events(cur, events: list[dict]):
    written = 0
    for e in events:
        try:
            cur.execute("""
                INSERT INTO catalyst_events (ticker, event_type, event_date, days_until, confidence)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (ticker, event_type, event_date) DO UPDATE SET
                    days_until = EXCLUDED.days_until,
                    confidence = EXCLUDED.confidence
            """, (e["ticker"], e["event_type"], e["event_date"].isoformat(),
                  e["days_until"], e["confidence"]))
            written += 1
        except Exception as ex:
            logger.warning("upsert catalyst %s/%s misslyckades: %s",
                           e.get("ticker"), e.get("event_type"), ex)
    return written


def clear_stale(cur, today: date):
    """Rensa passerade events (>30 dagar gamla) så tabellen bara har framtiden."""
    cur.execute("DELETE FROM catalyst_events WHERE event_date < %s", ((today - timedelta(days=30)).isoformat(),))
    return cur.rowcount


def main() -> None:
    parser = argparse.ArgumentParser(description="Katalysatorfönster (earnings + dividend)")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--print", action="store_true")
    args = parser.parse_args()

    if args.dry_run:
        today = date.today()
        snaps = [
            {"ticker": "SEB-A.ST", "event_date": today + timedelta(days=12), "confidence": "medium"},
            {"ticker": "NOKIA.HE", "event_date": today + timedelta(days=5), "confidence": "high"},
        ]
        divs = [{"ticker": "VOLV-B.ST", "yield_pct": 3.8}]
        events = []
        for s in snaps:
            d = s["event_date"]
            events.append({
                "ticker": s["ticker"],
                "event_type": "earnings",
                "event_date": d,
                "days_until": days_until(d, today),
                "confidence": s.get("confidence", "high"),
            })
        for d in divs:
            approx = today.replace(day=15) + timedelta(days=32)
            events.append({
                "ticker": d["ticker"],
                "event_type": "dividend_ex",
                "event_date": approx,
                "days_until": days_until(approx, today),
                "confidence": "low",
            })
        for e in events:
            print(e)
        print("catalyst_z =", catalyst_z(events, today), "boost =", catalyst_boost(events, today))
        return

    if not os.environ.get("DATABASE_URL"):
        logger.error("DATABASE_URL saknas")
        return
    import psycopg2
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()
    today = date.today()

    events = collect_events(cur, today)
    logger.info("Byggde %d events", len(events))

    stale = clear_stale(cur, today)
    written = upsert_events(cur, events)
    conn.commit()
    conn.close()
    logger.info("Skrev %d katalysator-events (rensade %d passerade)", written, stale)


if __name__ == "__main__":
    main()
