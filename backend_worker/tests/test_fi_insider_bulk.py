"""Tester för fi_insider_bulk.py — audit-fixarna 2026-08-29.

1) _parse_float: PER-CELL decimaldetektering (sv + en-GB + blandade
   separatorer + NBSP) — rubrikbaserad decimal_comma gav 100 000×-fel
   ('7,00926' → 700926) vid FI-språkbyte.
2) Issuer-fallback: universe_registry.name (exakt + prefix) primärt;
   company_profiles.description/industry ENDAST när registret saknar rad.
3) 0-rader-vägen: export 0 + HTML-rader → formatändring (exit 1); båda 0 →
   empty_ok.
4) isin_symbol_cache: worker_state-roundtrip (load/save via fake-conn),
   lokalfilen som read-only-fallback.

Rent uppspelat — ingen DB, inga externa anrop.
"""
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from backend_worker import fi_insider_bulk as fib


class TestParseFloat(unittest.TestCase):
    """Per-cell decimaldetektering — ingen rubrikspråksgissning (fix 1)."""

    def test_svensk_komma_decimal(self):
        self.assertEqual(fib._parse_float("20000,0"), 20000.0)
        self.assertEqual(fib._parse_float("7,00926"), 7.00926)

    def test_en_gb_punkt_decimal(self):
        self.assertEqual(fib._parse_float("20000.0"), 20000.0)

    def test_bada_separatorer_sista_ar_decimal(self):
        # en-GB tusental+decimal → 1234.56
        self.assertEqual(fib._parse_float("1,234.56"), 1234.56)
        # sv tusental+decimal → 1234.56
        self.assertEqual(fib._parse_float("1.234,56"), 1234.56)

    def test_fi_sprakbyte_7_00926_aldrig_700926(self):
        # Kärnregressionen: '7,00926' får ALDRIG bli 700926 (100 000×-fel)
        # när rubriken råkar vara en-GB.
        self.assertEqual(fib._parse_float("7,00926"), 7.00926)
        self.assertNotEqual(fib._parse_float("7,00926"), 700926.0)

    def test_nbsp_och_mellanslag_tas_bort(self):
        self.assertEqual(fib._parse_float("20\u00a0000"), 20000.0)
        self.assertEqual(fib._parse_float("20 000"), 20000.0)
        self.assertEqual(fib._parse_float("7\u00a0009,26"), 7009.26)

    def test_redan_numeriskt(self):
        self.assertEqual(fib._parse_float(20000), 20000.0)
        self.assertEqual(fib._parse_float(7.00926), 7.00926)

    def test_tomt_och_ogiltigt(self):
        self.assertIsNone(fib._parse_float(""))
        self.assertIsNone(fib._parse_float(None))
        self.assertIsNone(fib._parse_float("abc"))

    def test_parse_fi_csv_sprakbyte_header_en_values_sv(self):
        # en-GB-rubrik men sv-formatvärden ('7,00926') — header-baserad
        # decimal_comma gav 700926; per-cell ger 7.00926.
        content = (
            "Publication date;Issuer;ISIN;Volume;Price\r\n"
            "2026-08-25 00:00:00;Acme AB;SE0000000001;7,00926;20000,0\r\n"
        ).encode("utf-16-le")
        rows = fib.parse_fi_csv(content)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["shares"], 7.00926)
        self.assertEqual(rows[0]["price"], 20000.0)


class _ScriptedCursor:
    """Cursor med scriptade svar per SQL-fragment (första match vinner)."""

    def __init__(self, responses):
        self._responses = responses
        self.last_query = ""
        self.last_params = None

    def execute(self, sql, params=None):
        self.last_query = sql
        self.last_params = params
        return self

    def fetchone(self):
        for frag, row in self._responses:
            if frag in self.last_query:
                return row
        return None


class _ScriptedConn:
    def __init__(self, responses):
        self._cursor = _ScriptedCursor(responses)
        self.committed = False

    def cursor(self):
        return self._cursor

    def commit(self):
        self.committed = True


class TestIssuerFallback(unittest.TestCase):
    """Issuer-namn → ticker: universe_registry.name primärt (fix 2)."""

    def test_registry_namn_exakt_traffar(self):
        # Issuer matchar universe_registry.name exakt → ticker från registret.
        conn = _ScriptedConn([
            ("LOWER(name) = LOWER", ("REG.ST",)),
            ("name ILIKE", None),
            ("company_profiles", None),
        ])
        self.assertEqual(fib._map_issuer_to_ticker("Acme AB", conn), "REG.ST")

    def test_registry_namn_prefix_traffar(self):
        # Ingen exakt match men issuer ≥ 4 tecken → prefix-ILIKE mot name.
        conn = _ScriptedConn([
            ("LOWER(name) = LOWER", None),
            ("name ILIKE", ("REG.ST",)),
        ])
        self.assertEqual(fib._map_issuer_to_ticker("Acme", conn), "REG.ST")

    def test_description_traffar_inte_nar_registry_har_rad(self):
        # Registret HAR en matchande rad → description-vägen konsulteras INTE:
        # en leverantör vars description nämner kunden får ALDRIG fel ticker.
        conn = _ScriptedConn([
            ("LOWER(name) = LOWER", ("REG.ST",)),
            # company_profiles skulle ge SUP.ST (leverantören) — frågan ska
            # inte ens ställas när registret träffade.
        ])
        self.assertEqual(fib._map_issuer_to_ticker("Acme AB", conn), "REG.ST")
        self.assertNotIn("company_profiles", conn._cursor.last_query)

    def test_description_sista_fallback_nar_registry_saknar_rad(self):
        # Registret saknar matchande rad → gamla description/industry-vägen
        # (sista fallback) kan fortfarande träffa.
        conn = _ScriptedConn([
            ("LOWER(name) = LOWER", None),
            ("name ILIKE", None),
            ("company_profiles", ("SUP.ST",)),
        ])
        self.assertEqual(fib._map_issuer_to_ticker("Acme AB", conn), "SUP.ST")

    def test_kort_issuer_ingen_prefix_match(self):
        # issuer < 4 tecken → ingen prefix-match (för riskabel), bara exakt.
        conn = _ScriptedConn([
            ("LOWER(name) = LOWER", None),
            ("name ILIKE", ("REG.ST",)),   # ska INTE nås
            ("company_profiles", None),
        ])
        self.assertIsNone(fib._map_issuer_to_ticker("AB", conn))
        self.assertNotIn("ILIKE", conn._cursor.last_query)

    def test_tom_issuer(self):
        self.assertIsNone(fib._map_issuer_to_ticker("", _ScriptedConn([])))
        self.assertIsNone(fib._map_issuer_to_ticker(None, _ScriptedConn([])))


class TestZeroRowsPath(unittest.TestCase):
    """0-rader-vägen skiljer formatbyte från tomt fönster (fix 3)."""

    def _run_main(self, html_rows, ping_alive=True):
        out = io.StringIO()
        with mock.patch.object(fib, "fetch_register",
                               return_value={"trades": [], "path": "csv"}), \
             mock.patch.object(fib, "fetch_html_search", return_value=html_rows), \
             mock.patch.object(fib, "ping_search_page", return_value=ping_alive), \
             mock.patch("sys.argv", ["fi_insider_bulk"]), \
             mock.patch("sys.stdout", out):
            try:
                fib.main()
                code = 0
            except SystemExit as e:
                code = e.code
        return code, json.loads(out.getvalue())

    def test_export_0_men_html_rader_ar_formatandring(self):
        # Exporten gav 0 rader men HTML-sök med samma datum ger rader →
        # formatändring → error + exit 1 (inte tyst empty_ok).
        code, payload = self._run_main(html_rows=[{"isin": "SE0000000001", "name": "X"}])
        self.assertEqual(code, 1)
        self.assertEqual(payload["status"], "error")
        self.assertIn("format-ändring", payload["reason"])
        self.assertEqual(payload["html_rows"], 1)

    def test_export_0_och_ping_0_ar_tomt_fonster(self):
        # Både export och HTML-ping ger 0 → empty_ok=True som idag.
        code, payload = self._run_main(html_rows=[])
        self.assertEqual(code, 0)
        self.assertEqual(payload["status"], "ok")
        self.assertTrue(payload["empty_ok"])
        self.assertEqual(payload["rows"], 0)


class TestIsinCacheDbRoundtrip(unittest.TestCase):
    """isin_symbol_cache i worker_state: load/save via fake-conn (fix 4)."""

    def test_load_fran_worker_state(self):
        # psycopg2 returnerar JSONB som dict → returneras direkt.
        conn = _ScriptedConn([("worker_state", ({"SE0000000005": {"symbol": "CACHE.ST"}},))])
        self.assertEqual(fib._load_isin_symbol_cache(conn),
                         {"SE0000000005": {"symbol": "CACHE.ST"}})

    def test_load_tom_worker_state_faller_till_lokalfil(self):
        # Ingen rad i worker_state → lokalfilen läses read-only (migrering).
        with tempfile.TemporaryDirectory() as tmp:
            cache_path = Path(tmp) / "isin_symbol_cache.json"
            cache_path.write_text(
                json.dumps({"SE0000000005": {"symbol": "CACHE.ST"}}), encoding="utf-8")
            with mock.patch.object(fib, "ISIN_SYMBOL_CACHE_PATH", cache_path):
                conn = _ScriptedConn([("worker_state", None)])
                self.assertEqual(fib._load_isin_symbol_cache(conn),
                                 {"SE0000000005": {"symbol": "CACHE.ST"}})

    def test_load_fallback_lokalfil_vid_db_fel(self):
        # DB-fel → lokalfilen läses read-only (andra lagret).
        conn = _ScriptedConn([("worker_state", None)])
        conn._cursor.execute = mock.Mock(side_effect=RuntimeError("db down"))
        with tempfile.TemporaryDirectory() as tmp:
            cache_path = Path(tmp) / "isin_symbol_cache.json"
            cache_path.write_text(
                json.dumps({"SE0000000005": {"symbol": "CACHE.ST"}}), encoding="utf-8")
            with mock.patch.object(fib, "ISIN_SYMBOL_CACHE_PATH", cache_path):
                self.assertEqual(fib._load_isin_symbol_cache(conn),
                                 {"SE0000000005": {"symbol": "CACHE.ST"}})

    def test_load_utan_conn_lokalfil_read_only(self):
        # conn=None → lokalfilen endast (read-only).
        with tempfile.TemporaryDirectory() as tmp:
            cache_path = Path(tmp) / "isin_symbol_cache.json"
            cache_path.write_text(
                json.dumps({"SE0000000005": {"symbol": "CACHE.ST"}}), encoding="utf-8")
            with mock.patch.object(fib, "ISIN_SYMBOL_CACHE_PATH", cache_path):
                self.assertEqual(fib._load_isin_symbol_cache(),
                                 {"SE0000000005": {"symbol": "CACHE.ST"}})

    def test_save_upsert_till_worker_state(self):
        conn = _ScriptedConn([])
        fib._save_isin_symbol_cache(conn, {"SE0000000005": {"symbol": "CACHE.ST"}})
        self.assertTrue(conn.committed)
        self.assertEqual(conn._cursor.last_params[0], fib.ISIN_SYMBOL_CACHE_KEY)
        self.assertEqual(json.loads(conn._cursor.last_params[1]),
                         {"SE0000000005": {"symbol": "CACHE.ST"}})

    def test_map_isin_anvander_db_cache(self):
        # _map_isin_to_ticker läser cachen från worker_state (via conn).
        conn = _ScriptedConn([
            ("company_profiles", None),
            ("universe_registry", None),
            ("worker_state", ({"SE0000000005": {"symbol": "CACHE.ST"}},)),
        ])
        self.assertEqual(fib._map_isin_to_ticker("SE0000000005", conn), "CACHE.ST")


if __name__ == "__main__":
    unittest.main()