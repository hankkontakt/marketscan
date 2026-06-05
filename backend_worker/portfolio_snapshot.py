"""
Daily portfolio snapshot creator — runs as a cron job in GitHub Actions.
Creates or updates portfolio_snapshots rows for all users who have holdings.

Usage:
    python -m backend_worker.portfolio_snapshot

Environment:
    DATABASE_URL   — Supabase Postgres connection string (with service role)
"""
import os
import logging
from datetime import date

import psycopg2

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def run(dsn: str | None = None) -> int:
    """
    Create today's portfolio snapshots for all users with holdings.
    Returns the number of snapshots created.
    """
    dsn = dsn or os.environ.get("DATABASE_URL")
    if not dsn:
        logger.error("DATABASE_URL environment variable is required")
        return 0

    today = date.today()
    count = 0

    with psycopg2.connect(dsn) as con, con.cursor() as cur:
        # Find all users who have holdings with their portfolio value
        cur.execute("""
            SELECT
                p.user_id,
                SUM(
                    CASE
                        WHEN sr.price IS NOT NULL AND h.shares IS NOT NULL
                            THEN sr.price * h.shares
                        ELSE 0
                    END
                ) AS total_value,
                SUM(
                    CASE
                        WHEN h.cost_basis IS NOT NULL AND h.shares IS NOT NULL
                            THEN h.cost_basis * h.shares
                        ELSE 0
                    END
                ) AS total_cost,
                BOOL_AND(h.cost_basis IS NOT NULL) AS has_costs
            FROM portfolios p
            JOIN holdings h ON h.portfolio_id = p.id
            LEFT JOIN scan_results sr ON sr.ticker = h.ticker
            GROUP BY p.user_id
        """)

        rows = cur.fetchall()
        if not rows:
            logger.info("No users with holdings found")
            return 0

        for user_id, total_value, total_cost, has_costs in rows:
            total_value = round(float(total_value or 0), 2)
            total_cost = round(float(total_cost or 0), 2) if has_costs else None

            try:
                cur.execute(
                    """
                    INSERT INTO portfolio_snapshots (user_id, date, total_value, total_cost)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (user_id, date)
                    DO UPDATE SET total_value = EXCLUDED.total_value,
                                  total_cost  = EXCLUDED.total_cost,
                                  created_at  = NOW()
                    """,
                    (user_id, today, total_value, total_cost),
                )
                count += 1
                logger.debug(
                    "Snapshot %s for user %s: value=%.2f cost=%s",
                    today, user_id, total_value,
                    total_cost if has_costs else "N/A",
                )
            except Exception as exc:
                logger.error("Failed to create snapshot for user %s: %s", user_id, exc)

        con.commit()

    logger.info("Created %d portfolio snapshots for %s", count, today)
    return count


if __name__ == "__main__":
    run()
