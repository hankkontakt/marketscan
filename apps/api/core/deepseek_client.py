"""DeepSeek API client for AI features."""
import httpx
from apps.api.core.config import settings


def _extract_content(message: dict) -> str:
    """ÖppnaRouter-proxyvariation: vissa uppströms (t.ex. SiliconFlow) ignorerar
    thinking:disabled och lägger svaret i reasoning-fälten med content=null."""
    content = message.get("content")
    if content:
        return content
    reasoning = message.get("reasoning")
    if reasoning:
        return reasoning
    details = message.get("reasoning_details") or []
    return "\n".join(d.get("text", "") for d in details if isinstance(d, dict))


def _resolve_endpoint(key: str) -> tuple[str, str]:
    """Auto-routing: OpenRouter-nycklar ('sk-or-...') → openrouter.ai (model med
    leverantörsprefix); äkta DeepSeek-nycklar ('sk-...') → api.deepseek.com direkt
    (dag-1-läckan i Vercel-env: 'DEEPSEEK_API_KEY' byttes mot DeepSeek-platform-
    nyckel men URL:en pekade på OpenRouter → 401). Pure och testbar."""
    if key.startswith("sk-or-"):
        return settings.DEEPSEEK_API_URL, settings.DEEPSEEK_MODEL
    return "https://api.deepseek.com/v1/chat/completions", "deepseek-v4-flash"


async def call_deepseek(
    system_prompt: str,
    user_message: str,
    max_tokens: int = 500,
    temperature: float = 0.3,
) -> str:
    if not settings.DEEPSEEK_API_KEY:
        return "(AI ej konfigurerad)"

    url, model_name = _resolve_endpoint(settings.DEEPSEEK_API_KEY)
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            url,
            headers={
                "Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": model_name,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "thinking": {"type": "disabled"},
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return _extract_content(data["choices"][0]["message"])


async def call_deepseek_chat(
    system_prompt: str,
    context: str,
    messages: list[dict],
    max_tokens: int = 600,
) -> str:
    """Chat with message history + context prepended."""
    if not settings.DEEPSEEK_API_KEY:
        return "(AI ej konfigurerad)"

    url, model_name = _resolve_endpoint(settings.DEEPSEEK_API_KEY)
    augmented = []
    for i, m in enumerate(messages):
        if i == 0 and m["role"] == "user":
            augmented.append({"role": "user", "content": f"{context}\n\nFRÅGA: {m['content']}"})
        else:
            augmented.append(m)

    async with httpx.AsyncClient(timeout=45) as client:
        resp = await client.post(
            url,
            headers={
                "Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": model_name,
                "max_tokens": max_tokens,
                "temperature": 0.3,
                "thinking": {"type": "disabled"},
                "messages": [
                    {"role": "system", "content": system_prompt},
                    *augmented,
                ],
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return _extract_content(data["choices"][0]["message"])
