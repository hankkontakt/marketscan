#!/usr/bin/env python3
"""
Convert pointless `async def` FastAPI route handlers to plain `def`.

WHY: The codebase uses the synchronous Supabase SDK inside `async def` route
handlers. A sync call inside an async handler BLOCKS the event loop — an
anti-pattern that causes unpredictable latency/timeouts on serverless. FastAPI
runs plain `def` handlers in a worker threadpool, so converting handlers that
contain NO `await` to `def` is strictly safer and behavior-preserving.

SAFETY: Only converts functions that
  (1) are decorated with a route decorator (@router.get/post/put/delete/patch
      or @app...), so they are never awaited by user code, AND
  (2) contain no `await`, `async for`, or `async with` in their body.
Only the `async def` token on the definition line is rewritten; all other
formatting, comments and code are untouched.

Usage:
  python scripts/fix_async_handlers.py            # dry run (report only)
  python scripts/fix_async_handlers.py --apply    # rewrite files in place
"""
from __future__ import annotations

import ast
import glob
import os
import sys

ROUTER_METHODS = {"get", "post", "put", "delete", "patch", "head", "options"}


def _is_route_decorator(dec: ast.expr) -> bool:
    # Matches @router.get(...), @app.post(...), @some_router.put(...), etc.
    target = dec.func if isinstance(dec, ast.Call) else dec
    if isinstance(target, ast.Attribute) and target.attr in ROUTER_METHODS:
        return True
    return False


def _has_await(node: ast.AsyncFunctionDef) -> bool:
    for n in ast.walk(node):
        if isinstance(n, (ast.Await, ast.AsyncFor, ast.AsyncWith)):
            return True
    return False


def process_file(path: str, apply: bool) -> list[str]:
    src = open(path, encoding="utf-8").read()
    try:
        tree = ast.parse(src)
    except SyntaxError as e:
        print(f"  !! parse error in {path}: {e}")
        return []

    lines = src.splitlines(keepends=True)
    changes: list[str] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.AsyncFunctionDef):
            continue
        if _has_await(node):
            continue
        if not any(_is_route_decorator(d) for d in node.decorator_list):
            continue
        # node.lineno is the line of `async def ...` (1-based)
        idx = node.lineno - 1
        line = lines[idx]
        if "async def " in line:
            lines[idx] = line.replace("async def ", "def ", 1)
            changes.append(f"  {path}:{node.lineno}  {node.name}")

    if changes and apply:
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.writelines(lines)

    return changes


def main() -> int:
    apply = "--apply" in sys.argv
    root = os.path.join(os.path.dirname(__file__), "..", "apps", "api", "routers")
    root = os.path.normpath(root)
    all_changes: list[str] = []
    for path in sorted(glob.glob(os.path.join(root, "*.py"))):
        all_changes += process_file(path, apply)

    print(f"{'APPLIED' if apply else 'DRY RUN'} — {len(all_changes)} handler(s) "
          f"converted async def -> def:\n")
    print("\n".join(all_changes) if all_changes else "  (none)")
    if not apply:
        print("\nRe-run with --apply to write changes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
