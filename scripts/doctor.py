#!/usr/bin/env python3
"""
doctor.py — marketScan diagnostics CLI.

Runs local checks against all dependencies and prints a readable report.
Use for quick triage: "python scripts/doctor.py"

Returns exit code 0 if all checks pass, 1 if any fail.
"""
import os
import sys
import json

# Allow running from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx
from dotenv import load_dotenv

load_dotenv()

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"


def check(name: str, ok: bool, detail: str = ""):
    icon = f"{GREEN}✓{RESET}" if ok else f"{RED}✗{RESET}"
    status = f"{GREEN}OK{RESET}" if ok else f"{RED}FAIL{RESET}"
    detail_str = f" — {detail}" if detail else ""
    print(f"  {icon} {status}  {name}{detail_str}")
    return ok


def main():
    print("\nMarketScan Diagnostics\n")

    # ─── Environment ──────────────────────────────────────────────────
    print(" Environment:")
    all_ok = True

    supabase_url = os.getenv("SUPABASE_URL", "")
    supabase_key = os.getenv("SUPABASE_ANON_KEY", "")
    ok = bool(supabase_url and supabase_key)
    all_ok &= check("SUPABASE_URL + ANON_KEY", ok, "set" if ok else "MISSING")

    finnhub_key = os.getenv("FINNHUB_API_KEY", "")
    ok = bool(finnhub_key)
    all_ok &= check("FINNHUB_API_KEY", ok, "set" if ok else "MISSING")

    r2_key = os.getenv("R2_KEY_ID", "")
    r2_secret = os.getenv("R2_SECRET", "")
    ok = bool(r2_key and r2_secret)
    all_ok &= check("R2 credentials", ok, "set" if ok else "MISSING")

    deepseek_key = os.getenv("DEEPSEEK_API_KEY", "")
    ok = bool(deepseek_key)
    all_ok &= check("DEEPSEEK_API_KEY", ok, "set" if ok else "MISSING")

    gh_token = os.getenv("GH_DISPATCH_TOKEN", "")
    ok = bool(gh_token)
    all_ok &= check("GH_DISPATCH_TOKEN", ok, "set" if ok else "MISSING")

    # ─── External APIs ────────────────────────────────────────────────
    print("\n External APIs:")

    if finnhub_key:
        try:
            r = httpx.get(
                "https://finnhub.io/api/v1/quote",
                params={"symbol": "AAPL"},
                headers={"X-Finnhub-Token": finnhub_key},
                timeout=5,
            )
            ok = r.status_code == 200
            detail = f"HTTP {r.status_code}" if not ok else "svarar"
            all_ok &= check("Finnhub API", ok, detail)
        except Exception as e:
            all_ok &= check("Finnhub API", False, str(e))
    else:
        check("Finnhub API", False, "no key — skipped")

    # ─── Supabase ─────────────────────────────────────────────────────
    print("\n Database:")
    if supabase_url and supabase_key:
        try:
            from supabase import create_client
            sb = create_client(supabase_url, supabase_key)
            res = sb.table("scan_results").select("ticker", count="exact").limit(1).execute()
            count = res.count if hasattr(res, "count") else "?"
            all_ok &= check("Supabase connection", True, f"scan_results accessible ({count} rows)")
        except Exception as e:
            all_ok &= check("Supabase connection", False, str(e))
    else:
        check("Supabase connection", False, "no credentials — skipped")

    # ─── Pipelines ────────────────────────────────────────────────────
    print("\n Pipeline:")
    if supabase_url and supabase_key:
        try:
            from supabase import create_client
            sb = create_client(supabase_url, supabase_key)
            runs = sb.table("pipeline_runs").select("*").order("started_at", desc=True).limit(1).execute()
            if runs.data:
                r = runs.data[0]
                all_ok &= check("Last pipeline run", r.get("status") == "success",
                                f"{r.get('run_type')} @ {r.get('started_at', '?')} — {r.get('status', '?')}")
            else:
                all_ok &= check("Pipeline runs", False, "INGA pipeline-körningar — kör pipeline först")
        except Exception as e:
            all_ok &= check("Pipeline check", False, str(e))
    else:
        check("Pipeline check", False, "no credentials — skipped")

    # ─── Summary ──────────────────────────────────────────────────────
    print(f"\n {'='*40}")
    if all_ok:
        print(f" {GREEN}All checks passed.{RESET}")
    else:
        print(f" {RED}Some checks failed.{RESET}")

    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
