"""
Avanza CSV import — parse holdings export, map names to tickers.
No pandas dependency, pure Python + csv module (API-compatible).
"""
import csv
import io
import json
import re
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Load built-in ticker map
_TICKER_MAP_PATH = Path(__file__).resolve().parent.parent / "data" / "avanza_ticker_map.json"


def _load_ticker_map() -> dict[str, str]:
    try:
        with open(_TICKER_MAP_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning("Failed to load ticker map: %s", e)
        return {}


_BUILTIN_MAP: dict[str, str] = _load_ticker_map()


def normalize_name(name: str) -> str:
    return (
        name.lower()
        .strip()
        .replace(",", "")
        .replace(".", "")
        .replace("  ", " ")
    )


def find_ticker(name: str, custom_map: dict[str, str] | None = None) -> str | None:
    """Look up ticker by company name. Checks custom_map, then built-in map."""
    norm = normalize_name(name)
    if custom_map and norm in custom_map:
        return custom_map[norm]
    if norm in _BUILTIN_MAP:
        return _BUILTIN_MAP[norm]
    return None


def parse_swedish_number(s: str) -> float | None:
    """Convert Swedish number format '1 234,56' → 1234.56"""
    if s is None or s.strip() == "":
        return None
    cleaned = str(s).strip().replace("\xa0", "").replace(" ", "").replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


def parse_avanza_csv(content: str | bytes) -> list[dict]:
    """
    Parse Avanza CSV export format.

    Handles:
    - UTF-8 BOM / latin-1 encoding
    - Semicolon or comma separator
    - Swedish number format
    - Multiple column naming variants
    """
    if isinstance(content, bytes):
        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = content.decode("latin-1")
    else:
        text = content

    first_line = text.split("\n")[0]
    sep = ";" if ";" in first_line else ","

    reader = csv.DictReader(io.StringIO(text), delimiter=sep)

    # Normalize column names
    col_map = {}
    for col in reader.fieldnames or []:
        c = col.lower().strip()
        if any(x in c for x in ["värdepapper", "namn", "name", "security"]):
            col_map[col] = "name"
        elif any(x in c for x in ["antal", "quantity", "shares"]):
            col_map[col] = "shares"
        elif any(x in c for x in ["köpkurs", "genomsnittlig", "purchase", "cost"]):
            col_map[col] = "cost_basis"
        elif "kurs" in c and "köp" not in c and "price" in c:
            col_map[col] = "current_price"
        elif any(x in c for x in ["resultat", "result", "change"]):
            col_map[col] = "result"

    rows = []
    for row in reader:
        mapped = {}
        for orig_col, val in row.items():
            new_key = col_map.get(orig_col, orig_col)
            mapped[new_key] = val

        name = (mapped.get("name") or "").strip()
        if not name or name == "":
            continue

        result = {
            "name": name,
            "shares": parse_swedish_number(mapped.get("shares", "")),
            "cost_basis": parse_swedish_number(mapped.get("cost_basis", "")),
            "current_price": parse_swedish_number(mapped.get("current_price", "")),
        }
        rows.append(result)

    return rows


def build_preview(rows: list[dict], custom_map: dict[str, str] | None = None) -> list[dict]:
    """Build preview rows with ticker mapping results."""
    preview = []
    for row in rows:
        ticker = find_ticker(row["name"], custom_map)
        preview.append({
            "name": row["name"],
            "ticker": ticker,
            "shares": row["shares"],
            "cost_basis": row["cost_basis"],
            "current_price": row["current_price"],
            "mapped": ticker is not None,
        })
    return preview
