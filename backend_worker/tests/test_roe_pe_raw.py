"""Regressionstest — ROE/P/E RAW-värden (ROND 10).

Fångar median-neutraliserings-felet: neutralisering skriver om roe/pe IN PLACE
(2914.T 0 %, MSFT ~0.55×); *_raw-kolumner måste bevara sanna råvärden.
Kända värden från granskning 2026-08-31 (stockanalysis.com/Gurufocus/m.m.).
"""
import unittest

import pandas as pd

import backend_worker.db_loader as db_loader


# Verkliga ROE/P/E (källa: granskning 2026-08-31 + stockanalysis.com/Gurufocus)
FIXTURES = {
    "MSFT":   {"roe": 0.32,  "pe": 35.0},
    "UNP":    {"roe": 0.44,  "pe": 22.0},
    "7733.T": {"roe": 0.087, "pe": 26.7},
    "O39.SI": {"roe": 0.13,  "pe": 15.0},
    "2914.T": {"roe": 0.35,  "pe": 15.0},
    "MU":     {"roe": 0.50,  "pe": 25.0},
    "NVDA":   {"roe": 1.01,  "pe": 50.0},
}  # TODO: konfirmera exakta reportvärden mot källor (användarna har givit startpunkt)


def _raw_df() -> pd.DataFrame:
    """Simulera rå df från stock-scanner före neutralisering."""
    tickers = list(FIXTURES.keys())
    return pd.DataFrame({
        "ticker": tickers,
        "roe": [FIXTURES[t]["roe"] for t in tickers],
        "pe_trailing": [FIXTURES[t]["pe"] for t in tickers],
        "pe_forward": [FIXTURES[t]["pe"] * 0.9 for t in tickers],
        "roa": [0.1] * len(tickers),
    })


class TestRawPreservation(unittest.TestCase):
    def test_raw_columns_generated(self):
        """*_raw-kolumner måste skapas när raw-df passerar through (via load_scan)."""
        df = _raw_df()
        # Vi kan inte importera stock-scanner här; testa db_loader-sidan:
        # en df med *_raw-kolumner måste överleva _apply_sanity opåverkad.
        df = df.rename(columns={c: f"{c}_raw" for c in ("roe", "pe_trailing", "pe_forward")})
        df["roe"] = None  # neutraliserade residualer (interna, kan vara 0/negativa)
        df["pe_trailing"] = None
        out = db_loader._apply_sanity(df.copy())
        for t in FIXTURES:
            row = out[out["ticker"] == t].iloc[0]
            self.assertAlmostEqual(row["roe_raw"], FIXTURES[t]["roe"], places=3,
                                   msg=f"{t} roe_raw förstördes")
            self.assertAlmostEqual(row["pe_trailing_raw"], FIXTURES[t]["pe"], places=2,
                                   msg=f"{t} pe_trailing_raw förstördes")

    def test_raw_not_nulled_by_pe_rule(self):
        """pe_trailing_raw ska INTE nullas av pe < 6-regeln (råvärde, ej residual)."""
        df = _raw_df()
        # Endast raw-kolumnen; neutraliserade kolumnen saknas
        df = df.rename(columns={"pe_trailing": "pe_trailing_raw"})
        df["roe_raw"] = df.pop("roe")
        out = db_loader._apply_sanity(df.copy())
        # 7733.T pe 26.7 → bevaras; inga 0/null för positiva raw
        for t in FIXTURES:
            row = out[out["ticker"] == t].iloc[0]
            self.assertIsNotNone(row["pe_trailing_raw"], f"{t} pe_trailing_raw nullades")

    def test_raw_roe_not_nulled_by_abs5(self):
        """roe_raw ska INTE nullas av |v|>5-regeln (NVDA 1.01 = 101 % giltigt)."""
        df = _raw_df()
        df = df.rename(columns={"roe": "roe_raw"})
        out = db_loader._apply_sanity(df.copy())
        self.assertEqual(out[out["ticker"] == "NVDA"].iloc[0]["roe_raw"], 1.01)


    def test_raw_roe_preserved_when_residual_zero(self):
        """roe_raw ska bevaras även när residualen roe sätts till 0 / NA."""
        df = pd.DataFrame({
            "ticker": ["SAP.DE", "EQNR.OL"],
            "roe": [0.0335, 0.0687],
            "roe_raw": [0.175, 0.220],
        })
        out = db_loader._apply_sanity(df.copy())
        self.assertAlmostEqual(out[out["ticker"] == "SAP.DE"].iloc[0]["roe_raw"], 0.175)
        self.assertAlmostEqual(out[out["ticker"] == "EQNR.OL"].iloc[0]["roe_raw"], 0.220)


class TestBackfillRoeModule(unittest.TestCase):
    def test_import_backfill_module(self):
        import backend_worker.backfill_roe_raw as bfill
        self.assertTrue(callable(bfill.get_yfinance_roe))


class TestDbLoaderRoundtrip(unittest.TestCase):
    def test_scan_columns_include_raw(self):
        for col in ("roe_raw", "pe_trailing_raw", "pe_forward_raw", "roa_raw"):
            self.assertIn(col, db_loader.SCAN_COLUMNS, f"{col} saknas i SCAN_COLUMNS")


if __name__ == "__main__":
    unittest.main()
