"""
test_fundamentals_fetcher.py — Enhetstester för fundamental- och kassaflödesmotorn.
"""
import unittest
import pandas as pd
from backend_worker import fundamentals_fetcher as ff


class TestFundamentalsFetcher(unittest.TestCase):
    def test_extract_fundamentals_healthy_stock(self):
        """Tester extrahering ur kvartalsdataframes för ett starkt kassaflödesbolag."""
        dates = ["2026-06-30", "2026-03-31", "2025-12-31", "2025-09-30"]
        cf = pd.DataFrame({
            dates[0]: [50.0, 70.0, -20.0],
            dates[1]: [40.0, 60.0, -20.0],
            dates[2]: [45.0, 65.0, -20.0],
            dates[3]: [35.0, 55.0, -20.0],
        }, index=["Free Cash Flow", "Operating Cash Flow", "Capital Expenditure"])

        inc = pd.DataFrame({
            dates[0]: [150.0, 100.0, 40.0, 30.0],
            dates[1]: [140.0, 95.0, 38.0, 28.0],
            dates[2]: [130.0, 85.0, 35.0, 25.0],
            dates[3]: [120.0, 75.0, 30.0, 22.0],
        }, index=["Total Revenue", "Gross Profit", "EBIT", "Net Income"])

        bs = pd.DataFrame({
            dates[0]: [100.0, 150.0, 500.0, 300.0, 10.0],
            dates[1]: [100.0, 140.0, 480.0, 290.0, 10.0],
            dates[2]: [100.0, 130.0, 460.0, 280.0, 10.0],
            dates[3]: [100.0, 120.0, 440.0, 270.0, 10.0],
        }, index=["Total Debt", "Cash And Cash Equivalents", "Total Assets", "Common Stock Equity", "Ordinary Shares Number"])

        res = ff.extract_fundamentals(cf, bs, inc, market_cap=2000.0)
        self.assertEqual(res["fcf_ttm"], 170.0)
        self.assertEqual(res["ocf_ttm"], 250.0)
        self.assertEqual(res["net_income_ttm"], 105.0)
        self.assertEqual(res["revenue_ttm"], 540.0)
        self.assertEqual(res["net_debt"], -50.0)  # 100 total debt - 150 cash = -50 net cash
        self.assertEqual(res["fcf_yield"], 170.0 / 2000.0)
        self.assertAlmostEqual(res["sloan_accrual_ratio"], (105.0 - 250.0) / 500.0)
        self.assertIsNone(res["cash_runway_months"])  # Positivt FCF -> ingen kassarunway-risk
        self.assertEqual(res["dilution_rate_pct"], 0.0)

    def test_extract_fundamentals_empty_frames_handled_gracefully(self):
        """Tomma dataframes orsakar inga krascher."""
        res = ff.extract_fundamentals(None, None, None, market_cap=None)
        self.assertIsNone(res["fcf_ttm"])
        self.assertIsNone(res["sloan_accrual_ratio"])
        self.assertEqual(res["forensic_flags"], [])


if __name__ == "__main__":
    unittest.main()
