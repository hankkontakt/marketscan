"""Route-setup-check för alert-routerarna (ren unittest, ingen DB).

Verifierar att båda alert-routerarna är korrekt inkopplade i appen:
  - /api/alerts        → smart_alerts.py (compound larmregler, orörd)
  - /api/price-alerts  → alerts.py (prisriktkurslarm, renamed prefix)

Inga nätverks- eller DB-anrop — bara route-registrering i FastAPI-appen.
"""
import unittest

from fastapi.testclient import TestClient
from apps.api.main import app

test_client = TestClient(app)


class TestAlertRoutes(unittest.TestCase):
    """Route-setup-check: rutter finns med korrekta metoder GET/POST/DELETE."""

    @classmethod
    def setUpClass(cls):
        cls.routes = {}
        for r in app.routes:
            path = getattr(r, "path", None)
            methods = getattr(r, "methods", None)
            if path and methods:
                cls.routes.setdefault(path, set()).update(methods)

    def test_price_alerts_routes_exist(self):
        # alerts.py → prefix /api/price-alerts
        paths = {p for p in self.routes if "/api/price-alerts" in p}
        self.assertIn("/api/price-alerts", paths)
        self.assertIn("/api/price-alerts/{alert_id}", paths)
        self.assertIn("/api/price-alerts/check", paths)
        self.assertIn("GET", self.routes["/api/price-alerts"])
        self.assertIn("POST", self.routes["/api/price-alerts"])
        self.assertIn("DELETE", self.routes["/api/price-alerts/{alert_id}"])

    def test_alerts_routes_still_exist(self):
        # smart_alerts.py → /api/alerts (orörd)
        paths = {p for p in self.routes if "/api/alerts" in p}
        self.assertIn("/api/alerts", paths)
        self.assertIn("GET", self.routes["/api/alerts"])
        self.assertIn("POST", self.routes["/api/alerts"])
        self.assertIn("DELETE", self.routes["/api/alerts/{rule_id}"])

    def test_testclient_sees_both_prefixes(self):
        seen = {r.path for r in test_client.app.routes}
        self.assertIn("/api/alerts", seen)
        self.assertIn("/api/price-alerts", seen)


if __name__ == "__main__":
    unittest.main()