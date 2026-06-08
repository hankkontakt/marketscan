"""
Digest Mailer — sends weekly email digests to opted-in users.

Each digest includes:
  - Portfolio summary (total value, weekly change, top/worst holdings)
  - Top STARK signals this week (from score_history)
  - Score movers — biggest upward/downward changes vs 7 days ago
  - Signal changes — entries that moved to STARK this week

Runs every Monday morning via GitHub Actions.
Respects email_opt_in and weekly_digest flags in profiles.
Prevents duplicate sends via digest_log table.

Usage:
    python -m marketscan.backend_worker.digest_mailer
"""
import os
import logging
from datetime import date, timedelta

import psycopg2
import psycopg2.extras

from backend_worker.email import sender, layout, components

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


# ─── Digest HTML Builder ──────────────────────────────────────────────────────

def _build_digest_html(
    user_name: str,
    portfolio_summary: dict | None,
    stark_stocks: list[dict],
    score_movers_up: list[dict],
    score_movers_down: list[dict],
    signal_changes: list[dict],
) -> tuple[str, str]:
    """Returns (subject, html)."""

    parts = []

    # Greeting
    name = user_name or "Investerare"
    parts.append(layout.section(f"Hej {name}! Här är din veckosammanfattning från MarketScan."))

    # Portfolio summary
    if portfolio_summary and portfolio_summary.get("count", 0) > 0:
        parts.append(f"""
        <h2 style="font-size:13px; font-weight:600; color:#14181F; margin:16px 0 8px 0;">
          Din portfölj
        </h2>""")
        parts.append(layout.metric_row(
            "Antal innehav", str(portfolio_summary.get("count", 0))
        ))
        if portfolio_summary.get("total_value"):
            parts.append(layout.metric_row(
                "Uppskattat värde",
                f"{portfolio_summary['total_value']:,.0f} kr"
            ))
        if portfolio_summary.get("avg_score") is not None:
            parts.append(layout.metric_row(
                "Snittbetyg", f"{portfolio_summary['avg_score']:.1f}/100"
            ))
        if portfolio_summary.get("stark_count", 0) > 0:
            parts.append(layout.metric_row(
                "STARK-innehav", str(portfolio_summary["stark_count"])
            ))

    # STARK signals this week
    if stark_stocks:
        parts.append(f"""
        <h2 style="font-size:13px; font-weight:600; color:#14181F; margin:16px 0 8px 0;">
          Toppbetyg denna vecka
        </h2>""")
        rows = [
            (s["ticker"], s.get("name") or s["ticker"],
             s.get("entry_signal", ""), f"{s.get('score_total', 0):.0f}")
            for s in stark_stocks[:8]
        ]
        parts.append(layout.stock_table(rows))

    # Signal changes — new STARK
    if signal_changes:
        parts.append(f"""
        <h2 style="font-size:13px; font-weight:600; color:#14181F; margin:16px 0 8px 0;">
          Nya STARK-signaler denna vecka
        </h2>""")
        rows = [
            (s["ticker"], s.get("name") or s["ticker"], "STARK", f"{s.get('score_total', 0):.0f}")
            for s in signal_changes[:6]
        ]
        parts.append(layout.stock_table(rows))

    # Score movers up
    if score_movers_up:
        parts.append(f"""
        <h2 style="font-size:13px; font-weight:600; color:#14181F; margin:16px 0 8px 0;">
          Störst uppgång i betyg (7 dagar)
        </h2>""")
        rows = [
            (s["ticker"], s.get("name") or s["ticker"],
             s.get("entry_signal") or "–",
             f"+{s.get('score_change', 0):.1f} ({s.get('score_total', 0):.0f})")
            for s in score_movers_up[:6]
        ]
        parts.append(layout.stock_table(rows))

    # Score movers down
    if score_movers_down:
        parts.append(f"""
        <h2 style="font-size:13px; font-weight:600; color:#14181F; margin:16px 0 8px 0;">
          Störst nedgång i betyg (7 dagar)
        </h2>""")
        rows = [
            (s["ticker"], s.get("name") or s["ticker"],
             s.get("entry_signal") or "–",
             f"{s.get('score_change', 0):.1f} ({s.get('score_total', 0):.0f})")
            for s in score_movers_down[:6]
        ]
        parts.append(layout.stock_table(rows))

    # CTA button
    parts.append(layout.button("Öppna MarketScan", "{app_url}/screener"))

    content = "\n".join(parts)
    html = layout.layout(content)
    subject = f"MarketScan Veckodigest — {date.today().strftime('%d %b')}"
    return subject, html


# ─── Data Fetchers ────────────────────────────────────────────────────────────

def _get_stark_stocks(cur, limit: int = 10) -> list[dict]:
    """Top STARK stocks by score this week."""
    cur.execute("""
        SELECT s.ticker, s.name, s.score_total, s.entry_signal
        FROM scan_results s
        WHERE s.entry_signal = 'STARK'
        ORDER BY s.score_total DESC
        LIMIT %s
    """, (limit,))
    return [dict(r) for r in cur.fetchall()]


def _get_score_movers(cur, days: int = 7) -> tuple[list[dict], list[dict]]:
    """Stocks with largest score changes over N days."""
    week_ago = (date.today() - timedelta(days=days)).isoformat()

    cur.execute("""
        WITH prev AS (
            SELECT DISTINCT ON (ticker) ticker, score_total AS prev_score
            FROM score_history
            WHERE scan_date <= %s
            ORDER BY ticker, scan_date DESC
        )
        SELECT s.ticker, s.name, s.score_total, s.entry_signal,
               (s.score_total - prev.prev_score) AS score_change
        FROM scan_results s
        JOIN prev ON prev.ticker = s.ticker
        WHERE s.score_total IS NOT NULL AND prev.prev_score IS NOT NULL
          AND ABS(s.score_total - prev.prev_score) >= 5
        ORDER BY score_change DESC
        LIMIT 20
    """, (week_ago,))

    rows = [dict(r) for r in cur.fetchall()]
    up   = [r for r in rows if r["score_change"] and r["score_change"] > 0][:8]
    down = sorted([r for r in rows if r["score_change"] and r["score_change"] < 0],
                  key=lambda x: x["score_change"])[:6]
    return up, down


def _get_signal_changes(cur, days: int = 7) -> list[dict]:
    """Tickers that transitioned TO STARK in the last N days."""
    cur.execute("""
        SELECT DISTINCT t.ticker, s.name, s.score_total
        FROM signal_transitions t
        LEFT JOIN scan_results s ON s.ticker = t.ticker
        WHERE t.field = 'entry_signal'
          AND t.to_value = 'STARK'
          AND t.transition_date >= CURRENT_DATE - %s
        ORDER BY s.score_total DESC NULLS LAST
        LIMIT 10
    """, (days,))
    return [dict(r) for r in cur.fetchall()]


def _get_portfolio_summary(cur, user_id: str) -> dict | None:
    """Portfolio summary for a specific user."""
    cur.execute("""
        SELECT h.ticker, h.shares, COALESCE(s.price, h.cost_basis) AS price,
               s.score_total, s.entry_signal
        FROM portfolios p
        JOIN holdings h ON h.portfolio_id = p.id
        LEFT JOIN scan_results s ON s.ticker = h.ticker
        WHERE p.user_id = %s
    """, (user_id,))
    rows = cur.fetchall()
    if not rows:
        return None

    total_value = sum(float(r["price"] or 0) * float(r["shares"]) for r in rows)
    scores = [float(r["score_total"]) for r in rows if r["score_total"] is not None]
    stark_count = sum(1 for r in rows if r["entry_signal"] == "STARK")

    return {
        "count": len(rows),
        "total_value": round(total_value, 0),
        "avg_score": round(sum(scores) / len(scores), 1) if scores else None,
        "stark_count": stark_count,
    }


# ─── Main ─────────────────────────────────────────────────────────────────────

def send_weekly_digests(dsn: str) -> dict[str, int]:
    """Send digest emails to all opted-in users. Returns stats."""
    today      = date.today()
    week_start = (today - timedelta(days=today.weekday())).isoformat()  # Monday

    stats = {"users_checked": 0, "sent": 0, "skipped": 0, "errors": 0}

    with psycopg2.connect(dsn, client_encoding="UTF8") as conn:
        conn.autocommit = False
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Pre-compute market-wide data once
        stark_stocks   = _get_stark_stocks(cur)
        movers_up, movers_down = _get_score_movers(cur)
        signal_changes = _get_signal_changes(cur)

        # Load opted-in users
        cur.execute("""
            SELECT u.id, u.email, p.display_name,
                   COALESCE(p.email_opt_in, false) AS email_opt_in,
                   COALESCE(p.weekly_digest, true) AS weekly_digest
            FROM auth.users u
            LEFT JOIN profiles p ON p.id = u.id
            WHERE u.email IS NOT NULL
              AND COALESCE(p.email_opt_in, false) = true
              AND COALESCE(p.weekly_digest, true) = true
        """)
        users = cur.fetchall()
        stats["users_checked"] = len(users)
        logger.info("Sending digests to %d opted-in users", len(users))

        for user in users:
            user_id = user["id"]
            email   = user["email"]

            # Check if already sent this week
            cur.execute("""
                SELECT 1 FROM digest_log
                WHERE user_id = %s AND digest_type = 'weekly' AND week_start = %s
            """, (user_id, week_start))
            if cur.fetchone():
                stats["skipped"] += 1
                continue

            try:
                portfolio_summary = _get_portfolio_summary(cur, user_id)
                subject, html = _build_digest_html(
                    user_name=user.get("display_name") or email.split("@")[0],
                    portfolio_summary=portfolio_summary,
                    stark_stocks=stark_stocks,
                    score_movers_up=movers_up,
                    score_movers_down=movers_down,
                    signal_changes=signal_changes,
                )

                ok = sender.send(email, subject, html)

                if ok:
                    cur.execute("""
                        INSERT INTO digest_log (user_id, digest_type, week_start, email_to)
                        VALUES (%s, 'weekly', %s, %s)
                        ON CONFLICT (user_id, digest_type, week_start) DO NOTHING
                    """, (user_id, week_start, email))
                    conn.commit()
                    stats["sent"] += 1
                else:
                    stats["errors"] += 1

            except Exception as exc:
                logger.error("Digest failed for %s: %s", email, exc)
                stats["errors"] += 1
                try:
                    conn.rollback()
                except Exception:
                    pass

    logger.info(
        "Digest done: %d checked, %d sent, %d skipped, %d errors",
        stats["users_checked"], stats["sent"], stats["skipped"], stats["errors"],
    )
    return stats


if __name__ == "__main__":
    dsn = os.environ["DATABASE_URL"]
    send_weekly_digests(dsn)
