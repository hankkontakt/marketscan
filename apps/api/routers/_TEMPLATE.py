"""
ROUTER TEMPLATE — copy this file to start a new user-data router the safe way.

This template bakes in every convention that was learned the hard way. Follow
it and your endpoints get correct auth, RLS, error handling, and CORS for free.

To use:
  1. Copy to apps/api/routers/<feature>.py and rename `router` prefix/tags.
  2. Register it in apps/api/main.py:  app.include_router(<feature>.router)
     (prefix is set HERE via APIRouter(prefix=...), so don't double-prefix.)
  3. If it needs a new table, add a migration that:
        CREATE TABLE ...;
        ALTER TABLE <t> ENABLE ROW LEVEL SECURITY;
        CREATE POLICY "<t>_own" ON <t> FOR ALL
          USING ((select auth.uid()) = user_id)
          WITH CHECK ((select auth.uid()) = user_id);
        -- grants are covered by 023's ALTER DEFAULT PRIVILEGES, but be explicit:
        GRANT SELECT, INSERT, UPDATE, DELETE ON <t> TO authenticated;
  4. Verify: `python scripts/smoke_test.py http://localhost:8000`.

THE RULES (why each matters):
  • Use `def`, NOT `async def`, when the body only calls the synchronous
    Supabase SDK. FastAPI runs `def` handlers in a threadpool; a sync call in an
    `async def` blocks the event loop. Use `async def` ONLY if you `await`
    something (httpx, asyncio.gather).
  • User data → Depends(get_current_user) + Depends(get_user_supabase). The JWT
    is forwarded to PostgREST so RLS enforces per-user isolation.
  • Service role (Depends(get_supabase_admin)) bypasses RLS — use ONLY behind
    Depends(require_admin), never in a user-facing read/write.
  • Wrap DB calls with apps.api.core.db helpers so errors become readable
    HTTPExceptions (with CORS), never an opaque CORS-less 500 ("Nätverksfel").
  • Always set response_model so the contract is explicit and validated.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel

from apps.api.core import db
from apps.api.core.security import get_current_user, User
from apps.api.dependencies import get_user_supabase

# prefix lives here — main.py just does app.include_router(<feature>.router)
router = APIRouter(prefix="/api/widgets", tags=["widgets"])


# ─── Schemas ──────────────────────────────────────────────────────────────────

class WidgetIn(BaseModel):
    name: str
    color: str | None = None


class WidgetOut(BaseModel):
    id: str
    name: str
    color: str | None = None


# ─── Routes ───────────────────────────────────────────────────────────────────

@router.get("", response_model=list[WidgetOut])
def list_widgets(
    user: User = Depends(get_current_user),
    sb=Depends(get_user_supabase),
):
    """List the current user's widgets (RLS scopes to user automatically)."""
    return db.rows(
        sb.table("widgets").select("*").eq("user_id", user.id).order("name"),
        context="list_widgets",
    )


@router.get("/{widget_id}", response_model=WidgetOut)
def get_widget(
    widget_id: str,
    user: User = Depends(get_current_user),
    sb=Depends(get_user_supabase),
):
    """Fetch one widget or 404. The user_id filter is defence-in-depth on top
    of RLS — ownership is enforced even if a policy is ever misconfigured."""
    return db.one_or_404(
        sb.table("widgets").select("*").eq("id", widget_id).eq("user_id", user.id),
        what="Widget",
        context="get_widget",
    )


@router.post("", response_model=WidgetOut, status_code=status.HTTP_201_CREATED)
def create_widget(
    body: WidgetIn,
    user: User = Depends(get_current_user),
    sb=Depends(get_user_supabase),
):
    """Create a widget for the current user."""
    payload = {"user_id": user.id, "name": body.name, "color": body.color}
    return db.one_or_404(
        sb.table("widgets").insert(payload),
        what="Widget",
        context="create_widget",
    )


@router.delete("/{widget_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_widget(
    widget_id: str,
    user: User = Depends(get_current_user),
    sb=Depends(get_user_supabase),
):
    """Delete one of the user's own widgets (ownership-checked)."""
    db.one_or_404(
        sb.table("widgets").delete().eq("id", widget_id).eq("user_id", user.id),
        what="Widget",
        context="delete_widget",
    )
