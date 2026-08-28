"""
news_common.py — Delad logik för nyhetskedjan (normalisering, namnmatch, upsert).

Används av: news_events.py (Nasdaq-officiell), news_discovery.py (Google News/DDGS).
"""
from __future__ import annotations

import hashlib
import logging
import os
import re
from datetime import date, datetime
from typing import Optional

logger = logging.getLogger(__name__)


def norm(s: str) -> str:
    """'AB Säkerhetsgruppen (publ)' → 'sakerhetsgruppen' (för namnmatch)."""
    n = (s or "").lower()
    n = re.sub(r"[^a-zåäö0-9 ]+", " ", n)
    n = re.sub(r"\b(aktiebolag|ab|publ|holding|group|inc|corp)\b", " ", n)
    return re.sub(r"\s+", " ", n).strip()


def event_id(source: str, url: str) -> str:
    return hashlib.sha1(f"{source}|{url}".encode("utf-8")).hexdigest()


def load_registry(conn) -> dict:
    """norm-namn → (ticker, namn) ur universe_registry (tickers med suffix)."""
    cur = conn.cursor()
    cur.execute(
        "SELECT ticker, name FROM universe_registry "
        "WHERE ticker IS NOT NULL AND name IS NOT NULL"
    )
    out: dict = {}
    for ticker, name in cur.fetchall():
        if ticker and name:
            out[norm(name)] = (ticker, name.strip())
    return out


def match_ticker(headline: str, registry: dict) -> Optional[str]:
    """Slå upp ticker genom norm-namn-substring i rubriken (längst match vinner).

    Fallback för reg-rader som bara har ticker som 'namn' (X-): matcha basdelen
    av tickern (SIVE.ST → \\bsive\\w*) med ordgräns (undantag: flerklass-tickers
    med '-', t.ex. ERIC-B.ST, hoppas över — för kollisionsrisk).
    """
    if not headline:
        return None
    hl = norm(headline)
    best = None
    for key, (ticker, name) in registry.items():
        if len(key) < 4:
            continue
        if key in hl and (best is None or len(key) > len(best[0])):
            best = (key, ticker)
    # Ticker-bas-fallback (SIVE.ST → sive, ordgräns + egen stavning)
    if best is None:
        hl_raw = (headline or "").lower()
        for key, (ticker, _) in registry.items():
            base = (ticker or "").split(".")[0].lower().replace("-b", "").replace("-a", "")
            if not base or len(base) < 3 or "-" in ticker.split(".")[0]:
                continue
            if re.search(rf"\b{base}\w*", hl_raw) and (best is None or len(base) > len(best[0])):
                best = (base, ticker)
    return best[1] if best else None


def upsert_events(conn, rows: list[dict]) -> dict:
    """Upsert normaliserade händelser. row: source, source_category, headline,
    company_raw, ticker, published_at, message_url, mention_surge."""
    if not rows:
        return {"written": 0}
    cur = conn.cursor()
    written = 0
    for r in rows:
        try:
            cur.execute("""
                INSERT INTO news_events (
                    event_id, source, source_category, headline, company_raw,
                    ticker, published_at, message_url, mention_surge
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (source, message_url) DO UPDATE SET
                    headline = EXCLUDED.headline,
                    company_raw = COALESCE(EXCLUDED.company_raw, news_events.company_raw),
                    ticker = COALESCE(EXCLUDED.ticker, news_events.ticker),
                    published_at = EXCLUDED.published_at,
                    mention_surge = COALESCE(EXCLUDED.mention_surge, news_events.mention_surge)
            """, (
                event_id(r["source"], r["message_url"]),
                r["source"], r.get("source_category"), r["headline"],
                r.get("company_raw"), r.get("ticker"),
                r.get("published_at"), r["message_url"], r.get("mention_surge"),
            ))
            written += 1
        except Exception as e:
            logger.warning("Upsert failed %s: %s", r.get("message_url")[:60], e)
    conn.commit()
    return {"written": written}


def parse_pubdate(s: str) -> Optional[str]:
    """PubDate-strängar (RFC-822 / ISO) → ISO-datetime-str (DB-kompatibelt)."""
    if not s:
        return None
    try:
        from email.utils import parsedate_to_datetime
        dt = parsedate_to_datetime(s)
        return dt.astimezone().isoformat()
    except Exception:
        try:
            return date.fromisoformat(s[:10]).isoformat() + "T00:00:00+00:00"
        except Exception:
            return None


def connect():
    import psycopg2
    return psycopg2.connect(os.environ["DATABASE_URL"])
