import unittest
from apps.api.core.deepseek_client import _resolve_endpoint


class TestResolveEndpoint(unittest.TestCase):
    def test_openrouter_key(self):
        url, model = _resolve_endpoint("sk-or-v1-abcdef123456")
        self.assertIn("openrouter.ai", url)
        self.assertEqual(model, "deepseek/deepseek-v4-flash")

    def test_deepseek_platform_key(self):
        url, model = _resolve_endpoint("sk-1234567890abcdef0123456789abcdef")
        self.assertIn("api.deepseek.com", url)
        self.assertEqual(model, "deepseek-v4-flash")

    def test_empty_key_falls_back_to_openrouter(self):
        url, _ = _resolve_endpoint("")
        self.assertIn("openrouter.ai", url)


if __name__ == "__main__":
    unittest.main()
