"""Tester för insider_reconcile.py — karaktär-mappning, volym-aggregering,
key-matchning (both/fi_only/finnhub_only), coverage-first-beteende.

Inga DB-beroenden — testar enbart PURE-funktionerna.
"""
import unittest

from backend_worker.insider_reconcile import (
    classify_fi_karaktar,
    normalize_fi_row,
    normalize_finnhub_row,
    aggregate_shares,
    reconcile_key,
    compare,
    compute_coverage,
    proven_covered_tickers,
    flag_suspicious,
)


class TestClassifyFiKaraktar(unittest.TestCase):
    """FI-karaktärs-mappning → köp/sälj (sv + en MAR-kategorier)."""

    def test_svenska(self):
        self.assertEqual(classify_fi_karaktar("Förvärv"), "buy")
        self.assertEqual(classify_fi_karaktar("Avyttring"), "sell")
        self.assertEqual(classify_fi_karaktar("Teckning"), "buy")
        self.assertEqual(classify_fi_karaktar("Tilldelning"), "buy")
        self.assertEqual(classify_fi_karaktar("Konvertering"), "buy")

    def test_engelska(self):
        self.assertEqual(classify_fi_karaktar("Acquisition"), "buy")
        self.assertEqual(classify_fi_karaktar("Disposal"), "sell")
        self.assertEqual(classify_fi_karaktar("Subscription"), "buy")
        self.assertEqual(classify_fi_karaktar("Allotment"), "buy")
        self.assertEqual(classify_fi_karaktar("Exercise increase"), "buy")
        self.assertEqual(classify_fi_karaktar("Exercise decrease"), "sell")
        self.assertEqual(classify_fi_karaktar("Internal transaction – Acquisition"), "buy")
        self.assertEqual(classify_fi_karaktar("Internal transaction – Disposal"), "sell")

    def test_okand(self):
        self.assertEqual(classify_fi_karaktar("Gift"), "unknown")
        self.assertEqual(classify_fi_karaktar(""), "unknown")
        self.assertEqual(classify_fi_karaktar(None), "unknown")


class TestNormalizeFiRow(unittest.TestCase):
    """FI-rad → nyckelbar rad; History skippas; saknad nyckel → None."""

    def test_valid_sv_format(self):
        # Produktionsrader från fetch_register har float-konverterade volymer
        # (parse_fi_csv konverterar med rätt decimalformat per språk).
        row = {"isin": "SE0005100757", "trade_date": "2026-08-25 00:00:00",
               "shares": 20000.0, "karaktar": "Förvärv", "status": "Aktuell"}
        self.assertEqual(
            normalize_fi_row(row),
            {"isin": "SE0005100757", "trade_date": "2026-08-25",
             "shares": 20000.0, "type_class": "buy"},
        )

    def test_valid_en_format(self):
        row = {"isin": "SE0005100757", "trade_date": "25/08/2026 00:00:00",
               "shares": "20000.0", "karaktar": "Acquisition", "status": "Current"}
        self.assertEqual(
            normalize_fi_row(row),
            {"isin": "SE0005100757", "trade_date": "2026-08-25",
             "shares": 20000.0, "type_class": "buy"},
        )

    def test_history_skipped(self):
        row = {"isin": "SE0005100757", "trade_date": "2026-08-25 00:00:00",
               "shares": "20000,0", "karaktar": "Förvärv", "status": "Historik"}
        self.assertIsNone(normalize_fi_row(row))
        row_en = dict(row, status="History")
        self.assertIsNone(normalize_fi_row(row_en))

    def test_missing_isin(self):
        row = {"isin": "", "trade_date": "2026-08-25 00:00:00",
               "shares": "20000,0", "karaktar": "Förvärv"}
        self.assertIsNone(normalize_fi_row(row))

    def test_unknown_karaktar(self):
        row = {"isin": "SE0005100757", "trade_date": "2026-08-25 00:00:00",
               "shares": "20000,0", "karaktar": "Gift"}
        self.assertIsNone(normalize_fi_row(row))


class TestNormalizeFinnhubRow(unittest.TestCase):
    """Finnhub-rad → nyckelbar rad via ticker→isin-mappning."""

    ISIN_MAP = {"ERIC-B.ST": "SE0000108656"}

    def test_valid(self):
        row = {"ticker": "ERIC-B.ST", "name": "X", "type": "buy",
               "shares": 1000.0, "trade_date": "2026-08-25"}
        self.assertEqual(
            normalize_finnhub_row(row, self.ISIN_MAP),
            {"isin": "SE0000108656", "trade_date": "2026-08-25",
             "shares": 1000.0, "type_class": "buy"},
        )

    def test_unknown_ticker(self):
        row = {"ticker": "UNKNOWN.ST", "type": "buy",
               "shares": 1000.0, "trade_date": "2026-08-25"}
        self.assertIsNone(normalize_finnhub_row(row, self.ISIN_MAP))

    def test_unclassifiable_type(self):
        row = {"ticker": "ERIC-B.ST", "type": None,
               "shares": 1000.0, "trade_date": "2026-08-25"}
        self.assertIsNone(normalize_finnhub_row(row, self.ISIN_MAP))


class TestAggregateShares(unittest.TestCase):
    """Volym-aggregering: delad volym (samma isin/datum/typ) → summa."""

    def test_split_rows_summed(self):
        rows = [
            {"isin": "SE1", "trade_date": "2026-08-25", "shares": 512.0, "type_class": "buy"},
            {"isin": "SE1", "trade_date": "2026-08-25", "shares": 46414.0, "type_class": "buy"},
            {"isin": "SE1", "trade_date": "2026-08-25", "shares": 4841.0, "type_class": "buy"},
        ]
        agg = aggregate_shares(rows)
        self.assertEqual(agg[("SE1", "2026-08-25", "buy")], 51767.0)

    def test_distinct_keys_not_merged(self):
        rows = [
            {"isin": "SE1", "trade_date": "2026-08-25", "shares": 100.0, "type_class": "buy"},
            {"isin": "SE1", "trade_date": "2026-08-25", "shares": 200.0, "type_class": "sell"},
            {"isin": "SE1", "trade_date": "2026-08-26", "shares": 300.0, "type_class": "buy"},
        ]
        agg = aggregate_shares(rows)
        self.assertEqual(len(agg), 3)


class TestReconcileKey(unittest.TestCase):
    def test_normalizes_sign_and_rounding(self):
        self.assertEqual(reconcile_key("SE1", "2026-08-25", -1000.4, "sell"),
                         ("SE1", "2026-08-25", 1000, "sell"))
        self.assertEqual(reconcile_key("SE1", "2026-08-25", 1000.6, "buy"),
                         ("SE1", "2026-08-25", 1001, "buy"))


class TestCompare(unittest.TestCase):
    """Key-matchning: both / fi_only / finnhub_only / mismatches."""

    def test_both_fi_only_finnhub_only(self):
        fi_agg = {
            ("SE1", "2026-08-25", "buy"): 1000.0,
            ("SE1", "2026-08-26", "sell"): 500.0,
        }
        fh_agg = {
            ("SE1", "2026-08-25", "buy"): 1000.0,
            ("SE2", "2026-08-25", "buy"): 200.0,
        }
        cmp = compare(fi_agg, fh_agg)
        self.assertEqual(len(cmp["both"]), 1)
        self.assertEqual(len(cmp["fi_only"]), 1)
        self.assertEqual(len(cmp["finnhub_only"]), 1)
        self.assertEqual(cmp["mismatches"], [])

    def test_exact_match_is_both(self):
        fi_agg = {("SE1", "2026-08-25", "buy"): 1000.0}
        fh_agg = {("SE1", "2026-08-25", "buy"): 1000.0}
        cmp = compare(fi_agg, fh_agg)
        self.assertEqual(len(cmp["both"]), 1)
        self.assertEqual(len(cmp["fi_only"]), 0)
        self.assertEqual(len(cmp["finnhub_only"]), 0)

    def test_mismatch_volume(self):
        fi_agg = {("SE1", "2026-08-25", "buy"): 1000.0}
        fh_agg = {("SE1", "2026-08-25", "buy"): 950.0}
        cmp = compare(fi_agg, fh_agg)
        self.assertEqual(len(cmp["both"]), 0)          # olika nycklar (volym)
        self.assertEqual(len(cmp["fi_only"]), 1)
        self.assertEqual(len(cmp["finnhub_only"]), 1)
        self.assertEqual(len(cmp["mismatches"]), 1)    # men samma grupp
        self.assertEqual(cmp["mismatches"][0]["fi_shares"], 1000.0)
        self.assertEqual(cmp["mismatches"][0]["finnhub_shares"], 950.0)


class TestCoverageFirst(unittest.TestCase):
    """Coverage-first: finnhub_coverage X/N + suspicious ENDAST vid påvisad täckning."""

    def test_coverage_ratio(self):
        fh_rows = [{"ticker": "A.ST"}, {"ticker": "A.ST"}, {"ticker": "B.ST"}]
        covered, total = compute_coverage(fh_rows, ["A.ST", "B.ST", "C.ST"])
        self.assertEqual((covered, total), (2, 3))

    def test_ticker_without_finnhub_rows_not_flagged(self):
        # B.ST har FI-rader men INGA Finnhub-rader → inga finnhub_only/mismatch
        # → ingen suspicious-flagga.
        fi_agg = {("SE2", "2026-08-25", "buy"): 1000.0}   # SE2 = B.ST
        fh_agg = {}                                        # Finnhub har ingenting
        cmp = compare(fi_agg, fh_agg)
        isin_by_ticker = {"B.ST": "SE2"}
        proven = proven_covered_tickers(cmp, isin_by_ticker)
        self.assertEqual(proven, set())
        flags = flag_suspicious(cmp, proven, isin_by_ticker)
        self.assertEqual(flags, [])

    def test_finnhub_only_without_proven_coverage_not_flagged(self):
        # A.ST har BARA finnhub_only-rader (Finnhub-data matchar aldrig FI) →
        # ingen påvisad täckning → ingen suspicious-flagga.
        fi_agg = {("SE1", "2026-08-25", "buy"): 1000.0}
        fh_agg = {("SE1", "2026-08-26", "buy"): 500.0}   # annan dag → finnhub_only
        cmp = compare(fi_agg, fh_agg)
        isin_by_ticker = {"A.ST": "SE1"}
        proven = proven_covered_tickers(cmp, isin_by_ticker)
        self.assertEqual(proven, set())
        flags = flag_suspicious(cmp, proven, isin_by_ticker)
        self.assertEqual(flags, [])

    def test_covered_ticker_finnhub_only_flagged(self):
        # A.ST har en both-rad (täckning påvisad) + en finnhub_only-rad →
        # finnhub_only-raden flaggas som suspicious.
        fi_agg = {("SE1", "2026-08-25", "buy"): 1000.0}
        fh_agg = {
            ("SE1", "2026-08-25", "buy"): 1000.0,   # both → täckning påvisad
            ("SE1", "2026-08-26", "buy"): 500.0,    # finnhub_only
        }
        cmp = compare(fi_agg, fh_agg)
        isin_by_ticker = {"A.ST": "SE1"}
        proven = proven_covered_tickers(cmp, isin_by_ticker)
        self.assertEqual(proven, {"A.ST"})
        flags = flag_suspicious(cmp, proven, isin_by_ticker)
        self.assertEqual(len(flags), 1)
        self.assertEqual(flags[0]["kind"], "finnhub_only")
        self.assertEqual(flags[0]["ticker"], "A.ST")

    def test_mismatch_on_covered_ticker_flagged(self):
        # Volymavvikelse på täckt ticker → mismatch-flagga.
        fi_agg = {("SE1", "2026-08-25", "buy"): 1000.0}
        fh_agg = {("SE1", "2026-08-25", "buy"): 950.0}
        cmp = compare(fi_agg, fh_agg)
        isin_by_ticker = {"A.ST": "SE1"}
        proven = proven_covered_tickers(cmp, isin_by_ticker)
        self.assertEqual(proven, {"A.ST"})
        flags = flag_suspicious(cmp, proven, isin_by_ticker)
        self.assertEqual(len(flags), 1)
        self.assertEqual(flags[0]["kind"], "mismatch")


if __name__ == "__main__":
    unittest.main()