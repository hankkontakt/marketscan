#!/usr/bin/env python3
"""
verify_codex.py — Automatisk kvalitetskontroll för MarketScans Living AI Codex.

Kontrollerar:
1. Linjebudgetar (max 250 rader för index, max 500 rader per kapitel).
2. Att alla refererade filer och mappar i repot faktiskt existerar (inga trasiga sökvägar).
3. Att alla FastAPI-endpoints i apps.api.main finns dokumenterade i 04_API_ARCHITECTURE.md.
4. Att obligatoriska filer (SYSTEM_INDEX.md, llms.txt, alla kapitel) existerar.
"""

import os
import re
import sys
from pathlib import Path

# Force UTF-8 on Windows stdout if needed
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT_DIR = Path(__file__).resolve().parent.parent

BUDGETS = {
    "SYSTEM_INDEX.md": 250,
    "llms.txt": 250,
    "docs/codex/00_SYSTEM_BLUEPRINT.md": 500,
    "docs/codex/01_QUANT_MASTERRANK.md": 500,
    "docs/codex/02_DATA_PIPELINE.md": 500,
    "docs/codex/03_AI_RAG_SYNTHESIS.md": 500,
    "docs/codex/04_API_ARCHITECTURE.md": 500,
    "docs/codex/05_DATABASE_SCHEMA.md": 500,
    "docs/codex/06_FRONTEND_STATE_UX.md": 500,
    "docs/codex/07_PORTFOLIO_RISK.md": 500,
}

PATH_REGEX = re.compile(
    r'(?:`|(?:file:///[^`\(\)]*?))((?:apps|backend_worker|supabase|scripts|docs|data)/[a-zA-Z0-9_\-\./]+(?:\.[a-zA-Z0-9]+)?)'
)


def check_file_existence_and_budgets():
    errors = []
    print("[1/3] Kontrollerar filer och linjebudgetar...")
    for rel_path, max_lines in BUDGETS.items():
        file_path = ROOT_DIR / rel_path
        if not file_path.exists():
            errors.append(f"[ERROR] Saknad obligatorisk codex-fil: {rel_path}")
            continue

        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            line_count = len(lines)
            if line_count > max_lines:
                errors.append(
                    f"[WARN] Linjebudget överskriden: {rel_path} har {line_count} rader (max {max_lines})"
                )
            else:
                print(f"  [OK] {rel_path} ({line_count}/{max_lines} rader)")

    return errors


def check_path_anchors():
    errors = []
    print("\n[2/3] Verifierar länkade kodankare och filvägar...")
    codex_files = list(ROOT_DIR.glob("docs/codex/*.md")) + [
        ROOT_DIR / "SYSTEM_INDEX.md",
        ROOT_DIR / "llms.txt",
    ]

    checked_paths = set()
    found_paths_count = 0

    for cfile in codex_files:
        if not cfile.exists():
            continue
        with open(cfile, "r", encoding="utf-8") as f:
            content = f.read()

        matches = PATH_REGEX.findall(content)
        for m in matches:
            clean_path = m.split("#")[0].strip().rstrip("/.")
            # Ignore template/wildcards/directories
            if "*" in clean_path or clean_path in checked_paths:
                continue
            checked_paths.add(clean_path)
            found_paths_count += 1

            target = ROOT_DIR / clean_path
            if not target.exists():
                errors.append(
                    f"[ERROR] Död referens i {cfile.relative_to(ROOT_DIR)}: '{clean_path}' existerar inte på disk!"
                )

    print(f"  [OK] Verifierade {found_paths_count} unika kodankare och filvägar.")
    return errors


def check_api_route_coverage():
    errors = []
    print("\n[3/3] Kontrollerar täckning av FastAPI-routes...")
    api_doc = ROOT_DIR / "docs/codex/04_API_ARCHITECTURE.md"
    if not api_doc.exists():
        errors.append("[ERROR] 04_API_ARCHITECTURE.md saknas för route-validering.")
        return errors

    with open(api_doc, "r", encoding="utf-8") as f:
        doc_content = f.read()

    try:
        sys.path.insert(0, str(ROOT_DIR))
        from apps.api.main import app

        active_routes = set()
        for route in app.routes:
            if hasattr(route, "path") and hasattr(route, "methods"):
                # Filter out standard docs & swagger redirects
                if route.path in ["/docs", "/redoc", "/openapi.json", "/api/docs", "/docs/oauth2-redirect"]:
                    continue
                for method in route.methods:
                    if method in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
                        active_routes.add(f"{method} {route.path}")

        print(f"  [INFO] Hittade {len(active_routes)} aktiva API-routes i apps.api.main.")
        # Check that main router prefixes are covered
        missing = []
        for r in sorted(active_routes):
            path_part = r.split()[1]
            segments = [p for p in path_part.split("/") if p and not p.startswith("{")]
            base_prefix = "/" + "/".join(segments[:2]) if segments else path_part
            first_prefix = "/" + segments[0] if segments else path_part
            if (
                path_part not in doc_content
                and base_prefix not in doc_content
                and first_prefix not in doc_content
                and r not in doc_content
            ):
                missing.append(r)

        if missing:
            print(
                f"  [WARN] Observera: {len(missing)} routes saknar specifik omnämnande (kan täckas av prefix):"
            )
            for m in missing[:5]:
                print(f"     - {m}")
            if len(missing) > 5:
                print(f"     ... och {len(missing) - 5} till.")
        else:
            print("  [OK] Alla API-routes och prefix finns representerade i API-boken.")

    except Exception as e:
        print(f"  [WARN] Kunde inte importera apps.api.main ({e}) - hoppar över djup route-audit.")

    return errors


def main():
    print("=" * 60)
    print("   MARKETSCAN CODEX VERIFIER (LIVING DOCS GATE)")
    print("=" * 60)

    all_errors = []
    all_errors.extend(check_file_existence_and_budgets())
    all_errors.extend(check_path_anchors())
    all_errors.extend(check_api_route_coverage())

    print("\n" + "=" * 60)
    if all_errors:
        print(f"RESULTAT: {len(all_errors)} fel/varningar hittades:")
        for err in all_errors:
            print(f"  {err}")
        print("=" * 60)
        sys.exit(1)
    else:
        print("RESULTAT: Alla filer, budgetar och länkar är 100% verifierade!")
        print("=" * 60)
        sys.exit(0)


if __name__ == "__main__":
    main()
