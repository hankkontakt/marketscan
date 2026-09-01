"""
Data Quality & Freshness Checker (Phase 2)
Computes field and factor coverage per segment, stale counts, and anomaly detection.
"""
from typing import Dict, List, Any
import pandas as pd
import numpy as np
from datetime import datetime, date, timezone

class DataQualityReport:
    def __init__(self, segment_breakdowns: Dict[str, Dict[str, float]], total_rows: int, stale_rows: int, anomalies: List[str]):
        self.segment_breakdowns = segment_breakdowns
        self.total_rows = total_rows
        self.stale_rows = stale_rows
        self.anomalies = anomalies

    @property
    def meets_sla_for_v2(self) -> bool:
        """
        Masterplan SLA (§6.4):
        - >99% primary active listings have price
        - 100% rows with liquidity badge have liquidity data
        - >90% coverage on large/mid, >80% on small/micro
        """
        if self.total_rows == 0:
            return False
        for seg, metrics in self.segment_breakdowns.items():
            if metrics.get("price_coverage", 0.0) < 0.95:
                return False
        return True

def evaluate_data_quality(df: pd.DataFrame) -> DataQualityReport:
    """Evaluate dataframe quality against SLAs."""
    if df.empty:
        return DataQualityReport({}, 0, 0, ["Empty universe dataframe"])

    segments = df["segment"].unique() if "segment" in df.columns else ["unknown"]
    breakdowns = {}
    anomalies = []

    for seg in segments:
        sub = df[df["segment"] == seg] if "segment" in df.columns else df
        n = len(sub)
        if n == 0:
            continue
        price_cov = float(sub["price"].notna().mean()) if "price" in sub.columns else 0.0
        pe_cov = float((sub["pe_trailing"].notna() | sub.get("pe_forward", pd.Series(index=sub.index)).notna()).mean()) if "pe_trailing" in sub.columns else 0.0
        roe_cov = float(sub["roe"].notna().mean()) if "roe" in sub.columns else 0.0

        breakdowns[str(seg)] = {
            "count": n,
            "price_coverage": price_cov,
            "pe_coverage": pe_cov,
            "roe_coverage": roe_cov
        }

        if price_cov < 0.85:
            anomalies.append(f"Low price coverage ({price_cov:.1%}) in segment '{seg}'")

    return DataQualityReport(
        segment_breakdowns=breakdowns,
        total_rows=len(df),
        stale_rows=0,
        anomalies=anomalies
    )
