"""
Score Tracker — snapshots daily scores and detects signal transitions.

Runs after every pipeline execution (triggered by pipeline.yml).
Populates:
  - score_history: daily snapshot of every ticker's scores + signals + price
  - signal_transitions: logs every time entry_signal or trend_signal changes

This data powers:
  - Score history charts in the frontend (/aktie/[ticker])
  - Smart alert evaluations (score_change, signal_change types)
  - Strategy Lab backtesting (score_history is the simulation dataset)
  - Signal persistence analytics

Usage:
    python -m marketscan.backend_worker.score_tracker
"""
import os
import logging
from datetime import date

import psycopg2
import psycopg2.extras

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

SCORE_FIELDS = [
    "score_total", "score_value", "score_quality", "score_momentum",
    "score_growth", "score_risk", "score_dividend", "score_sentiment",
]

SIGNAL_FIELDS = ["entry_signal", "trend_signal"]


def snapshot_scores(dsn: str) -> dict[str, int]:
    """
    1. Snapshot today's scan_results into score_history.
    2. Detect signal transitions vs yesterday.
    Returns: {"snapshotted": N, "transitions": M}
    """
    today = date.today().isoformat()
    stats = {"snapshotted": 0, "transitions": 0}

    with psycopg2.connect(dsn, client_encoding="UTF8") as conn:
        conn.autocommit = False
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # ── 1. Load today's scan_results ──────────────────────────────────────
        cur.execute("""
            SELECT ticker, scan_date,
                   score_total, score_value, score_quality, score_momentum,
                   score_growth, score_risk, score_dividend, score_sentiment,
                   entry_signal, confidence_label, trend_signal,
                   price, change_pct, vol_20d, piotroski_f
            FROM scan_results
        """)
        today_rows = cur.fetchall()
        logger.info("Loaded %d rows from scan_results", len(today_rows))

        if not today_rows:
            logger.warning("scan_results is empty — nothing to snapshot")
            return stats

        # ── 2. Bulk upsert into score_history ─────────────────────────────────
        insert_data = []
        for row in today_rows:
            insert_data.append((
                row["ticker"], today,
                row["score_total"], row["score_value"], row["score_quality"],
                row["score_momentum"], row["score_growth"], row["score_risk"],
                row["score_dividend"], row["score_sentiment"],
                row["entry_signal"], row["confidence_label"], row["trend_signal"],
                row["price"], row["change_pct"], row["vol_20d"], row["piotroski_f"],
            ))

        psycopg2.extras.execute_values(
            cur,
            """
            INSERT INTO score_history (
                ticker, scan_date,
                score_total, score_value, score_quality, score_momentum,
                score_growth, score_risk, score_dividend, score_sentiment,
                entry_signal, confidence_label, trend_signal,
                price, change_pct, vol_20d, piotroski_f
            ) VALUES %s
            ON CONFLICT (ticker, scan_date) DO UPDATE SET
                score_total = EXCLUDED.score_total,
                score_value = EXCLUDED.score_value,
                score_quality = EXCLUDED.score_quality,
                score_momentum = EXCLUDED.score_momentum,
                score_growth = EXCLUDED.score_growth,
                score_risk = EXCLUDED.score_risk,
                score_dividend = EXCLUDED.score_dividend,
                score_sentiment = EXCLUDED.score_sentiment,
                entry_signal = EXCLUDED.entry_signal,
                confidence_label = EXCLUDED.confidence_label,
                trend_signal = EXCLUDED.trend_signal,
                price = EXCLUDED.price,
                change_pct = EXCLUDED.change_pct,
                vol_20d = EXCLUDED.vol_20d,
                piotroski_f = EXCLUDED.piotroski_f
            """,
            insert_data,
            template=None,
            page_size=500,
        )
        stats["snapshotted"] = len(insert_data)
        conn.commit()
        logger.info("Snapshotted %d scores for %s", stats["snapshotted"], today)

        # ── 3. Detect signal transitions ──────────────────────────────────────
        # Compare today's signals with the most recent previous snapshot
        cur.execute("""
            SELECT DISTINCT ON (ticker) ticker, entry_signal, trend_signal, scan_date
            FROM score_history
            WHERE scan_date < %s
            ORDER BY ticker, scan_date DESC
        """, (today,))
        prev_rows = {r["ticker"]: r for r in cur.fetchall()}

        transitions = []
        today_map = {r["ticker"]: r for r in today_rows}

        for ticker, prev in prev_rows.items():
            curr = today_map.get(ticker)
            if not curr:
                continue

            for field in SIGNAL_FIELDS:
                prev_val = prev[field]
                curr_val = curr[field]
                if prev_val != curr_val and curr_val is not None:
                    transitions.append((
                        ticker, today, field, prev_val, curr_val,
                        curr["score_total"], curr["price"],
                    ))

        if transitions:
            psycopg2.extras.execute_values(
                cur,
                """
                INSERT INTO signal_transitions
                    (ticker, transition_date, field, from_value, to_value, score_total_at, price_at)
                VALUES %s
                ON CONFLICT (ticker, transition_date, field) DO NOTHING
                """,
                transitions,
                page_size=200,
            )
            conn.commit()
            stats["transitions"] = len(transitions)
            logger.info("Recorded %d signal transitions for %s", len(transitions), today)

    return stats


def cleanup_old_history(dsn: str, keep_days: int = 730) -> int:
    """Remove score_history older than keep_days (default: 2 years)."""
    with psycopg2.connect(dsn) as conn, conn.cursor() as cur:
        cur.execute(
            "DELETE FROM score_history WHERE scan_date < CURRENT_DATE - INTERVAL '%s days'",
            (keep_days,)
        )
        deleted = cur.rowcount
        conn.commit()
    if deleted:
        logger.info("Cleaned up %d old score_history rows (>%d days)", deleted, keep_days)
    return deleted


if __name__ == "__main__":
    dsn = os.environ["DATABASE_URL"]
    result = snapshot_scores(dsn)
    cleanup_old_history(dsn)
    logger.info(
        "Score tracker done: %d snapshotted, %d transitions",
        result["snapshotted"], result["transitions"],
    )
