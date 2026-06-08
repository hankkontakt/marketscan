#!/usr/bin/env python3
"""
API smoke test — one command that probes the whole API surface and tells you
exactly what's broken.

The point: distinguish the failure *kinds* that matter.
  - A public endpoint must return 200.
  - An auth/admin endpoint, called WITHOUT a token, must return 401/403 — that
    proves it is both reachable AND protected. A 500 there means the auth layer
    itself is crashing (e.g. a missing JWT secret). A 404 means a routing/prefix
    bug. Either is a real problem the smoke test catches in seconds.

Usage:
  python scripts/smoke_test.py                         # probe live API
  python scripts/smoke_test.py http://localhost:8000   # probe local
  SMOKE_JWT=<token> python scripts/smoke_test.py        # also test authed reads

Exit code is non-zero if any probe FAILs, so this works in CI / pre-deploy.
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request

DEFAULT_BASE = "https://marketscan-api.vercel.app"

# (method, path, body|None)  — grouped by the status we EXPECT.
PUBLIC = [  # expect 200
    ("GET", "/api/health", None),
    ("GET", "/api/scan?limit=3", None),
    ("GET", "/api/scan/sectors", None),
    ("GET", "/api/scan/countries", None),
    ("GET", "/api/scan/meta", None),
    ("GET", "/api/stocks?q=INVE-B.ST", None),
    ("GET", "/api/stocks/search?q=invest", None),
    ("GET", "/api/markets/indices", None),
    ("GET", "/api/markets/sectors", None),
    ("GET", "/api/markets/top-movers", None),
    ("GET", "/api/calendar/earnings", None),
    ("GET", "/api/calendar/ipo", None),
    ("GET", "/api/smallcap", None),
]
AUTH_REQUIRED = [  # expect 401/403 without a token
    ("GET", "/api/portfolio", None),
    ("GET", "/api/portfolio/funds", None),
    ("GET", "/api/watchlist", None),
    ("GET", "/api/alerts", None),
    ("GET", "/api/notifications", None),
    ("GET", "/api/profile", None),
    ("GET", "/api/transactions", None),
    ("GET", "/api/screens", None),
    ("POST", "/api/portfolio/import/confirm", {"rows": []}),
]
ADMIN_REQUIRED = [  # expect 401/403 without a token
    ("GET", "/api/admin/status", None),
    ("GET", "/api/admin/diagnostics/deep", None),
    ("GET", "/api/debug/health", None),
]


def probe(base: str, method: str, path: str, body, token: str | None):
    url = base + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    req.add_header("Origin", "https://web-hankkontakts-projects.vercel.app")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=40) as resp:
            ms = int((time.monotonic() - t0) * 1000)
            return resp.status, resp.read(300).decode("utf-8", "replace"), ms, dict(resp.headers)
    except urllib.error.HTTPError as e:
        ms = int((time.monotonic() - t0) * 1000)
        return e.code, e.read(300).decode("utf-8", "replace"), ms, dict(e.headers)
    except Exception as e:
        ms = int((time.monotonic() - t0) * 1000)
        return None, f"{type(e).__name__}: {e}", ms, {}


def check(label, expected, base, probes, token=None):
    results = []
    for method, path, body in probes:
        status, snippet, ms, headers = probe(base, method, path, body, token)
        ok = status in expected and (status is None or status < 500)
        # CORS header sanity on cross-origin calls
        cors = "ACAO" if headers.get("Access-Control-Allow-Origin") else "no-CORS"
        results.append((ok, method, path, status, ms, cors, snippet.replace("\n", " ")[:90]))
    return results


def main() -> int:
    base = DEFAULT_BASE
    for a in sys.argv[1:]:
        if a.startswith("http"):
            base = a.rstrip("/")
    token = os.environ.get("SMOKE_JWT")

    print(f"\nSmoke test  →  {base}\n" + "=" * 78)
    groups = [
        ("PUBLIC (expect 200)", {200}, PUBLIC, None),
        ("AUTH-REQUIRED, no token (expect 401/403)", {401, 403}, AUTH_REQUIRED, None),
        ("ADMIN-REQUIRED, no token (expect 401/403)", {401, 403}, ADMIN_REQUIRED, None),
    ]
    all_results = []
    for title, expected, probes, tok in groups:
        print(f"\n{title}")
        print("-" * 78)
        results = check(title, expected, base, probes, tok)
        all_results += results
        for ok, method, path, status, ms, cors, snippet in results:
            mark = "OK  " if ok else "FAIL"
            st = status if status is not None else "ERR"
            print(f"  [{mark}] {method:4} {path:45} {str(st):4} {ms:>5}ms {cors:8}")
            if not ok:
                print(f"         └─ {snippet}")

    # Optional: authenticated reads should be 200 when a token is supplied.
    if token:
        print("\nAUTHENTICATED reads with SMOKE_JWT (expect 200)")
        print("-" * 78)
        results = check("authed", {200}, base, [p for p in AUTH_REQUIRED if p[0] == "GET"], token)
        all_results += results
        for ok, method, path, status, ms, cors, snippet in results:
            mark = "OK  " if ok else "FAIL"
            print(f"  [{mark}] {method:4} {path:45} {str(status):4} {ms:>5}ms")
            if not ok:
                print(f"         └─ {snippet}")

    fails = [r for r in all_results if not r[0]]
    print("\n" + "=" * 78)
    print(f"RESULT: {len(all_results) - len(fails)}/{len(all_results)} passed, {len(fails)} failed")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
