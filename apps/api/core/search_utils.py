"""
Search input sanitization helpers.

Prevents PostgREST filter-structure injection by allowing only safe
characters in ilike patterns. Special PostgREST syntax characters
(, . ( ) | &) are stripped before interpolation.
"""
import re

# Allow letters (including Swedish), digits, common ticker chars (.-), space, slash, ampersand
_SAFE_RE = re.compile(r"[^\w\s.\-/&ÅÄÖåäö]", re.UNICODE)
_MAX_SEARCH_LEN = 60


def safe_search(term: str) -> str:
    """Sanitize a user-supplied search term for use in PostgREST ilike filters.

    - Strips characters that could inject extra PostgREST filter tokens
      (commas, parentheses, dots used as path separators, etc.)
    - Trims whitespace and limits length to 60 chars
    - Returns empty string if input is None or blank
    """
    if not term:
        return ""
    # Truncate first (before regex, to avoid scanning very long strings)
    cleaned = term[:_MAX_SEARCH_LEN]
    # Strip unsafe PostgREST metacharacters
    cleaned = _SAFE_RE.sub("", cleaned)
    return cleaned.strip()
