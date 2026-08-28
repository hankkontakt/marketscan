"""
news_common.py — Delad logik för nyhetskedjan (normalisering, namnmatch, upsert).

Används av: news_events.py (Nasdaq-officiell), news_discovery.py (Google News).
"""
from __future__ import annotations

import hashlib
import logging
import os
import re
from datetime import date
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


# Generiska ämnesord som ALDRIG får trigga ticker-match (oavsett case).
GENERIC_BASES = {"investor", "note", "sci", "abb", "bba", "etc"}


def match_ticker(headline: str, registry: dict) -> Optional[str]:
    """Slå upp ticker genom norm-namn-substring i rubriken (längst match vinner).

    Fallback för reg-rader som bara har ticker som 'namn' (X-): matcha basdelen
    av tickern (SIVE.ST → \\bsive\\w*) med ordgräns (undantag: flerklass-tickers
    med '-', t.ex. ERIC-B.ST, hoppas över — för kollisionsrisk).

    Falsk-positiv-skydd (2026-08-29):
    - Generiska baser (investor/note/sci/abb/bba/etc) matchas aldrig.
    - Baser 2-3 tecken: token i texten måste vara UPPER-case (INVE/ABB skrivs
      versaler i rubriker).
    - Baser 4-5 tecken: token måste vara capitalized eller UPPER-case
      ("Hexagon" matchar HEXA-B.ST, "hexa" i löptext gör det inte).
    """
    if not headline:
        return None
    hl = norm(headline)
    best = None
    for key, (ticker, name) in registry.items():
        if len(key) < 4 or key in GENERIC_BASES:
            continue
        if key in hl and (best is None or len(key) > len(best[0])):
            best = (key, ticker)
    # Ticker-bas-fallback (SIVE.ST → sive, ordgräns + egen stavning)
    if best is None:
        hl_raw = (headline or "").lower()
        for key, (ticker, _) in registry.items():
            base = (ticker or "").split(".")[0].lower().replace("-b", "").replace("-a", "")
            if not base or len(base) < 2 or base in GENERIC_BASES or "-" in ticker.split(".")[0]:
                continue
            m = re.search(rf"\b{base}\w*", hl_raw)
            if not m:
                continue
            token = headline[m.start():m.end()]
            if len(base) <= 3 and not token.isupper():
                continue
            if 4 <= len(base) <= 5 and not (token[0].isupper() or token.isupper()):
                continue
            if best is None or len(base) > len(best[0]):
                best = (base, ticker)
    return best[1] if best else None


def normalize_url(source: str, url: str) -> str:
    """Stabilisera URL: Google News-links har variabla query-parametrar —
    använd scheme+host+path endast (artikel-ID ligger i path)."""
    if not url:
        return url
    try:
        from urllib.parse import urlsplit
        p = urlsplit(url)
        return f"{p.scheme}://{p.netloc}{p.path}"
    except Exception:
        return url


def upsert_events(conn, rows: list[dict], dedup_hours: int = 36) -> dict:
    """Upsert normaliserade händelser. row = {source, source_category, headline,
    company_raw, ticker, published_at, message_url, mention_surge}.

    DEDUP: nätdubbel (samma rubrik-ferst 50 tecken + samma ticker inom 36 h)
    hoppas över — varje källa kan annars fylla på dubletter.
    """
    if not rows:
        return {"written": 0}
    cur = conn.cursor()
    written = skipped = 0
    for r in rows:
        try:
            if r.get("ticker") and dedup_hours > 0:
                cur.execute("""
                    SELECT 1 FROM news_events
                    WHERE ticker = %s
                      AND LOWER(LEFT(headline, 50)) = LOWER(LEFT(%s, 50))
                      AND published_at > NOW() - INTERVAL '%s hours'
                    LIMIT 1
                """, (r["ticker"], r["headline"], str(dedup_hours)))
                if cur.fetchone():
                    skipped += 1
                    continue
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
                event_id(r["source"], normalize_url(r["source"], r["message_url"])),
                r["source"], r.get("source_category"), r["headline"],
                r.get("company_raw"), r.get("ticker"),
                r.get("published_at"), normalize_url(r["source"], r["message_url"]),
                r.get("mention_surge"),
            ))
            written += 1
        except Exception as e:
            logger.warning("Upsert failed %s: %s", r.get("message_url")[:60], e)
    conn.commit()
    return {"written": written, "skipped_dupes": skipped}


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


# ─── Injektionsskydd (deterministiskt — LLM litar vi INTE på för detta) ────────
# Bevisat 2026-08-28: deepseek-v4-flash FÖLJER instruktioner i nyhetstexten
# ("ignore previous instructions" → bearing=positive). Därför: misstänkt innehåll
# klassificeras ALDRIG av LLM:en — det får neutral + låg förtroende + märkning.

INJECTION_PATTERNS = [
    r"\bignore\s+(?:all|previous|the|any|any previous)",
    r"\bignore all previous\b", r"\bignore previous instructions\b",
    r"\bignore the previous\b", r"\bignore preceding instructions\b",
    r"\bforget\s+(?:everything|all|previous)",
    r"\bdisregard\s+(?:previous|the|all|instructions)",
    r"\bsystem\s*(?:message|prompt|instructions|instruktion|says|told)",
    r"\bassistant\s*[:>]", r"\buser\s*[:>]",
    r"</?system>", r"<\s*system", r"<\s*assistant", r"<!--", r"<%",
    r"\{\{\s*[a-z_]+\s*\}\}", r"\[\[", r"```", r"`json`", r"```json",
    r"\bcorrige", r"\bcorrect your answer\b",
    r"\bbecome a\b", r"\byou are now\b", r"\bno longer need\b",
    r"\btreat everything above\b",
    r"\bhallucinat", r"\bberätta\s+(\bnu\b|\batt\b)",
    r"\bact\s+as\b", r"\bpretend\b", r"\bfrom now on",
]


def is_suspicious(text: str) -> bool:
    """True = innehållet bär injektionssignaturer → LLM ska INTE se det."""
    if not text:
        return False
    t = (text or "").lower()
    return any(__import__("re").search(p, t) for p in INJECTION_PATTERNS)


def connect():
    import psycopg2
    return psycopg2.connect(os.environ["DATABASE_URL"])
