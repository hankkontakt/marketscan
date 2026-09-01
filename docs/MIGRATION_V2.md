# MarketScan v2 Migration & Rollback Guide

## Architecture Summary
MarketScan v2 separates monolithic scores into:
1. **MasterRank v2**: 3–12m economic thesis attractiveness (Quality 25%, Growth 20%, Valuation 20%, Momentum 15%, Revisions 10%, Capital Allocation 5%, Catalysts 5%).
2. **SetupState**: Descriptive price action state machine (CONFIRMED, PULLBACK, NEUTRAL, EXTENDED, DAMAGED, EVENT_RISK, INSUFFICIENT).
3. **RiskState**: Fundamental uncertainty, balance-sheet safety, realized volatility, and hard liquidity grades (A–F).
4. **DataGrade**: Data freshness, provenance, and weighted factor coverage (A–F).
5. **AI Research Panel**: Evidence-first RAG with retrieved citations and server-side canonical facts.

## Feature Flags Control Matrix
Feature flags are managed in `apps/api/core/feature_flags.py` and configurable via environment variables:

| Flag Name | Default | Purpose |
| :--- | :--- | :--- |
| `MARKETSCAN_FF_DECISION_V2_API` | `false` | Serves `/api/v2/decisions/*` canonical endpoints |
| `MARKETSCAN_FF_SCREENER_V2` | `false` | Enables 6-column DecisionTable in Screener UI |
| `MARKETSCAN_FF_STOCK_DECISION_V2`| `false` | Enables DecisionHeader & WhyDrawer on Stock page |
| `MARKETSCAN_FF_AI_RESEARCH_V2` | `false` | Enables Evidence-First RAG AI Research Panel |
| `MARKETSCAN_FF_SETUP_STATE_SHADOW`| `true` | Shadow computation and outcome logging for SetupState |
| `MARKETSCAN_FF_RISK_ENGINE_V2` | `true` | Calculates RiskState and real liquidity grades |
| `MARKETSCAN_FF_SECURITY_MASTER_V2`| `true` | Enforces hard tradability and corporate actions |

## Rollback Procedures
1. **Immediate API Rollback**: Set `MARKETSCAN_FF_DECISION_V2_API=false`. All clients fall back to v1 `/scan` and `/master/rank`.
2. **Immediate UI Rollback**: Set `MARKETSCAN_FF_SCREENER_V2=false` and `MARKETSCAN_FF_STOCK_DECISION_V2=false`. UI reverts to v1 ResultTable and VerdictHeader.
3. **Database Dual-Write / Non-Destructive**: All v1 tables (`scan_results`, `master_rank_snapshots`, etc.) are maintained during migration. V2 tables (`issuers`, `securities`, `listings`, `decision_snapshots`, `factor_snapshots`) are additive.
