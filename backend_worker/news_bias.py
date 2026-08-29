"""
news_bias.py — Nyhets-bäring → sentiment-integration (T10).

news_events.bearing (nasdaq/gnews/ddgs, redan klassad av news_classifier.py)
fogas in i sentiment-kedjan: per ticker, 72h-fönster, viktad direktbäring.

compute_news_bias — REN funktion (ingen DB): list[dict] → bias i [-1, 1].
apply_news_bias   — DB-integration: läser news_events, uppdaterar scan_results.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Bearing → riktad vikt (FÖRENKLAD modell, PLAN.md T10).
_BEARING_SCORE = {
    "negative": -1.0,
    "positive": 1.0,
    "neutral": 0.0,
}

# Sentiment-vikt ur stock-scanner core.config FACTOR_WEIGHTS (sentiment).
# Används för delta-approximationen av score_total i apply_news_bias.
SENTIMENT_WEIGHT = 0.077


def _bearing_score(bearing, direction) -> float:
    """Bearing → riktad vikt. conditional → ±0.5 enligt direction (up/down)."""
    b = str(bearing or "").strip().lower()
    if b in _BEARING_SCORE:
        return _BEARING_SCORE[b]
    if b == "conditional":
        d = str(direction or "").strip().lower()
        if d == "up":
            return 0.5
        if d == "down":
            return -0.5
        return 0.0
    return 0.0  # okänd/None bearing → neutral


def _coerce_dt(value, ref: datetime) -> datetime | None:
    """Normalisera published_at till samma tz-medvetenhet som ref (now)."""
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    if not isinstance(value, datetime):
        return None
    if ref.tzinfo is None and value.tzinfo is not None:
        return value.replace(tzinfo=None)
    if ref.tzinfo is not None and value.tzinfo is None:
        return value.replace(tzinfo=ref.tzinfo)
    return value


def compute_news_bias(events: list[dict], now: datetime, window_hours: int = 72) -> dict | None:
    """
    Viktad nyhets-bäring för EN ticker.

    Filter: published_at >= now − window_hours.
    Per event: score(bearing, direction) * confidence (fallback 1.0 om None).
    bias_raw = sum(weighted) / max(1, sum(confidence)); clip till [-1, 1].

    Returnerar {"news_bias": float, "news_bias_n": int, "ticker": str} eller
    None om 0 events i fönstret.
    """
    if not events:
        return None
    cutoff = now - timedelta(hours=window_hours)
    weighted = 0.0
    conf_sum = 0.0
    n = 0
    for ev in events:
        published = _coerce_dt(ev.get("published_at"), now)
        if published is None or published < cutoff:
            continue
        confidence = ev.get("confidence")
        if confidence is None:
            confidence = 1.0
        try:
            confidence = float(confidence)
        except (TypeError, ValueError):
            confidence = 1.0
        weighted += _bearing_score(ev.get("bearing"), ev.get("direction")) * confidence
        conf_sum += confidence
        n += 1
    if n == 0:
        return None
    bias = max(-1.0, min(1.0, weighted / max(1.0, conf_sum)))
    return {"news_bias": bias, "news_bias_n": n, "ticker": events[0].get("ticker")}


def apply_news_bias(db_conn, window_hours: int = 72) -> int:
    """
    Integrera nyhets-bäring i scan_results (T10).

    För varje ticker med klassade news_events i fönstret:
      - news_bias = compute_news_bias(events)
      - score_sentiment = clip(base + bias * 25, 0, 100)
      - score_total = clip(score_total + (ny − gammal sentiment) * 0.077, 0, 100)

    Endast rader som redan har icke-NULL score_sentiment uppdateras; en ticker
    som saknas i scan_results hoppas över (loggas).

    Idempotent: räknar ALLTID från aktuell DB-rad (base = nuvarande
    score_sentiment), aldrig kumulativt — två körningar ger samma resultat.

    Returnerar antal uppdaterade rader.
    """
    now = datetime.now()
    cutoff = now - timedelta(hours=window_hours)
    updated = 0

    with db_conn.cursor() as cur:
        # Klassade events i fönstret, grupperade per ticker (en round-trip)
        cur.execute(
            """
            SELECT ticker, bearing, direction, confidence, published_at
            FROM news_events
            WHERE ticker IS NOT NULL
              AND bearing IS NOT NULL
              AND published_at >= %s
            ORDER BY ticker, published_at
            """,
            (cutoff,),
        )
        by_ticker: dict[str, list[dict]] = {}
        for ticker, bearing, direction, confidence, published_at in cur.fetchall():
            by_ticker.setdefault(ticker, []).append({
                "ticker": ticker,
                "bearing": bearing,
                "direction": direction,
                "confidence": confidence,
                "published_at": published_at,
            })

        for ticker, events in by_ticker.items():
            bias = compute_news_bias(events, now, window_hours)
            if bias is None:
                continue
            cur.execute(
                "SELECT score_sentiment, score_total FROM scan_results WHERE ticker = %s",
                (ticker,),
            )
            row = cur.fetchone()
            if row is None:
                logger.warning("news_bias: %s saknas i scan_results — hoppar över", ticker)
                continue
            old_sentiment, score_total = row
            if old_sentiment is None:
                # Endast rader som redan har icke-NULL score_sentiment
                continue
            new_sentiment = max(0.0, min(100.0, float(old_sentiment) + bias["news_bias"] * 25.0))
            # delta-approximation av composite — vikt 0.077 ur stock-scanner core.config FACTOR_WEIGHTS (sentiment)
            if score_total is not None:
                new_total = max(
                    0.0, min(100.0, float(score_total) + (new_sentiment - float(old_sentiment)) * SENTIMENT_WEIGHT)
                )
            else:
                new_total = None
            cur.execute(
                """
                UPDATE scan_results
                SET score_sentiment = %s, score_total = %s,
                    news_bias = %s, news_bias_n = %s
                WHERE ticker = %s
                """,
                (new_sentiment, new_total, bias["news_bias"], bias["news_bias_n"], ticker),
            )
            updated += 1

    db_conn.commit()
    logger.info("news_bias: uppdaterade %d rader i scan_results", updated)
    return updated