"""Persistent AI response cache using the Supabase ai_cache table.

Provides functions for reading, writing, and clearing cached AI responses
with automatic expiration based on creation time.
"""
from datetime import datetime, timedelta, timezone


def get_cached(key: str, sb, max_age_hours: int = 24):
    """Retrieve a cached AI response if it exists and has not expired.

    Args:
        key: The cache key (typically f"{endpoint}:{ticker}:{date}").
        sb: Authenticated Supabase client.
        max_age_hours: Maximum age in hours for a cache entry to be
                       considered valid (default 24).

    Returns:
        The cached response data (typically a dict) if found and fresh,
        or None if the entry is missing or expired.
    """
    try:
        result = (
            sb.table("ai_cache")
            .select("response_data, created_at")
            .eq("cache_key", key)
            .execute()
        )
        if result.data and len(result.data) > 0:
            row = result.data[0]
            created_at = row.get("created_at")
            if created_at:
                if isinstance(created_at, str):
                    created_dt = datetime.fromisoformat(
                        created_at.replace("Z", "+00:00")
                    )
                else:
                    created_dt = created_at
                age = datetime.now(timezone.utc) - created_dt
                if age < timedelta(hours=max_age_hours):
                    return row["response_data"]
                # Entry is stale -- remove it
                sb.table("ai_cache").delete().eq("cache_key", key).execute()
            else:
                return row["response_data"]
    except Exception:
        pass
    return None


def set_cache(key: str, content, sb) -> None:
    """Store an AI response in the cache (upsert).

    If the key already exists its content and creation timestamp are
    replaced.  After writing, expired entries (>= 7 days old) are cleaned
    via the database-level ``clean_ai_cache()`` function.

    Args:
        key: The cache key.
        content: The response data to cache (must be JSON-serializable).
        sb: Authenticated Supabase client.
    """
    try:
        sb.table("ai_cache").upsert(
            {
                "cache_key": key,
                "response_data": content,
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
            on_conflict="cache_key",
        ).execute()
        # Housekeeping: remove entries older than 7 days
        sb.rpc("clean_ai_cache").execute()
    except Exception:
        pass


def clear_cache(sb) -> None:
    """Delete every row from the ai_cache table.

    Args:
        sb: Authenticated Supabase client.
    """
    try:
        sb.table("ai_cache").delete().neq("cache_key", "").execute()
    except Exception:
        pass
