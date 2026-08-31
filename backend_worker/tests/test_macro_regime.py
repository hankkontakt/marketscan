"""Tester för Dynamic Macro & Factor Regime Engine."""
import unittest
from backend_worker.macro_regime import (
    classify_macro_regime,
    derive_regime_from_scan,
    REGIME_WEIGHT_TILTS,
    BASE_WEIGHTS,
)


class TestMacroRegime(unittest.TestCase):
    def test_expansion_risk_on(self):
        """Låg VIX + hög bredd + normal kurva -> EXPANSION_RISK_ON."""
        regime, res = classify_macro_regime(
            vix=13.5,
            yield_spread_2y10y=0.75,
            uptrend_breadth_pct=72.0,
            inflation_rate_pct=2.1,
        )
        self.assertEqual(regime, "EXPANSION_RISK_ON")
        self.assertEqual(res["color"], "emerald")
        self.assertGreater(res["weights"]["momentum"], BASE_WEIGHTS["momentum"])
        self.assertGreater(res["weights"]["growth"], BASE_WEIGHTS["growth"])

    def test_stagflation_high_rate(self):
        """Hög inflation + inverterad kurva -> STAGFLATION_HIGH_RATE."""
        regime, res = classify_macro_regime(
            vix=21.0,
            yield_spread_2y10y=-0.45,
            uptrend_breadth_pct=38.0,
            inflation_rate_pct=5.2,
        )
        self.assertEqual(regime, "STAGFLATION_HIGH_RATE")
        self.assertEqual(res["color"], "amber")
        self.assertGreater(res["weights"]["value"], BASE_WEIGHTS["value"])
        self.assertGreater(res["weights"]["payout"], BASE_WEIGHTS["payout"])

    def test_contraction_crisis(self):
        """VIX > 28 + låg bredd -> CONTRACTION_CRISIS."""
        regime, res = classify_macro_regime(
            vix=32.0,
            yield_spread_2y10y=-0.10,
            uptrend_breadth_pct=20.0,
        )
        self.assertEqual(regime, "CONTRACTION_CRISIS")
        self.assertEqual(res["color"], "rose")
        self.assertGreaterEqual(res["weights"]["quality"], 0.30)

    def test_fallback_neutral(self):
        """Ingen indata -> NEUTRAL utan krasch."""
        regime, res = classify_macro_regime()
        self.assertEqual(regime, "NEUTRAL")
        self.assertEqual(res["weights"], BASE_WEIGHTS)

    def test_derive_from_scan(self):
        """Härled regim från scan_results rader."""
        rows = [
            {"trend_signal": "Upptrend", "entry_signal": "STARK", "change_pct": 0.01},
            {"trend_signal": "Upptrend", "entry_signal": "OK", "change_pct": 0.005},
            {"trend_signal": "Upptrend", "entry_signal": "STARK", "change_pct": 0.02},
            {"trend_signal": "Nedtrend", "entry_signal": "EJ_AKTUELL", "change_pct": -0.01},
        ]
        regime, res = derive_regime_from_scan(rows)
        self.assertIn(regime, REGIME_WEIGHT_TILTS)


if __name__ == "__main__":
    unittest.main()
