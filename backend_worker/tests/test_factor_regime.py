"""Tester för factor_regime.py — komposit, R12, OOS-percentil, klassificering.

Ren unittest, inga DB- eller nätverksberoenden: testar bara de rena
beräkningsfunktionerna (compute_nordic_composite, rolling_12m,
oos_percentile, classify_regime).
"""
import unittest

import numpy as np
import pandas as pd

from backend_worker.factor_regime import (classify_regime, compute_nordic_composite,
                                          oos_percentile, rolling_12m)


class TestComposite(unittest.TestCase):
    def test_two_valid_is_nan(self):
        # 2 giltiga länder → NaN (kräv ≥3)
        df = pd.DataFrame({
            "SWE": [0.01, np.nan, 0.02],
            "DNK": [0.02, 0.01, np.nan],
            "FIN": [np.nan, np.nan, np.nan],
            "NOR": [np.nan, np.nan, 0.03],
        })
        comp = compute_nordic_composite(df)
        self.assertTrue(np.isnan(comp.iloc[0]))   # SWE+DNK
        self.assertTrue(np.isnan(comp.iloc[1]))   # bara DNK
        self.assertTrue(np.isnan(comp.iloc[2]))   # SWE+NOR

    def test_three_and_four_valid_is_mean(self):
        df = pd.DataFrame({
            "SWE": [0.01, 0.04],
            "DNK": [0.03, 0.02],
            "FIN": [0.05, np.nan],
            "NOR": [np.nan, 0.02],
        })
        comp = compute_nordic_composite(df)
        self.assertAlmostEqual(comp.iloc[0], (0.01 + 0.03 + 0.05) / 3)   # 3 giltiga
        self.assertAlmostEqual(comp.iloc[1], (0.04 + 0.02 + 0.02) / 3)   # 3 giltiga

    def test_four_valid_is_plain_mean(self):
        df = pd.DataFrame({
            "SWE": [0.01], "DNK": [0.02], "FIN": [0.03], "NOR": [0.04],
        })
        comp = compute_nordic_composite(df)
        self.assertAlmostEqual(comp.iloc[0], 0.025)


class TestRolling12M(unittest.TestCase):
    def test_less_than_12_valid_is_nan(self):
        # 11 giltiga totalt → ingen position kan ha 12 giltiga månader
        s = pd.Series([0.01] * 11 + [np.nan, np.nan, np.nan])
        r = rolling_12m(s)
        self.assertTrue(r.isna().all())

    def test_exactly_12_valid(self):
        s = pd.Series([0.01] * 12)
        r = rolling_12m(s)
        self.assertTrue(r.iloc[:11].isna().all())
        self.assertAlmostEqual(r.iloc[11], 1.01 ** 12 - 1)

    def test_gap_skipped_but_still_12_valid(self):
        # t=13: giltiga bakåt = 13,12,10,9,...,1 → 12 st (index 11 är NaN-gap)
        s = pd.Series([0.01] * 11 + [np.nan, 0.01, 0.01])
        r = rolling_12m(s)
        self.assertAlmostEqual(r.iloc[13], 1.01 ** 12 - 1)


class TestOosPercentile(unittest.TestCase):
    def test_small_series(self):
        s = pd.Series([0.3, 0.1, 0.2])
        p = oos_percentile(s)
        self.assertAlmostEqual(p.iloc[0], 1.0)          # 1/1
        self.assertAlmostEqual(p.iloc[1], 0.5)          # 1/2
        self.assertAlmostEqual(p.iloc[2], 2 / 3)        # 2/3

    def test_ties_count_as_le(self):
        s = pd.Series([0.1, 0.1, 0.1])
        p = oos_percentile(s)
        self.assertTrue((p == 1.0).all())               # ties räknas ≤

    def test_nan_skipped(self):
        s = pd.Series([0.3, np.nan, 0.1])
        p = oos_percentile(s)
        self.assertTrue(np.isnan(p.iloc[1]))
        self.assertAlmostEqual(p.iloc[2], 0.5)          # hist=[0.3,0.1] → 1/2


class TestClassify(unittest.TestCase):
    def test_insufficient_history(self):
        regime, reason = classify_regime(0.99, 239)
        self.assertEqual(regime, "otillracklig")
        self.assertIn("n=239", reason)

    def test_boundaries(self):
        self.assertEqual(classify_regime(0.80, 300)[0], "stark")    # ≥ 0.80
        self.assertEqual(classify_regime(0.79, 300)[0], "normal")
        self.assertEqual(classify_regime(0.20, 300)[0], "svag")     # ≤ 0.20
        self.assertEqual(classify_regime(0.21, 300)[0], "normal")

    def test_reason_mentions_percentile(self):
        _, reason = classify_regime(0.87, 475)
        self.assertIn("87%", reason)


if __name__ == "__main__":
    unittest.main()