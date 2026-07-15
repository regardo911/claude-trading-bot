"""The book's worked examples, as assertions.

If any of these fail, the repo has drifted from the book. That is the point.
"""
from __future__ import annotations

import pytest

from risk.risk_manager import KELLY_FRACTION, RiskManager


def kelly(win_rate: float, profit_factor: float) -> float:
    return win_rate - (1 - win_rate) / profit_factor


class TestKellyScenarios:
    """ch09.md:59-77 — the three worked Kelly scenarios."""

    def test_scenario_1_screener_strategy(self):
        # 53.7% win rate, 1.79 profit factor -> Kelly 27.8%, quarter-Kelly 6.95%
        k = kelly(0.537, 1.79)
        assert k == pytest.approx(0.278, abs=0.001)
        assert k * KELLY_FRACTION == pytest.approx(0.0695, abs=0.0002)

    def test_scenario_2_weaker_strategy(self):
        # 52% win rate, 1.3 profit factor -> Kelly 15.1%, quarter-Kelly 3.8%
        k = kelly(0.52, 1.3)
        assert k == pytest.approx(0.151, abs=0.001)
        assert k * KELLY_FRACTION == pytest.approx(0.038, abs=0.001)

    def test_scenario_3_no_edge_is_negative(self):
        # 48% win rate, 0.9 profit factor -> Kelly -9.8%. Bet ZERO.
        k = kelly(0.48, 0.9)
        assert k == pytest.approx(-0.098, abs=0.001)
        assert k < 0


class TestPositionSizes:
    """ch09.md:413-417 — position sizing on a $100K account."""

    def test_nvda_925_at_3pct_stop_is_72_shares(self, clean_account):
        rm = RiskManager(client=clean_account)
        assert rm.calculate_position_size("NVDA", 925.00) == 72

    def test_ford_12_at_3pct_stop_is_5555_shares(self, clean_account):
        rm = RiskManager(client=clean_account)
        assert rm.calculate_position_size("F", 12.00) == 5555

    def test_tsla_240_at_5pct_stop_is_166_shares(self, clean_account):
        rm = RiskManager(client=clean_account)
        assert rm.calculate_position_size("TSLA", 240.00, stop_loss_pct=0.05) == 166


class TestZeroFloor:
    """ch09.md:185-189 — no hard floor. ZERO is the right answer, not 1 share."""

    def test_negative_kelly_returns_zero_shares_not_one(self, clean_account):
        rm = RiskManager(client=clean_account)
        shares = rm.calculate_position_size(
            "NVDA", 925.00, win_rate=0.48, profit_factor=0.9)
        assert shares == 0

    def test_negative_kelly_verdict_is_rejected_no_edge(self, clean_account):
        rm = RiskManager(client=clean_account)
        rm.initialize_day()
        result = rm.evaluate_trade("NVDA", 925.00, win_rate=0.48, profit_factor=0.9)
        assert result["verdict"] == "REJECTED-NO-EDGE"
        assert result["approved_shares"] == 0
