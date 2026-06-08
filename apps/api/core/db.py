"""
User-data access helpers with consistent, debuggable error handling.

Use these in route handlers instead of calling `sb.table(...).execute()` bare.
They translate raw Postgres / PostgREST errors into clean HTTPExceptions with
actionable Swedish messages and the right HTTP status — so a DB problem reaches
the client as a READABLE error (and is logged with context), never as an opaque
500 or a CORS-less "Nätverksfel".

This module exists because a missing table GRANT (Postgres 42501) once hid
behind a generic "Nätverksfel" for a very long debugging session. With these
helpers, that exact error now says: "Databasrättighet saknas … kör migration
023" — diagnosable at a glance.

Typical use:

    from apps.api.core import db

    @router.get("/widgets")
    def list_widgets(user=Depends(get_current_user), sb=Depends(get_user_supabase)):
        return db.rows(sb.table("widgets").select("*").eq("user_id", user.id),
                       context="list_widgets")

    @router.get("/widgets/{wid}")
    def get_widget(wid: str, user=Depends(get_current_user), sb=Depends(get_user_supabase)):
        return db.one_or_404(
            sb.table("widgets").select("*").eq("id", wid).eq("user_id", user.id),
            what="Widget",
        )
"""
from __future__ import annotations

import logging
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)

# Postgres / PostgREST error code -> (http_status, message, hint)
_PG_ERRORS: dict[str, tuple[int, str, str | None]] = {
    "42501": (
        status.HTTP_502_BAD_GATEWAY,
        "Databasrättighet saknas (permission denied)",
        "Kör migration 023_grant_table_privileges.sql i Supabase SQL Editor.",
    ),
    "42P01": (
        status.HTTP_502_BAD_GATEWAY,
        "Tabellen finns inte",
        "En migration är troligen inte körd — se GET /api/admin/diagnostics/deep.",
    ),
    "42703": (
        status.HTTP_502_BAD_GATEWAY,
        "Kolumnen finns inte",
        "Schema och kod är osynkade — en migration saknas eller koden är fel.",
    ),
    "23505": (status.HTTP_409_CONFLICT, "Posten finns redan", None),
    "23503": (status.HTTP_400_BAD_REQUEST, "Refererad post saknas (foreign key)", None),
    "23514": (status.HTTP_400_BAD_REQUEST, "Värdet bröt mot en databasregel (check)", None),
    "23502": (status.HTTP_400_BAD_REQUEST, "Obligatoriskt fält saknas (not null)", None),
}


def _extract_code(err: Exception) -> str | None:
    """Pull a Postgres SQLSTATE / PostgREST code out of a supabase-py error."""
    code = getattr(err, "code", None)
    if code:
        return str(code)
    # APIError often stringifies to a dict containing 'code': '42501'
    msg = str(err)
    for c in _PG_ERRORS:
        if c in msg:
            return c
    return None


def run(query, *, context: str = ""):
    """Execute a Supabase query builder, translating errors to HTTPException.

    `context` is a short label (usually the handler name) included in logs and,
    for known errors, in the client message — so failures are traceable.
    """
    try:
        return query.execute()
    except HTTPException:
        raise
    except Exception as e:  # supabase APIError, httpx errors, etc.
        code = _extract_code(e)
        if code in _PG_ERRORS:
            http_status, msg, hint = _PG_ERRORS[code]
            logger.error("DB %s in %s: %s", code, context or "?", str(e)[:300])
            detail = f"{msg}" + (f" [{context}]" if context else "")
            if hint:
                detail += f" — {hint}"
            raise HTTPException(http_status, detail)
        logger.exception("Unexpected DB error in %s", context or "?")
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            f"Databasfel{(' i ' + context) if context else ''}: {str(e)[:200]}",
        )


def rows(query, *, context: str = "") -> list:
    """Execute and return the row list (empty list if none)."""
    return run(query, context=context).data or []


def one_or_404(query, *, what: str = "Posten", context: str = ""):
    """Execute and return the first row, or raise 404 if there are none."""
    res = run(query, context=context)
    if not res.data:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"{what} hittades inte")
    return res.data[0]


def first_or_none(query, *, context: str = ""):
    """Execute and return the first row or None (no 404)."""
    res = run(query, context=context)
    return res.data[0] if res.data else None
