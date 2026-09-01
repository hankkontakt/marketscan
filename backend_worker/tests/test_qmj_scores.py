"""Tester för qmj_scores.py — rena funktioner (ingen nätverk/DB)."""
import io
import json
import math
import os
import sys
import unittest
from contextlib import redirect_stdout
from datetime import date
from unittest.mock import MagicMock, patch

import pandas as pd

import backend_worker.qmj_scores as qmj_scores
from backend_worker.qmj_scores import (
    fy_age_fit, as_of_strict, bucket_mcap, rank_pct, composite,
    short_exclusion, extract_metrics, storage_to_frames, _frames_to_storage,
    stratum_of, latest_valid_period, main,
)


def _mk_frames(interest_expense=None):
    """Syntetiska bokslut (3 år): känt korrekta förväntningsvärden."""
    periods = ["2023-12-31", "2024-12-31", "2025-12-31"]
    if interest_expense is None:
        # yfinance rapporterar Interest Expense NEGATIV (absoluta enheter)
        interest_expense = [-1_200_000.0, -1_200_000.0, -1_200_000.0]
    fin = pd.DataFrame({
        "Net Income":           [8.0, 9.0, 10.0],
        "Operating Income":     [12.0, 13.0, 14.0],
        "Gross Profit":         [26.0, 28.0, 30.0],
        "Interest Expense":     interest_expense,
    }, index=periods).T
    bal = pd.DataFrame({
        "Total Assets":                                          [180.0, 190.0, 200.0],
        "Total Liabilities Net Minority Interest":               [80.0, 85.0, 90.0],
        "Stockholders Equity":                                   [100.0, 105.0, 110.0],
        "Total Debt":                                            [55.0, 58.0, 60.0],
        "Cash And Cash Equivalents":                             [18.0, 19.0, 20.0],
        "Ordinary Shares Number":                                [10e6, 10e6, 10e6],
    }, index=periods).T
    cash = pd.DataFrame({
        "Operating Cash Flow":                                   [11.0, 11.5, 12.0],
        "Capital Expenditure":                                   [-2.5, -3.0, -3.0],
        "Depreciation And Amortization":                         [3.0, 3.5, 4.0],
    }, index=periods).T
    return fin, bal, cash


class TestFyAgeFit(unittest.TestCase):
    def test_three_years_ok(self):
        last, suspect = fy_age_fit(
            [date(2023, 12, 31), date(2024, 12, 31), date(2025, 12, 31)], date.today())
        self.assertEqual(last, date(2025, 12, 31))
        self.assertFalse(suspect)

    def test_too_few_columns(self):
        last, suspect = fy_age_fit([date(2024, 12, 31), date(2025, 12, 31)], date.today())
        self.assertIsNone(last)
        self.assertTrue(suspect)

    def test_quarterly_smuggled_in(self):
        last, suspect = fy_age_fit(
            [date(2024, 12, 31), date(2025, 3, 31), date(2025, 6, 30)], date.today())
        self.assertIsNone(last)
        self.assertTrue(suspect)


class TestAsOfStrict(unittest.TestCase):
    def test_not_usable_before_plus5months(self):
        # FY-slut 2025-12-31 → giltig från 2026-05-31
        self.assertFalse(as_of_strict(date(2025, 12, 31), date(2026, 4, 30)))
        self.assertTrue(as_of_strict(date(2025, 12, 31), date(2026, 6, 1)))


class TestBucketMcap(unittest.TestCase):
    def test_groups(self):
        self.assertEqual(bucket_mcap(100e6), 0)
        self.assertEqual(bucket_mcap(800e6), 1)
        self.assertEqual(bucket_mcap(3e9), 2)
        self.assertEqual(bucket_mcap(10e6), 3)   # under 50 M → utanför "vårat" universum
        self.assertEqual(bucket_mcap(None), 3)
        self.assertEqual(bucket_mcap(-5), 3)


class TestRankPct(unittest.TestCase):
    def test_three_values(self):
        r = rank_pct({"a": 1.0, "b": 2.0, "c": 3.0})
        self.assertLess(r["a"], r["b"])
        self.assertLess(r["b"], r["c"])
        self.assertAlmostEqual(r["b"], 50.0, places=1)

    def test_small_n_neutral(self):
        r = rank_pct({"a": 1.0, "b": 2.0})
        self.assertEqual(r["a"], 50.0)
        self.assertEqual(r["b"], 50.0)


class TestComposite(unittest.TestCase):
    def test_all_neutral(self):
        self.assertEqual(composite(None, None, None, None, None), 50.0)

    def test_quality_dominant_weight(self):
        # q=100 + allt neutralt → 0.40×100 + 0.25×50 + 0.10×50 + 0.10×50 + 0.15×50
        self.assertAlmostEqual(composite(100, None, None, None, None), 70.0, places=1)


class TestShortExclusion(unittest.TestCase):
    def test_high_short(self):
        self.assertIn("short_high", short_exclusion(9.5, False))
        self.assertIsNone(short_exclusion(5.5, False))
        self.assertEqual(short_exclusion(5.5, True), "short_new_disclosure")
        self.assertIsNone(short_exclusion(None, True))   # ingen data → neutral


class TestExtractMetrics(unittest.TestCase):
    def test_known_values(self):
        fin, bal, cash = _mk_frames()
        m = extract_metrics(fin, bal, cash, 100.0, [0.001] * 260)
        self.assertTrue(m["data_quality"] in ("ok", "partial"))
        # roe = 10/110
        self.assertAlmostEqual(m["roe"], 10.0 / 110.0, places=4)
        self.assertAlmostEqual(m["roa"], 14.0 / 200.0, places=4)
        self.assertAlmostEqual(m["gmar"], 30.0 / 200.0, places=4)
        self.assertAlmostEqual(m["cfoa"], 12.0 / 200.0, places=4)
        self.assertAlmostEqual(m["accruals"], (10.0 - 12.0) / 200.0, places=4)
        self.assertAlmostEqual(m["leverage"], 90.0 / 110.0, places=4)
        self.assertAlmostEqual(m["ndebt_ebitda"], 40.0 / 18.0, places=4)
        # intcov = ebit / abs(interest) — yfinance ger NEGATIV Interest Expense
        self.assertAlmostEqual(m["intcov"], 14.0 / 1_200_000.0, places=10)
        self.assertAlmostEqual(m["issuance"], 0.0, places=4)
        # mcap = 100 × 10M = 1e9 (absolut) → grupp 1
        self.assertEqual(bucket_mcap(m["mcap_local"]), 1)
        # fcf = 12 - 3 = 9 (absolut) → yield = 9/1e9
        self.assertIsNotNone(m["fcf_yield"])
        self.assertLess(abs(m["fcf_yield"] - 9e-9), 1e-8)
        self.assertIsNotNone(m["fy_end"])

    def test_empty_frames_partial(self):
        m = extract_metrics(pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), 100.0, [])
        self.assertEqual(m["data_quality"], "partial")

    def test_momentum_needs_252(self):
        fin, bal, cash = _mk_frames()
        m = extract_metrics(fin, bal, cash, 100.0, [0.001] * 100)
        self.assertIsNone(m["momentum_raw"])

    def test_intcov_zero_interest_none(self):
        # interest == 0 → intcov None (faktorn skippas, ingen division med 0)
        fin, bal, cash = _mk_frames(interest_expense=[0.0, 0.0, 0.0])
        m = extract_metrics(fin, bal, cash, 100.0, [0.001] * 260)
        self.assertIsNone(m["intcov"])

    def test_momentum_without_annual_data(self):
        # Ny-listat bolag: <3 års bokslut (fy_last None) men prishistorik finns →
        # momentum/vol ska ändå beräknas (bug: tidig return hoppade över blocket).
        periods = ["2024-12-31", "2025-12-31"]
        fin = pd.DataFrame({
            "Net Income":           [9.0, 10.0],
            "Operating Income":     [13.0, 14.0],
            "Gross Profit":         [28.0, 30.0],
            "Interest Expense":     [-1_200_000.0, -1_200_000.0],
        }, index=periods).T
        bal = pd.DataFrame({
            "Total Assets":                            [190.0, 200.0],
            "Total Liabilities Net Minority Interest": [85.0, 90.0],
            "Stockholders Equity":                     [105.0, 110.0],
            "Total Debt":                              [58.0, 60.0],
            "Cash And Cash Equivalents":               [19.0, 20.0],
            "Ordinary Shares Number":                  [10e6, 10e6],
        }, index=periods).T
        cash = pd.DataFrame({
            "Operating Cash Flow":                     [11.5, 12.0],
            "Capital Expenditure":                     [-3.0, -3.0],
            "Depreciation And Amortization":           [3.5, 4.0],
        }, index=periods).T
        m = extract_metrics(fin, bal, cash, 100.0, [0.001] * 260)
        self.assertIsNone(m["fy_end"])
        self.assertIsNotNone(m["momentum_raw"])
        self.assertIsNotNone(m["momentum_vol_scaled"])

    def test_roundtrip_storage(self):
        fin, bal, cash = _mk_frames()
        frames = {"financials": fin, "balance_sheet": bal, "cashflow": cash}
        import pandas as pd2  # noqa — för kompatibilitet
        hist = pd.DataFrame({"Close": [100.0] * 20})
        stored = _frames_to_storage(frames, hist)
        fin2, bal2, cash2 = storage_to_frames(stored)
        m2 = extract_metrics(fin2, bal2, cash2, 100.0, [0.001] * 260)
        # Samma värden efter round-trip
        self.assertIsNotNone(m2["roe"])


class TestStratumOf(unittest.TestCase):
    def test_established(self):
        self.assertEqual(stratum_of(15, 1000e6, 80e6, 500e6), "established")

    def test_new_small_by_revenue(self):
        self.assertEqual(stratum_of(15, 100e6, 10e6, 50e6), "new_small")

    def test_new_small_by_age(self):
        self.assertEqual(stratum_of(1, 1000e6, 10e6, 100e6), "new_small")

    def test_growth_early(self):
        self.assertEqual(stratum_of(10, 1000e6, -20e6, 300e6), "growth_early")

    def test_turnaround(self):
        self.assertEqual(stratum_of(20, 1000e6, 10e6, -50e6), "turnaround")

    def test_missing_data_falls_to_new(self):
        self.assertEqual(stratum_of(None, None, None, None), "new_small")


class TestLatestValidPeriod(unittest.TestCase):
    def test_latest_valid_period(self):
        # [2024-12-31, 2025-12-31] + today 2026-08-29 → "2025-12-31"
        self.assertEqual(
            latest_valid_period(["2024-12-31", "2025-12-31"], date(2026, 8, 29)),
            "2025-12-31")
        # [2026-03-31] + today 2026-08-29 → None (fy_end+5mån > today)
        self.assertIsNone(latest_valid_period(["2026-03-31"], date(2026, 8, 29)))
        # [2026-03-31, 2025-12-31] → "2025-12-31" (fallback till äldre giltig)
        self.assertEqual(
            latest_valid_period(["2026-03-31", "2025-12-31"], date(2026, 8, 29)),
            "2025-12-31")

    def test_empty_and_garbage(self):
        self.assertIsNone(latest_valid_period([], date(2026, 8, 29)))
        self.assertIsNone(latest_valid_period(["inte-datum"], date(2026, 8, 29)))


class TestExtractMetricsPeriod(unittest.TestCase):
    def test_period_column_used(self):
        fin, bal, cash = _mk_frames()
        m = extract_metrics(fin, bal, cash, 100.0, [0.001] * 260, period="2024-12-31")
        self.assertEqual(m["fy_end"], "2024-12-31")
        # 2024-kolumnen: roe = 9/105, roa = 13/190, gmar = 28/190, cfoa = 11.5/190
        self.assertAlmostEqual(m["roe"], 9.0 / 105.0, places=4)
        self.assertAlmostEqual(m["roa"], 13.0 / 190.0, places=4)
        self.assertAlmostEqual(m["gmar"], 28.0 / 190.0, places=4)
        self.assertAlmostEqual(m["cfoa"], 11.5 / 190.0, places=4)
        # period != senaste FY → data_quality partial
        self.assertEqual(m["data_quality"], "partial")
        self.assertEqual(m["fy_periods"], ["2023-12-31", "2024-12-31", "2025-12-31"])

    def test_period_equals_fy_last_quality_as_today(self):
        fin, bal, cash = _mk_frames()
        m = extract_metrics(fin, bal, cash, 100.0, [0.001] * 260, period="2025-12-31")
        self.assertEqual(m["fy_end"], "2025-12-31")
        self.assertEqual(m["data_quality"], "ok")
        self.assertAlmostEqual(m["roe"], 10.0 / 110.0, places=4)

    def test_invalid_period_falls_back_to_fy_last(self):
        fin, bal, cash = _mk_frames()
        m = extract_metrics(fin, bal, cash, 100.0, [0.001] * 260, period="1999-12-31")
        self.assertEqual(m["fy_end"], "2025-12-31")
        self.assertAlmostEqual(m["roe"], 10.0 / 110.0, places=4)


class _FakeDate(date):
    """datetime.date med fryst today() — deterministiska main-tester."""

    @classmethod
    def today(cls):
        return date(2026, 8, 29)


class TestMainPitFallback(unittest.TestCase):
    """Main-flöde: mocked fetch → fallback till senaste giltiga period ger poäng
    i stället för PIT-block (senaste FY 2026-03-31 ej giltig 2026-08-29)."""

    def _mk_raw(self):
        periods = ["2024-03-31", "2025-03-31", "2026-03-31"]
        fin = pd.DataFrame({
            "Net Income":           [8.0, 9.0, 10.0],
            "Operating Income":     [12.0, 13.0, 14.0],
            "Gross Profit":         [26.0, 28.0, 30.0],
            "Interest Expense":     [-1_200_000.0, -1_200_000.0, -1_200_000.0],
        }, index=periods).T
        bal = pd.DataFrame({
            "Total Assets":                                          [180.0, 190.0, 200.0],
            "Total Liabilities Net Minority Interest":               [80.0, 85.0, 90.0],
            "Stockholders Equity":                                   [100.0, 105.0, 110.0],
            "Total Debt":                                            [55.0, 58.0, 60.0],
            "Cash And Cash Equivalents":                             [18.0, 19.0, 20.0],
            "Ordinary Shares Number":                                [10e6, 10e6, 10e6],
        }, index=periods).T
        cash = pd.DataFrame({
            "Operating Cash Flow":                                   [11.0, 11.5, 12.0],
            "Capital Expenditure":                                   [-2.5, -3.0, -3.0],
            "Depreciation And Amortization":                         [3.0, 3.5, 4.0],
        }, index=periods).T
        frames = {"financials": fin, "balance_sheet": bal, "cashflow": cash}
        hist = pd.DataFrame({"Close": [100.0] * 260})
        stored = _frames_to_storage(frames, hist)
        stored["ticker"] = "TEST.ST"
        stored["fetched_at"] = "2026-08-29"
        return stored

    @patch.object(qmj_scores, "date", _FakeDate)
    @patch("backend_worker.qmj_scores.time.sleep")
    @patch("psycopg2.connect")
    @patch("backend_worker.qmj_scores.fetch_ticker_data")
    def test_fallback_gives_scores_instead_of_pit_block(self, mock_fetch, mock_connect, _mock_sleep):
        mock_fetch.return_value = self._mk_raw()
        mock_connect.return_value = MagicMock()
        # fetchall-ordning: universum, sektor, insider, short
        mock_connect.return_value.cursor.return_value.fetchall.side_effect = [
            [("TEST.ST",)], [], [], []]
        buf = io.StringIO()
        with patch.dict(os.environ, {"DATABASE_URL": "postgresql://mock"}):
            with patch.object(sys, "argv", ["qmj_scores.py"]):
                with redirect_stdout(buf):
                    main()
        out = json.loads(buf.getvalue())
        self.assertEqual(out["status"], "ok")
        self.assertEqual([r["ticker"] for r in out["top5"]], ["TEST.ST"])
        # as_of_date = vald giltig period (2025-03-31), inte senaste FY (2026-03-31)
        cursor = mock_connect.return_value.cursor.return_value
        insert_calls = [c for c in cursor.execute.call_args_list
                        if "INSERT INTO qmj_scores" in str(c.args[0])]
        self.assertEqual(len(insert_calls), 1)
        params = insert_calls[0].args[1]
        self.assertEqual(params[2], "2025-03-31")   # as_of_date
        self.assertEqual(params[11], 50.0)          # alpha_rank — poäng, inte PIT-block
class TestMewsVarianceAndQuality(unittest.TestCase):
    def test_rank_pct_variance_across_diverse_inputs(self):
        """R15 (Task 7): rank_pct producerar äkta varians och hanterar None/ties utan falska default-artefakter."""
        vals = {"A": 10.0, "B": 25.0, "C": 50.0, "D": 75.0, "E": 100.0, "F": None}
        res = rank_pct(vals)
        self.assertNotIn("F", res)
        self.assertEqual(len(set(res.values())), 5)
        # Bättre värden ger strikt högre percentil
        self.assertGreater(res["E"], res["D"])
        self.assertGreater(res["D"], res["C"])
        self.assertGreater(res["C"], res["B"])
        self.assertGreater(res["B"], res["A"])

    def test_composite_excludes_none_cleanly(self):
        """None-faktorer faller tillbaka på neutral 50 utan att krascha eller skapa NaN."""
        comp = composite(q=80.0, m=None, v=60.0, p=None, i=None)
        self.assertTrue(math.isfinite(comp))
        self.assertGreater(comp, 50.0)


if __name__ == "__main__":
    unittest.main()
