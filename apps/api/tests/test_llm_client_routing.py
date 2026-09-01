"""Routing-paritet + cache-policy för LLM-klienten (ren unittest, inget nätverk).

Verifierar (regression för daily-coach-felet 2026-08-31):
  - llm_client återanvänder deepseek_client._resolve_endpoint (EN routing-källa;
    tidigare hårdkodades OpenRouter → 401 med DeepSeek-plattformsnyckel)
  - nycklar läses från settings vid ANROPSTID (inte import-tid)
  - _normalize_gemini_finish → OpenAI-style 'length'/'stop'
  - max_tokens trådas genom till båda providers
  - daily-coach: misslyckat LLM-svar returnerar tom briefing och CACHAS ALDRIG
    i ai_cache (frontend visar feltillstånd med retry i stället)
"""
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from apps.api.core.config import settings
from apps.api.core import llm_client
from apps.api.core.deepseek_client import _resolve_endpoint


class _FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code
        self.text = ""

    def json(self):
        return self._payload


class TestProviderRouting(unittest.TestCase):
    """EN routing-källa: llm_client ska följa exakt samma kontrakt som
    committee/explain-vägen (deepseek_client)."""

    def test_llm_client_uses_shared_routing(self):
        self.assertIs(llm_client._resolve_endpoint, _resolve_endpoint)

    def test_platform_key_routes_to_deepseek_api(self):
        old = settings.DEEPSEEK_API_KEY
        try:
            settings.DEEPSEEK_API_KEY = "test-platform-dummy-key"
            url, model = _resolve_endpoint(settings.DEEPSEEK_API_KEY)
            self.assertIn("api.deepseek.com", url)
            self.assertEqual(model, "deepseek-v4-flash")
        finally:
            settings.DEEPSEEK_API_KEY = old

    def test_openrouter_key_uses_settings_model(self):
        old = settings.DEEPSEEK_API_KEY
        try:
            settings.DEEPSEEK_API_KEY = "sk-or-v1-mock-test-key"
            url, model = _resolve_endpoint(settings.DEEPSEEK_API_KEY)
            self.assertIn("openrouter.ai", url)
            self.assertEqual(model, settings.DEEPSEEK_MODEL)
        finally:
            settings.DEEPSEEK_API_KEY = old

    def test_empty_deepseek_key_short_circuits_without_network(self):
        old = settings.DEEPSEEK_API_KEY
        try:
            settings.DEEPSEEK_API_KEY = ""
            with patch.object(llm_client.httpx, "post") as mock_post:
                self.assertIsNone(llm_client._call_deepseek_complete("prompt"))
            mock_post.assert_not_called()
        finally:
            settings.DEEPSEEK_API_KEY = old

    def test_deepseek_platform_key_url_and_model(self):
        old = settings.DEEPSEEK_API_KEY
        calls = {}

        def fake_post(url, json=None, timeout=None, headers=None):
            calls["url"] = url
            calls["body"] = json
            return _FakeResponse({"choices": [{"message": {"content": "hej"}, "finish_reason": "stop"}]})

        try:
            settings.DEEPSEEK_API_KEY = "test-platform-dummy-key"
            with patch.dict("os.environ", {"LLM_DAILY_PAID_CAP": "999999"}), \
                 patch.object(llm_client.httpx, "post", side_effect=fake_post):
                res = llm_client._call_deepseek_complete("prompt", max_tokens=1500)
            self.assertEqual(res, {"text": "hej", "finish_reason": "stop"})
            self.assertIn("api.deepseek.com", calls["url"])
            self.assertEqual(calls["body"]["model"], "deepseek-v4-flash")
            self.assertEqual(calls["body"]["max_tokens"], 1500)
        finally:
            settings.DEEPSEEK_API_KEY = old

    def test_gemini_key_from_settings_and_max_tokens_threaded(self):
        old = settings.GEMINI_API_KEY
        calls = {}

        def fake_post(url, json=None, timeout=None):
            calls["url"] = url
            calls["body"] = json
            return _FakeResponse({
                "candidates": [{
                    "content": {"parts": [{"text": "hej"}]},
                    "finishReason": "STOP",
                }],
            })

        try:
            settings.GEMINI_API_KEY = "test-key"
            with patch.object(llm_client.httpx, "post", side_effect=fake_post):
                res = llm_client._call_gemini_complete("prompt", max_tokens=1234)
            self.assertEqual(res, {"text": "hej", "finish_reason": "stop"})
            self.assertIn("key=test-key", calls["url"])
            self.assertEqual(calls["body"]["generationConfig"]["maxOutputTokens"], 1234)
        finally:
            settings.GEMINI_API_KEY = old

    def test_gemini_truncation_flagged_as_length(self):
        old = settings.GEMINI_API_KEY

        def fake_post(url, json=None, timeout=None):
            return _FakeResponse({
                "candidates": [{
                    "content": {"parts": [{"text": "halvt svar"}]},
                    "finishReason": "MAX_TOKENS",
                }],
            })

        try:
            settings.GEMINI_API_KEY = "test-key"
            with patch.object(llm_client.httpx, "post", side_effect=fake_post):
                res = llm_client._call_gemini_complete("prompt")
            self.assertEqual(res["finish_reason"], "length")
        finally:
            settings.GEMINI_API_KEY = old


class TestGeminiFinishNormalization(unittest.TestCase):
    def test_max_tokens_maps_to_length(self):
        self.assertEqual(llm_client._normalize_gemini_finish("MAX_TOKENS"), "length")

    def test_stop_maps_to_stop(self):
        self.assertEqual(llm_client._normalize_gemini_finish("STOP"), "stop")

    def test_none_is_none(self):
        self.assertIsNone(llm_client._normalize_gemini_finish(None))
        self.assertIsNone(llm_client._normalize_gemini_finish(""))

    def test_unknown_lowercased(self):
        self.assertEqual(llm_client._normalize_gemini_finish("SAFETY"), "safety")


class TestCleanCoachText(unittest.TestCase):
    def test_valid_text_passes(self):
        from apps.api.routers.ai import _clean_coach_text
        self.assertEqual(_clean_coach_text(" Bra briefing. "), "Bra briefing.")

    def test_empty_and_provider_errors_rejected(self):
        from apps.api.routers.ai import _clean_coach_text
        self.assertEqual(_clean_coach_text(""), "")
        self.assertEqual(_clean_coach_text(None), "")
        self.assertEqual(_clean_coach_text("(AI ej konfigurerad)"), "")
        self.assertEqual(_clean_coach_text("(AI-tjänsterna är tillfälligt otillgängliga)"), "")


class TestDailyCoachCachePolicy(unittest.IsolatedAsyncioTestCase):
    """Kärnregression: fel svar får ALDRIG fastna i ai_cache en hel dag."""

    def _req(self):
        from apps.api.routers.ai import DailyCoachRequest
        return DailyCoachRequest(holdings=[{"ticker": "MU", "shares": 10, "price": 100}])

    async def test_success_is_cached_and_uses_quality_routing(self):
        from apps.api.routers.ai import daily_coach

        captured = {}

        async def fake_llm_complete(prompt, **kwargs):
            captured.update(kwargs)
            return {"text": "Bra briefing med konkreta tal."}

        sb, user = MagicMock(), SimpleNamespace(id="u1")
        with patch("apps.api.routers.ai.get_cached", return_value=None), \
             patch("apps.api.routers.ai.set_cache") as mock_set, \
             patch("apps.api.core.llm_client.llm_complete", side_effect=fake_llm_complete):
            resp = await daily_coach(self._req(), user=user, sb=sb)

        self.assertEqual(resp["briefing"], "Bra briefing med konkreta tal.")
        self.assertFalse(resp["empty"])
        self.assertEqual(captured.get("prefer"), "quality")
        self.assertEqual(captured.get("max_tokens"), 700)
        mock_set.assert_called_once()

    async def test_llm_error_returns_empty_briefing_and_is_never_cached(self):
        from apps.api.routers.ai import daily_coach

        async def fake_llm_complete(prompt, **kwargs):
            return {"error": "No LLM provider available", "text": ""}

        sb, user = MagicMock(), SimpleNamespace(id="u1")
        with patch("apps.api.routers.ai.get_cached", return_value=None), \
             patch("apps.api.routers.ai.set_cache") as mock_set, \
             patch("apps.api.core.llm_client.llm_complete", side_effect=fake_llm_complete):
            resp = await daily_coach(self._req(), user=user, sb=sb)

        self.assertEqual(resp["briefing"], "")
        self.assertFalse(resp["empty"])
        self.assertIn("storsta_position", resp["facts"])  # fakta grounding oförändrad
        mock_set.assert_not_called()  # fel CACHAS ALDRIG

    async def test_llm_exception_returns_empty_briefing_and_is_never_cached(self):
        from apps.api.routers.ai import daily_coach

        async def fake_llm_complete(prompt, **kwargs):
            raise RuntimeError("network down")

        sb, user = MagicMock(), SimpleNamespace(id="u1")
        with patch("apps.api.routers.ai.get_cached", return_value=None), \
             patch("apps.api.routers.ai.set_cache") as mock_set, \
             patch("apps.api.core.llm_client.llm_complete", side_effect=fake_llm_complete):
            resp = await daily_coach(self._req(), user=user, sb=sb)

        self.assertEqual(resp["briefing"], "")
        mock_set.assert_not_called()


if __name__ == "__main__":
    unittest.main()
