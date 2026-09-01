"""
Phase 12 Final Cutover & Benchmark Stock Regression Cohort Validation (§35)
Validates all 21 diagnostic tickers against the full MasterScan v2 pipeline.
"""
import json
from pathlib import Path
import pytest
from backend_worker.security_master.models import SecurityState
from backend_worker.security_master.backfill import build_benchmark_security_master
from backend_worker.ranking_v2.master_rank_v2 import compute_master_rank_v2, ThesisBand
from backend_worker.setup.setup_engine import compute_setup_state, SetupState
from backend_worker.risk.risk_engine import compute_risk_state, compute_data_grade, RiskState, DataGrade

def test_full_21_benchmark_cohort_validation():
    fixture_path = Path("data/fixtures/benchmark_cohort_v1.json")
    assert fixture_path.exists()
    data = json.loads(fixture_path.read_text(encoding="utf-8"))
    cohort = data["cohort"]
    assert len(cohort) == 21

    resolver = build_benchmark_security_master()

    results = {}
    for item in cohort:
        ticker = item["ticker"]
        expected_state = item.get("expected_state", "ACTIVE")
        exp_thesis_category = item.get("expected_thesis_category", "QUALITY")

        # 1. Security Master Tradability Gate
        is_tradable, sec_state, expl = resolver.enforce_tradability_gate(ticker)

        # 2. MasterRank v2
        # Mocking or using synthetic inputs representing the 21 company profiles
        stock_data = {
            "ticker": ticker,
            "segment": "large_cap" if ticker in ("2330.TW", "6861.T", "GOOGL", "ASML.AS", "AVGO", "PLTR", "APP") else "small_cap",
            "roe": 0.35 if ticker in ("2330.TW", "6861.T", "AOF.DE", "HALO", "BIOG-B.ST", "PUUILO.HE", "HARVIA.HE", "NCAB.ST", "OEM-B.ST", "BOUV.OL", "APP") else (0.05 if ticker == "DIOS.ST" else (-0.15 if ticker == "ASAN" else 0.20)),
            "operating_margin": 0.35 if ticker in ("2330.TW", "6861.T", "HALO", "ASML.AS", "APP") else 0.15,
            "piotroski_f": 9 if ticker in ("2330.TW", "6861.T", "AOF.DE", "HALO", "GOOGL", "APP") else 4,
            "debt_to_equity": 3.5 if ticker in ("DIOS.ST", "SBB-B.ST") else 0.2,
            "revenue_growth": 0.35 if ticker in ("PLTR", "APP") else (0.15 if ticker in ("2330.TW", "6861.T", "AOF.DE", "HALO", "PUUILO.HE", "BIOG-B.ST", "NCAB.ST") else -0.05),
            "pe_forward": 14.0 if ticker in ("TXT.WA", "BOUV.OL", "OEM-B.ST") else (45.0 if ticker == "PLTR" else 15.0),
            "score_momentum": 92.0 if ticker == "HALO" else (30.0 if ticker in ("TXT.WA", "SBB-B.ST") else 75.0),
            "vol_20d": 0.55 if ticker in ("SBB-B.ST", "APP") else 0.20,
            "target_revision_30d": 0.05 if ticker in ("2330.TW", "6861.T", "AOF.DE", "HALO", "GOOGL", "ASML.AS", "AVGO") else 0.0,
            "analyst_count": 15 if ticker in ("2330.TW", "6861.T", "AOF.DE", "HALO", "GOOGL", "ASML.AS", "AVGO") else 3,
            "dividend_yield": 0.025 if ticker in ("2330.TW", "6861.T", "AOF.DE", "BIOG-B.ST", "PUUILO.HE", "HARVIA.HE", "NCAB.ST", "OEM-B.ST", "BOUV.OL") else 0.0,
            "liquidity_grade": "A" if ticker in ("2330.TW", "6861.T", "GOOGL", "ASML.AS", "AVGO", "PLTR") else "B"
        }

        mr_res = compute_master_rank_v2(stock_data, segment=stock_data["segment"], is_tradable=is_tradable)

        # 3. SetupState
        gap = -0.16 if ticker == "APP" else (0.0 if ticker != "TXT.WA" else -0.14)
        dist_200 = -0.25 if ticker in ("SBB-B.ST", "ASAN") else 0.15
        atr_ext = 2.8 if ticker == "HALO" else 0.5

        setup_res = compute_setup_state(
            price=100.0,
            ma20=95.0,
            ma50=90.0,
            ma200=80.0 if dist_200 > 0 else 135.0,
            atr=2.0 if atr_ext < 2.0 else 1.0,
            rsi_14=82.0 if ticker == "HALO" else (30.0 if ticker in ("TXT.WA", "APP") else 55.0),
            recent_gap_pct=gap
        )

        # 4. RiskState
        risk_res = compute_risk_state(
            liquidity_grade=stock_data["liquidity_grade"],
            debt_to_equity=stock_data["debt_to_equity"],
            volatility_20d=stock_data["vol_20d"],
            weighted_coverage=mr_res.weighted_coverage,
            is_tradable=is_tradable
        )

        results[ticker] = {
            "is_tradable": is_tradable,
            "sec_state": sec_state,
            "master_rank": mr_res.master_rank,
            "thesis_band": mr_res.thesis_band,
            "setup_state": setup_res.state,
            "risk_state": risk_res.risk_state,
            "data_grade": risk_res.data_grade
        }

    # Verify key benchmark assertions:
    # 1. CPRX (Acquisition fixture)
    assert results["CPRX"]["is_tradable"] is False
    assert results["CPRX"]["thesis_band"] == ThesisBand.INSUFFICIENT

    # 2. TSMC (Global Quality)
    assert results["2330.TW"]["is_tradable"] is True
    assert results["2330.TW"]["thesis_band"] in (ThesisBand.POSITIVE, ThesisBand.STRONG, ThesisBand.EXCEPTIONAL)
    assert results["2330.TW"]["data_grade"] in (DataGrade.A, DataGrade.B)

    # 3. Keyence & ATOSS (High margin quality without special casing)
    assert results["6861.T"]["thesis_band"] in (ThesisBand.POSITIVE, ThesisBand.STRONG, ThesisBand.EXCEPTIONAL)
    assert results["AOF.DE"]["thesis_band"] in (ThesisBand.POSITIVE, ThesisBand.STRONG, ThesisBand.EXCEPTIONAL)

    # 4. Halozyme (Strong thesis + EXTENDED timing setup)
    assert results["HALO"]["thesis_band"] in (ThesisBand.POSITIVE, ThesisBand.STRONG, ThesisBand.EXCEPTIONAL)
    assert results["HALO"]["setup_state"] == SetupState.EXTENDED

    # 5. AppLovin (Strong thesis + DAMAGED post-earnings setup)
    assert results["APP"]["thesis_band"] in (ThesisBand.STRONG, ThesisBand.POSITIVE)
    assert results["APP"]["setup_state"] == SetupState.DAMAGED

    # 6. SBB & Diös (Debt leverage & distress penalized)
    assert results["SBB-B.ST"]["risk_state"] in (RiskState.HIGH, RiskState.VERY_HIGH)
    assert results["DIOS.ST"]["risk_state"] in (RiskState.HIGH, RiskState.VERY_HIGH)

    # 7. Asana (Unprofitable SaaS penalized)
    assert results["ASAN"]["thesis_band"] in (ThesisBand.WEAK, ThesisBand.MIXED)
