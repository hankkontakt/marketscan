"""
Feature flags management for MarketScan v1 -> v2 migration.
Controls dark launching, shadow models, and gradual user rollout.
"""
import os
from typing import Dict

# Default feature flag values
DEFAULT_FLAGS = {
    "decision_v2_api": False,     # Canonical v2 decision endpoints
    "decision_v3_api": False,     # Immutable manifest projections; no request-time scoring
    "screener_v2": False,        # Frontend v2 decision table
    "stock_decision_v2": False,  # Frontend v2 stock page header & why drawer
    "ai_research_v2": False,     # Evidence-first RAG & non-authoritative AI panel
    "setup_state_shadow": True,  # Compute SetupState in background shadow mode
    "risk_engine_v2": True,      # Compute multi-dimensional RiskState & real liquidity grade
    "security_master_v2": True,  # Enforce hard tradability & corporate action gates
    "master_rank_v2_challenger": True, # Run MasterRank v2 alongside v1
}

def get_feature_flags() -> Dict[str, bool]:
    """
    Get effective feature flags resolved from environment variables or defaults.
    Format in env: MARKETSCAN_FF_<FLAG_NAME_UPPER>=true/false
    """
    flags = dict(DEFAULT_FLAGS)
    for key in flags:
        env_var = f"MARKETSCAN_FF_{key.upper()}"
        if env_var in os.environ:
            val = os.environ[env_var].strip().lower()
            flags[key] = val in ("1", "true", "yes", "on")
    return flags

def is_feature_enabled(flag_name: str) -> bool:
    """Check if a specific feature flag is active."""
    flags = get_feature_flags()
    return flags.get(flag_name, False)
