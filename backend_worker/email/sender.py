"""
Email sender — sends via Resend.
No tracking on transactional emails. Plain-text alternative included.
"""
import os
import logging
import json
import urllib.request
import urllib.error

from . import components

logger = logging.getLogger(__name__)

RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
RESEND_FROM = os.environ.get("RESEND_FROM", "onboarding@resend.dev")
APP_URL = os.environ.get("APP_URL", "https://marketscan.vercel.app")
UNSUBSCRIBE_URL = os.environ.get("UNSUBSCRIBE_URL", "")


def send(to: str, subject: str, html_body: str, plain_text: str | None = None) -> bool:
    """Send an email via Resend API. Returns True if successful."""
    if not RESEND_API_KEY:
        logger.warning("RESEND_API_KEY not set — email not sent")
        return False

    # Resend API endpoint
    url = "https://api.resend.com/emails"

    # Clean HTML: replace template variables
    html_body = html_body.replace("{app_url}", APP_URL).replace("{unsubscribe_url}", UNSUBSCRIBE_URL)
    plain_text = plain_text or _strip_html(html_body)

    payload = json.dumps({
        "from": RESEND_FROM,
        "to": [to],
        "subject": subject,
        "html": html_body,
        "text": plain_text,
    }).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Authorization": f"Bearer {RESEND_API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            logger.info("Email sent to %s: %s (status=%d)", to, subject, resp.status)
            return True
    except urllib.error.HTTPError as e:
        logger.error("Resend API error %d: %s", e.code, e.read().decode())
        return False
    except urllib.error.URLError as e:
        logger.error("Resend connection error: %s", e.reason)
        return False


def send_notification(
    to: str,
    template_name: str,
    **kwargs,
) -> bool:
    """Send a notification email using a registered template."""
    template_fn = components.TEMPLATES.get(template_name)
    if not template_fn:
        logger.error("Unknown email template: %s", template_name)
        return False

    subject, html = template_fn(**kwargs)
    return send(to, subject, html)


def _strip_html(html: str) -> str:
    """Basic HTML-to-text stripping for plain-text alternative."""
    import re
    text = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text
