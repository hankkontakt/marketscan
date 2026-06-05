"""
Vercel serverless entrypoint for MarketScan API.
This file exists at the repo root so Vercel can find it.
It re-exports the FastAPI app from apps/api/main.py.
"""
import sys
import os

# Add repo root to path so 'apps.api.main' is importable
_repo_root = os.path.dirname(os.path.abspath(__file__))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

from apps.api.main import app
