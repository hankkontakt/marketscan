"""
Rate limiting configuration for FastAPI using slowapi (optional).

Tiers:
  - AI endpoints: 10 req/min/user (DeepSeek costs money)
  - Admin endpoints: 30 req/min/user
  - Auth/profile endpoints: 20 req/min/IP (brute force protection)
  - General endpoints: 100 req/min/IP

Gracefully degrades when slowapi is not installed.
"""
import logging
from fastapi import FastAPI

logger = logging.getLogger(__name__)

try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded
    from slowapi.util import get_remote_address

    limiter = Limiter(
        key_func=get_remote_address,
        default_limits=["100/minute"],
        enabled=True,
    )
    _slowapi_available = True
except ImportError:
    logger.warning("slowapi not installed — rate limiting disabled")
    limiter = None
    _slowapi_available = False
    RateLimitExceeded = None
    _rate_limit_exceeded_handler = None


def add_rate_limiting(app: FastAPI) -> None:
    """Wire rate limiting into a FastAPI application (no-op if slowapi unavailable)."""
    if not _slowapi_available or limiter is None:
        return
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
