"""
Price alert checker -- runs every 30min on weekdays via GitHub Actions.
Checks active alerts against current prices, triggers when condition met.
Now also creates in-app notifications and sends email when triggered.
"""
import os
import sys
import logging
from datetime import datetime, timezone
from decimal import Decimal

import psycopg2

logger = logging.getLogger(__name__)


def get_active_alerts(cursor) -> list[tuple]:
    """Fetch all active price alerts from the database."""
    cursor.execute(
        "SELECT id, user_id, ticker, condition, target_price, note "
        "FROM price_alerts WHERE active = TRUE"
    )
    return cursor.fetchall()


def get_current_prices(cursor, tickers: list[str]) -> dict[str, float | None]:
    """Fetch current prices from scan_results for the given tickers."""
    if not tickers:
        return {}
    placeholders = ",".join("%s" for _ in tickers)
    cursor.execute(
        f"SELECT ticker, price FROM scan_results WHERE ticker IN ({placeholders})",
        list(tickers),
    )
    result: dict[str, float | None] = {}
    for row in cursor.fetchall():
        ticker, price = row
        if price is not None:
            result[ticker] = float(price) if isinstance(price, Decimal) else price
        else:
            result[ticker] = None
    return result


def fetch_price_yfinance(ticker: str) -> float | None:
    """Fallback: fetch current price via yfinance for tickers not in scan_results."""
    try:
        import yfinance as yf
        stock = yf.Ticker(ticker)
        info = stock.info
        price = info.get("currentPrice") or info.get("regularMarketPrice")
        if price is not None:
            logger.info("yfinance fallback for %s: current price = %s", ticker, price)
            return float(price)
    except Exception as exc:
        logger.debug("yfinance fallback failed for %s: %s", ticker, exc)
    return None


def check_and_trigger(
    cursor,
    alert_id: str,
    user_id: str,
    ticker: str,
    current_price: float,
    target_price: float,
    condition: str,
    note: str | None,
) -> bool:
    """Check if alert condition is met, mark as triggered, and create notification."""
    triggered = False
    if condition == "above" and current_price >= target_price:
        triggered = True
    elif condition == "below" and current_price <= target_price:
        triggered = True

    if triggered:
        # Mark alert as triggered
        cursor.execute(
            "UPDATE price_alerts SET active = FALSE, triggered_at = %s WHERE id = %s",
            (datetime.now(timezone.utc), alert_id),
        )

        # Create in-app notification
        direction = "över" if condition == "above" else "under"
        title = f"Prisbevakning: {ticker}"
        body = f"Kursen nådde {direction} {target_price:.2f} kr (aktuell: {current_price:.2f} kr)"
        if note:
            body += f" — {note}"

        cursor.execute(
            "INSERT INTO notifications (user_id, type, title, body, link) "
            "VALUES (%s, 'price_alert', %s, %s, %s)",
            (user_id, title, body, f"/aktie/{ticker}"),
        )

        # Try sending email notification if user has opted in
        _try_send_email_alert(cursor, user_id, ticker, condition, target_price, current_price, note)

    return triggered


def _try_send_email_alert(
    cursor, user_id: str, ticker: str, condition: str,
    target_price: float, current_price: float, note: str | None,
) -> None:
    """Send email notification if user has opted in."""
    try:
        cursor.execute(
            "SELECT email_opt_in FROM profiles WHERE id = %s",
            (user_id,),
        )
        profile = cursor.fetchone()
        if not profile or not profile[0]:
            return

        # Get user email from auth.users
        cursor.execute(
            "SELECT email FROM auth.users WHERE id = %s",
            (user_id,),
        )
        user_row = cursor.fetchone()
        if not user_row or not user_row[0]:
            return
        email = user_row[0]

        # Same-connection, try to import sender
        try:
            from backend_worker.email.sender import send_notification
            send_notification(
                to=email,
                template_name="price_alert",
                ticker=ticker,
                name=ticker,
                condition=condition,
                target_price=target_price,
                current_price=current_price,
                note=note,
            )
        except Exception:
            logger.exception("Failed to send email notification")
    except Exception:
        logger.exception("Failed to check email opt-in")


def run_check(dsn: str | None = None) -> tuple[int, int]:
    """
    Run the full price alert check cycle.
    Returns (checked_count, triggered_count).
    """
    dsn = dsn or os.environ["DATABASE_URL"]

    with psycopg2.connect(dsn) as conn, conn.cursor() as cur:
        alerts = get_active_alerts(cur)
        if not alerts:
            logger.info("No active alerts to check")
            return 0, 0

        unique_tickers = sorted({a[2] for a in alerts})
        logger.info(
            "Found %d active alerts across %d unique tickers",
            len(alerts), len(unique_tickers),
        )

        # Fetch prices from scan_results
        prices = get_current_prices(cur, unique_tickers)

        # Fallback to yfinance for tickers missing from scan_results
        missing = [t for t in unique_tickers if t not in prices or prices[t] is None]
        if missing:
            logger.info("Tickers not found in scan_results, trying yfinance: %s", missing)
            for ticker in missing:
                price = fetch_price_yfinance(ticker)
                if price is not None:
                    prices[ticker] = price

        checked = 0
        triggered = 0
        for alert in alerts:
            alert_id, user_id, ticker, condition, target_price, note = alert
            current_price = prices.get(ticker)

            if current_price is None:
                logger.warning("No price available for %s (alert %s) -- skipping", ticker, alert_id)
                continue

            target = float(target_price) if isinstance(target_price, Decimal) else target_price
            checked += 1

            if check_and_trigger(cur, alert_id, user_id, ticker, current_price, target, condition, note):
                triggered += 1
                logger.info(
                    "TRIGGERED alert %s: %s %s %.2f (current=%.2f, target=%.2f)",
                    alert_id, ticker, condition, target, current_price, target,
                )

        conn.commit()

    logger.info("Price alert check complete: %d checked, %d triggered", checked, triggered)
    return checked, triggered


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        logger.error("DATABASE_URL is not set. Set it in .env or as an environment variable.")
        sys.exit(1)

    checked, triggered = run_check(dsn)
    logger.info("Done: %d checked, %d triggered", checked, triggered)
