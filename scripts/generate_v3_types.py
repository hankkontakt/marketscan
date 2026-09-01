"""Generate TypeScript types for the V3 decision API from FastAPI's OpenAPI schema.

Run:  python scripts/generate_v3_types.py [--check]
Writes: apps/web/lib/types/decision_v3.ts (GENERATED — do not edit by hand).
--check regenerates to a temp file and fails if the committed file drifted.

The backend/frontend contract for /api/v3/decisions/* is the generated file.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT = REPO_ROOT / "apps" / "web" / "lib" / "types" / "decision_v3.ts"

# Schemas to emit, in order. Only these and their refs are included.
TOP_LEVEL = [
    "DecisionProjectionV3",
    "ScreenerProjectionV3",
    "CurrentSnapshotV3",
    "ChangeEventV3",
    "ChangesProjectionV3",
    "CompareRequestV3",
    "CompareProjectionV3",
    "TransitionEventV3",
]

HEADER = """// GENERATED FILE — do not edit by hand.
// Source of truth: apps/api/schemas/decision_v3.py (OpenAPI).
// Regenerate: python scripts/generate_v3_types.py  (--check in CI/tests).
"""

_TYPE_MAP = {
    "number": "number",
    "integer": "number",
    "string": "string",
    "boolean": "boolean",
    "null": "null",
}


def _ts_type(schema: dict, schemas: dict) -> str:
    if "$ref" in schema:
        name = schema["$ref"].rsplit("/", 1)[-1]
        return name
    if "anyOf" in schema:
        parts = [_ts_type(item, schemas) for item in schema["anyOf"]]
        if "null" in parts:
            parts.remove("null")
            return f"{_parenthesize(parts[0] if len(parts) == 1 else ' | '.join(parts))} | null"
        return " | ".join(parts)
    kind = schema.get("type")
    if kind == "array":
        return f"{_ts_type(schema.get('items', {}), schemas)}[]"
    if kind == "object":
        if not schema.get("properties"):
            additional = schema.get("additionalProperties")
            if isinstance(additional, dict) and additional.get("type") in _TYPE_MAP:
                return f"Record<string, {_TYPE_MAP[additional['type']]}>"
            return "Record<string, unknown>"
        return "object"
    return _TYPE_MAP.get(kind, "unknown")


def _parenthesize(ts_type: str) -> str:
    return f"({ts_type})" if " | " in ts_type else ts_type


def _render_schema(name: str, schema: dict, schemas: dict) -> str:
    lines = [f"export interface {name} {{"]
    required = set(schema.get("required", []))
    for prop_name, prop_schema in schema.get("properties", {}).items():
        optional = "" if prop_name in required else "?"
        lines.append(f"  {prop_name}{optional}: {_ts_type(prop_schema, schemas)};")
    lines.append("}")
    return "\n".join(lines)


def _collect_refs(schema: dict, schemas: dict, collected: list[str]) -> None:
    if "$ref" in schema:
        name = schema["$ref"].rsplit("/", 1)[-1]
        if name not in collected:
            collected.append(name)
            _collect_refs(schemas[name], schemas, collected)
        return
    for key in ("anyOf", "allOf", "oneOf"):
        for item in schema.get(key, []):
            _collect_refs(item, schemas, collected)
    for item in schema.get("items") or []:
        _collect_refs(item, schemas, collected)
    for prop in (schema.get("properties") or {}).values():
        _collect_refs(prop, schemas, collected)


def generate() -> str:
    from apps.api.main import app

    schema = app.openapi()
    schemas = schema["components"]["schemas"]
    sections = [HEADER]
    for name in TOP_LEVEL:
        sections.append(_render_schema(name, schemas[name], schemas))
    sections.append(
        "export type V3DecisionTypes = "
        + " | ".join(TOP_LEVEL)
        + ";"
    )
    return "\n\n".join(sections) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="fail if the committed file drifted")
    args = parser.parse_args()
    generated = generate()
    if args.check:
        if not OUTPUT.exists():
            print(f"MISSING {OUTPUT}", file=sys.stderr)
            return 1
        if OUTPUT.read_text(encoding="utf-8") != generated:
            print(f"DRIFT: {OUTPUT} is out of sync with OpenAPI — run python scripts/generate_v3_types.py", file=sys.stderr)
            return 1
        print("OK: generated V3 types match OpenAPI contract")
        return 0
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(generated, encoding="utf-8")
    print(f"Wrote {OUTPUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())