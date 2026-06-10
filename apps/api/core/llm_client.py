"""
llm_client.py — Enhetligt LLM-interface med kostnadsoptimerad routing.

Ordning: Gemini free tier → DeepSeek v4-flash (betald) → fel.
Allt cachas via ai_cache (cache_key = sha256 av prompt+model+task).
Budgettak: max N DeepSeek-anrop/dygn (env LLM_DAILY_PAID_CAP, default 500).

Används av:
  - #7 Svensk dokumentintelligens (RAG-extraktion)
  - #19 Black-Litterman (AI-views)
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from datetime import datetime, date
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

# Miljövariabler
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
LLM_DAILY_PAID_CAP = int(os.environ.get("LLM_DAILY_PAID_CAP", "500"))

# Gemini endpoints (free tier)
GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta"
GEMINI_EMBED_MODEL = "models/embedding-001"
GEMINI_FLASH_MODEL = "models/gemini-1.5-flash-latest"

# DeepSeek endpoint
DEEPSEEK_BASE = "https://api.deepseek.com/v1"

# Cache-nyckel-prefix
CACHE_PREFIX = "llm:"


def _make_cache_key(prompt: str, model: str, task: str) -> str:
    """Skapa cache-nyckel från prompt + model + task."""
    raw = f"{prompt}|{model}|{task}"
    return CACHE_PREFIX + hashlib.sha256(raw.encode()).hexdigest()[:48]


def _check_cache(cache_key: str, conn) -> Optional[dict]:
    """Kolla ai_cache-tabellen för cachat svar."""
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT response FROM ai_cache WHERE cache_key = %s AND created_at > NOW() - INTERVAL '30 days'",
            (cache_key,),
        )
        row = cur.fetchone()
        if row:
            return row[0] if isinstance(row[0], dict) else json.loads(row[0])
    except Exception:
        pass
    return None


def _write_cache(cache_key: str, response: dict, conn):
    """Spara svar i ai_cache."""
    try:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO ai_cache (cache_key, model, prompt, response, created_at)
               VALUES (%s, %s, %s, %s, NOW())
               ON CONFLICT (cache_key) DO NOTHING""",
            (cache_key, "llm_client", "", json.dumps(response)),
        )
        conn.commit()
    except Exception as e:
        logger.debug("Cache write failed: %s", e)


def _check_daily_budget(model: str) -> bool:
    """Kontrollera om daglig budget för betalda modeller är nådd."""
    if model == "gemini":
        return True  # Gemini free tier har ingen budget-begränsning här
    # DeepSeek: kontrollera räknare via fil/enkel state
    budget_file = f"/tmp/llm_budget_{date.today().isoformat()}.count"
    try:
        if os.path.exists(budget_file):
            count = int(open(budget_file).read().strip())
            if count >= LLM_DAILY_PAID_CAP:
                logger.warning("Daglig LLM-budget nådd (%d/%d)", count, LLM_DAILY_PAID_CAP)
                return False
    except (ValueError, OSError):
        pass
    return True


def _increment_budget(model: str):
    """Öka daglig budget-räknare."""
    if model == "deepseek":
        budget_file = f"/tmp/llm_budget_{date.today().isoformat()}.count"
        try:
            count = 0
            if os.path.exists(budget_file):
                count = int(open(budget_file).read().strip())
            with open(budget_file, "w") as f:
                f.write(str(count + 1))
        except OSError:
            pass


def _call_gemini_complete(prompt: str, json_schema: Optional[dict] = None) -> Optional[dict]:
    """Anropa Gemini Flash-Lite (free tier)."""
    if not GEMINI_API_KEY:
        logger.debug("GEMINI_API_KEY not set")
        return None

    url = f"{GEMINI_BASE}/{GEMINI_FLASH_MODEL}:generateContent?key={GEMINI_API_KEY}"

    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 2048,
        },
    }

    if json_schema:
        body["generationConfig"]["response_mime_type"] = "application/json"
        body["generationConfig"]["response_schema"] = json_schema

    try:
        resp = httpx.post(url, json=body, timeout=60)
        if resp.status_code == 429:
            logger.warning("Gemini rate limited (429) — faller tillbaka")
            return None
        if resp.status_code != 200:
            logger.warning("Gemini error %d: %s", resp.status_code, resp.text[:200])
            return None

        data = resp.json()
        candidates = data.get("candidates", [])
        if not candidates:
            return None

        text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
        if json_schema:
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                logger.warning("Gemini JSON parse failed, raw: %s", text[:200])
                return {"raw": text}
        return {"text": text}

    except httpx.TimeoutException:
        logger.warning("Gemini timeout")
        return None
    except Exception as e:
        logger.warning("Gemini call failed: %s", e)
        return None


def _call_deepseek_complete(prompt: str, json_schema: Optional[dict] = None) -> Optional[dict]:
    """Anropa DeepSeek v4-flash (betald)."""
    if not DEEPSEEK_API_KEY:
        logger.debug("DEEPSEEK_API_KEY not set")
        return None

    if not _check_daily_budget("deepseek"):
        return None

    url = f"{DEEPSEEK_BASE}/chat/completions"

    messages = [
        {"role": "system", "content": "Du är en analytisk assistent. Svara kortfattat och precist."},
        {"role": "user", "content": prompt},
    ]

    body = {
        "model": "deepseek-chat",
        "messages": messages,
        "temperature": 0.1,
        "max_tokens": 2048,
    }

    if json_schema:
        body["response_format"] = {"type": "json_object"}

    try:
        resp = httpx.post(
            url,
            json=body,
            headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}"},
            timeout=120,
        )
        if resp.status_code == 429:
            logger.warning("DeepSeek rate limited (429)")
            return None
        if resp.status_code != 200:
            logger.warning("DeepSeek error %d: %s", resp.status_code, resp.text[:200])
            return None

        data = resp.json()
        text = data.get("choices", [{}])[0].get("message", {}).get("content", "")

        _increment_budget("deepseek")

        if json_schema:
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                logger.warning("DeepSeek JSON parse failed")
                return {"raw": text}
        return {"text": text}

    except httpx.TimeoutException:
        logger.warning("DeepSeek timeout")
        return None
    except Exception as e:
        logger.warning("DeepSeek call failed: %s", e)
        return None


async def llm_complete(
    prompt: str,
    *,
    task: str = "default",
    json_schema: Optional[dict] = None,
    prefer: str = "cheap",
    cache: bool = True,
    max_retries: int = 1,
) -> dict:
    """Enhetligt LLM-anrop med routing, cache och retry.

    Args:
        prompt: Prompt att skicka.
        task: Uppgiftsbeskrivning (för cache och logging).
        json_schema: JSON-schema för strukturerad output.
        prefer: "cheap" (Gemini först) eller "quality" (DeepSeek först).
        cache: Använd cache?
        max_retries: Antal retries vid valideringsfel (L3). Default 1.

    Returns:
        Dict med svar ('text' eller JSON-fält).
    """
    # Välj modellordning
    if prefer == "quality":
        providers = [_call_deepseek_complete, _call_gemini_complete]
        model_names = ["deepseek", "gemini"]
    else:
        providers = [_call_gemini_complete, _call_deepseek_complete]
        model_names = ["gemini", "deepseek"]

    model_used = model_names[0]

    # Cache-koll
    if cache:
        try:
            import psycopg2
            database_url = os.environ.get("DATABASE_URL")
            if database_url:
                conn = psycopg2.connect(database_url)
                cache_key = _make_cache_key(prompt, model_used, task)
                cached = _check_cache(cache_key, conn)
                conn.close()
                if cached:
                    logger.info("Cache HIT för task=%s", task)
                    return cached
        except Exception:
            pass

    # Anropa providers i ordning (med retry vid valideringsfel)
    current_prompt = prompt
    for attempt in range(max_retries + 1):
        for i, provider in enumerate(providers):
            result = provider(current_prompt, json_schema)
            if result:
                # L3: Validera JSON-schema om json_schema gavs
                if json_schema and json_schema.get("required"):
                    if isinstance(result, dict) and "error" not in result:
                        missing = [f for f in json_schema["required"]
                                   if f not in result]
                        if missing:
                            logger.warning(
                                "Missing required fields %s in %s response (attempt %d/%d)",
                                missing, model_names[i], attempt + 1, max_retries + 1,
                            )
                            if attempt < max_retries:
                                # Uppdatera prompt för retry och bryt ur provider-loopen
                                # så att nästa försök börjar om med första providern
                                current_prompt = prompt + f"\n\nDu missade fältet/na: {', '.join(missing)} — inkludera dem."
                                break  # Break provider loop to retry with first provider
                            # Acceptera ändå med flagga
                            result["_validation_warning"] = f"missing_fields: {missing}"

                # Spara i cache
                if cache:
                    try:
                        import psycopg2
                        database_url = os.environ.get("DATABASE_URL")
                        if database_url:
                            conn = psycopg2.connect(database_url)
                            cache_key = _make_cache_key(current_prompt, model_names[i], task)
                            _write_cache(cache_key, result, conn)
                            conn.close()
                    except Exception:
                        pass
                return result
        else:
            # Provider-loopen slutfördes utan break (ingen retry behövs)
            # Sista försöket misslyckades, gå vidare
            break

    # Alla providers misslyckades
    logger.error("Alla LLM-providers misslyckades för task=%s", task)
    return {"error": "No LLM provider available", "text": ""}


async def llm_embed(texts: list[str]) -> list[list[float]]:
    """Gemini embedding (free tier). Returnerar vektorer.

    Args:
        texts: Lista med texter att embedda.

    Returns:
        Lista med vektorer (dim 768).
    """
    if not GEMINI_API_KEY:
        logger.error("GEMINI_API_KEY not set for embeddings")
        return [[0.0] * 768] * len(texts)

    url = f"{GEMINI_BASE}/{GEMINI_EMBED_MODEL}:embedContent?key={GEMINI_API_KEY}"

    all_embeddings = []
    batch_size = 50  # Gemini free tier batch-limit

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        body = {
            "model": GEMINI_EMBED_MODEL,
            "content": {
                "parts": [{"text": t} for t in batch],
            },
        }

        try:
            resp = httpx.post(url, json=body, timeout=30)
            if resp.status_code != 200:
                logger.warning("Gemini embedding error %d: %s", resp.status_code, resp.text[:200])
                all_embeddings.extend([[0.0] * 768] * len(batch))
                continue

            data = resp.json()
            embeddings = data.get("embedding", [])
            if isinstance(embeddings, dict):
                # Single embedding response
                values = embeddings.get("values", [0.0] * 768)
                all_embeddings.append(values)
            elif isinstance(embeddings, list):
                for emb in embeddings:
                    values = emb.get("values", [0.0] * 768)
                    all_embeddings.append(values)
            else:
                all_embeddings.extend([[0.0] * 768] * len(batch))

        except Exception as e:
            logger.warning("Gemini embedding call failed: %s", e)
            all_embeddings.extend([[0.0] * 768] * len(batch))

    return all_embeddings
