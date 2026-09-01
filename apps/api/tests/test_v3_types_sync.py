"""Contract parity: the committed generated TS types must match OpenAPI.

Runs scripts/generate_v3_types.py --check, which regenerates the V3 decision
types in memory and compares against apps/web/lib/types/decision_v3.ts. This is
the drift gate between backend schemas and the frontend contract.
"""
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_generated_v3_types_are_in_sync_with_openapi():
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT)
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "generate_v3_types.py"), "--check"],
        capture_output=True,
        text=True,
        env=env,
        timeout=120,
    )
    assert result.returncode == 0, f"generated types drifted:\n{result.stdout}\n{result.stderr}"
    assert "match OpenAPI contract" in result.stdout