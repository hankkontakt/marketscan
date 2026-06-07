"""
Email components — reusable HTML building blocks for email templates.
No emojis, clean Lysa-style, single accent color.
"""
from datetime import date
from .layout import layout, section, metric_row, stock_table, button

TEMPLATES: dict[str, callable] = {}


def template(name: str):
    """Register an email template function."""
    def decorator(fn):
        TEMPLATES[name] = fn
        return fn
    return decorator


@template("price_alert")
def price_alert_email(ticker: str, name: str, condition: str, target_price: float, current_price: float, note: str | None = None) -> tuple[str, str]:
    """Price alert triggered email. Returns (subject, html_body)."""
    direction = "över" if condition == "above" else "under"
    subject = f"Prisbevakning: {ticker} nådde {direction} {target_price:.2f} kr"
    safe_note = _escape_html(note) if note else None
    body = layout(f"""
        {section(f'Din prisbevakning för <strong>{_escape_html(name)}</strong> ({_escape_html(ticker)}) har löpt ut.')}
        {metric_row("Bevakad kurs", f"{direction.upper()} {target_price:.2f} kr")}
        {metric_row("Aktuell kurs", f"{current_price:.2f} kr")}
        {metric_row("Datum", date.today().isoformat())}
        {safe_note and section(f'Anteckning: {safe_note}') or ''}
        {button("Visa aktien", f"{{app_url}}/aktie/{ticker}")}
    """)
    return subject, body


@template("earnings_reminder")
def earnings_reminder_email(ticker: str, name: str, report_date: str) -> tuple[str, str]:
    """Upcoming earnings report reminder. Returns (subject, html_body)."""
    subject = f"Rapportdag: {ticker} rapporterar {report_date}"
    body = layout(f"""
        {section(f'<strong>{name}</strong> ({ticker}) rapporterar den <strong>{report_date}</strong>.')}
        {section('Håll utkik efter kvartalsrapporten för att se hur bolaget utvecklas.')}
        {button("Visa aktien", f"{{app_url}}/aktie/{ticker}")}
    """)
    return subject, body


@template("score_change")
def score_change_email(ticker: str, name: str, old_score: float, new_score: float, signal: str) -> tuple[str, str]:
    """Score change notification. Returns (subject, html_body)."""
    direction = "ökat" if new_score > old_score else "minskat"
    subject = f"Betygsändring: {ticker} ({name}) — {new_score:.0f}/100"
    safe_name = _escape_html(name)
    body = layout(f"""
        {section(f'MarketScan-betyget för <strong>{safe_name}</strong> ({_escape_html(ticker)}) har {direction}.')}
        {metric_row("Tidigare betyg", f"{old_score:.0f}/100")}
        {metric_row("Nytt betyg", f"{new_score:.0f}/100")}
        {metric_row("Köpläge", signal)}
        {button("Visa analysen", f"{{app_url}}/aktie/{ticker}")}
    """)
    return subject, body


@template("daily_digest")
def daily_digest_email(
    top_movers: list[tuple[str, str, str, str]],
    score_changes: list[tuple[str, str, float, float]],
    date_str: str | None = None,
) -> tuple[str, str]:
    """Daily digest with top movers and score changes. Returns (subject, html_body).
    score_changes: list of (ticker, name, old_score, new_score)
    """
    d = date_str or date.today().isoformat()
    subject = f"MarketScan — daglig sammanfattning {d}"
    sections = [f"<h2 style='font-size: 14px; margin: 16px 0 8px 0; color: #14181F;'>Dagens marknad</h2>"]

    if top_movers:
        sections.append(stock_table(top_movers))

    if score_changes:
        sections.append("<h2 style='font-size: 14px; margin: 16px 0 8px 0; color: #14181F;'>Betygsförändringar</h2>")
        rows = [(t, n, f"{o:.0f} → {n:.0f}" if isinstance(n, (int, float)) else str(n), "") for t, n, o, n2 in score_changes]
        sections.append(stock_table(rows))

    body = layout("".join(sections))
    return subject, body


def _escape_html(text: str | None) -> str:
    """Escape HTML special characters in user-provided text."""
    if text is None:
        return ""
    return (
        text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#x27;")
    )
