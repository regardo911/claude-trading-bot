"""Shared pytest fixtures. Every test runs offline, seeded, with no API keys."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Belt and braces: the suite must never depend on a key being absent OR present.
for var in ("ANTHROPIC_API_KEY", "UW_API_KEY", "ALPACA_API_KEY",
            "ALPACA_SECRET_KEY", "KALSHI_KEY_ID", "KALSHI_PRIVATE_KEY_PATH"):
    os.environ.pop(var, None)
os.environ["CTB_OFFLINE"] = "1"


@pytest.fixture
def clean_account():
    """A $100K paper account with no open positions — ch09's implicit assumption."""
    from utils.offline import OfflineTradingClient

    return OfflineTradingClient(paper=True, positions=[])


@pytest.fixture
def loaded_account():
    """The fixture portfolio: NVDA -3%, AMZN +6%, a TSLA short +6%, MU flat."""
    from utils.offline import OfflineTradingClient

    return OfflineTradingClient(paper=True)
