"""
Rate limiting configuration for FastAPI using slowapi.

Tiers:
  - AI endpoints: 10 req/min/user (DeepSeek costs money)
  - Admin endpoints: 30 req/min/user
  - Auth/profile endpoints: 20 req/min/IP (brute force protection)
  - General endpoints: 100 req/min/IP
"""
from fastapi import FastAPI
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["100/minute"],
    enabled=True,
)


def add_rate_limiting(app: FastAPI) -> None:
    """Wire rate limiting into a FastAPI application."""
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
