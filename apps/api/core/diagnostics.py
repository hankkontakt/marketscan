"""
System self-diagnostics.

ONE admin call that surfaces the config / permission / migration problems that
otherwise take a long debugging session to pin down. Built after a "Nätverksfel"
turned out to be a missing table GRANT (Postgres 42501) that was invisible to
every layer above the database.

Key idea: probe each user table with the AUTHENTICATED client (the admin's JWT
forwarded to PostgREST). The service_role client bypasses RLS *and* grants, so
it can't reveal a missing grant — but an authenticated read hits the exact same
permission path a real user does. A 42501 there is the smoking gun.

Returns a plain dict (JSON-serialisable) with an `issues` list. Empty issues
list == healthy.
"""
from __future__ import annotations

import os
from typing import Any

from apps.api.core.config import settings

# Tables every logged-in user must be able to read/write (RLS-scoped per user).
USER_TABLES = [
    "profiles", "portfolios", "holdings", "transactions", "watchlist",
    "price_alerts", "saved_screens", "notifications", "notification_preferences",
    "fund_holdings", "user_ticker_requests", "portfolio_snapshots",
]

# Tables meant to be publicly readable (no RLS by design).
PUBLIC_TABLES = ["scan_results"]

# Marker table -> the migration that introduces it. Lets us infer, without DB
# introspection, which manual migrations have actually been run.
MIGRATION_MARKERS = {
    "014_transactions": "transactions",
    "018_rls_hardening": "client_errors",
    "019_risk_analytics": "portfolio_risk_cache",
    "020_smart_alerts": "alert_rules",
    "021_strategy_lab": "strategies",
    "022_fund_holdings": "fund_holdings",
}

# Env vars that must be present for core features to work, with the feature
# they unlock (shown to the admin so a missing one is self-explanatory).
REQUIRED_ENV = {
    "SUPABASE_URL": "Databasanslutning",
    "SUPABASE_ANON_KEY": "Publik läsning / auth",
    "SUPABASE_SERVICE_KEY": "Admin/cron-skrivningar (kringgår RLS)",
    "SUPABASE_JWT_SECRET": "JWT-verifiering (inloggning)",
}
OPTIONAL_ENV = {
    "FINNHUB_API_KEY": "Aktiekurser/index",
    "DEEPSEEK_API_KEY": "AI-analys",
    "R2_KEY_ID": "Parquet-lagring (R2)",
    "GH_DISPATCH_TOKEN": "Pipeline-trigger från admin",
}


def _msg(e: Exception) -> str:
    return str(e)[:300]


def _env_present(name: str) -> bool:
    val = getattr(settings, name, None)
    if val:
        return True
    return bool(os.environ.get(name, ""))


def run_diagnostics(sb_user: Any, sb_admin: Any) -> dict:
    """
    sb_user  : authenticated-context client (admin JWT forwarded) — reveals grants/RLS.
    sb_admin : service_role client — reveals existence/row counts (bypasses RLS).
    """
    report: dict = {
        "ok": True,
        "issues": [],
        "env": {"required": {}, "optional": {}},
        "tables": {},
        "migrations": {},
    }

    # ── 1. Environment variables ───────────────────────────────────────────────
    for name, feature in REQUIRED_ENV.items():
        present = _env_present(name)
        report["env"]["required"][name] = {"present": present, "feature": feature}
        if not present:
            report["issues"].append(
                f"ENV saknas: {name} — krävs för {feature}. Sätt i Vercel (marketscan-api)."
            )
    for name, feature in OPTIONAL_ENV.items():
        report["env"]["optional"][name] = {"present": _env_present(name), "feature": feature}

    # ── 2. Tables: existence + authenticated-context reachability ──────────────
    for t in USER_TABLES + PUBLIC_TABLES:
        entry: dict = {}

        # Existence + row count via service_role (bypasses RLS & grants).
        try:
            r = sb_admin.table(t).select("*", count="exact").limit(0).execute()
            entry["exists"] = True
            entry["rows"] = r.count
        except Exception as e:
            entry["exists"] = False
            entry["error"] = _msg(e)
            report["issues"].append(f"TABELL {t}: saknas eller oläsbar för service_role — {_msg(e)}")
            report["tables"][t] = entry
            continue

        # Authenticated-context read — the exact path a real user hits.
        # A 42501 here means the GRANT is missing (run migration 023).
        try:
            sb_user.table(t).select("*").limit(1).execute()
            entry["authenticated_read"] = "ok"
        except Exception as e:
            m = _msg(e)
            entry["authenticated_read"] = "FAIL"
            entry["auth_error"] = m
            hint = ""
            if "42501" in m or "permission denied" in m:
                hint = " → kör migration 023_grant_table_privileges.sql i Supabase SQL Editor"
            report["issues"].append(f"TABELL {t}: authenticated-läsning nekad — {m}{hint}")

        report["tables"][t] = entry

    # ── 3. Migration state (inferred from marker tables) ───────────────────────
    for mig, marker in MIGRATION_MARKERS.items():
        cached = report["tables"].get(marker, {}).get("exists")
        if cached is None:
            try:
                sb_admin.table(marker).select("*").limit(0).execute()
                cached = True
            except Exception:
                cached = False
        report["migrations"][mig] = cached
        if not cached:
            report["issues"].append(
                f"MIGRATION {mig}: verkar inte körd (tabellen '{marker}' saknas)."
            )

    report["ok"] = len(report["issues"]) == 0
    report["summary"] = (
        "Allt OK" if report["ok"] else f"{len(report['issues'])} problem hittade"
    )
    return report
