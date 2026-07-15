"""Regression tests pinning every section-3.7 reconciliation.

One test per decision. If a future contributor "fixes" one of these back to what
the book printed, a test goes red and tells them why.
"""
from __future__ import annotations

import inspect
import json
import random

import pytest

from backtester import backtester as bt
from prediction import prediction_analyzer as pa
from risk.risk_manager import MAX_SECTOR_CONCENTRATION, RiskManager


# --------------------------------------------------------------------------- #
# #6 — Monte Carlo: bootstrap WITH replacement.
# Resolved in the 2nd-edition book (ch06.md:205); this repo already matched.
# The guard stays so neither the repo nor a naive "fix" ever regresses to
# random.sample().
# --------------------------------------------------------------------------- #
class TestMonteCarloBootstrap:
    """Guards the sampler that earlier printings got wrong."""

    def _trades(self, n=200, seed=1):
        rng = random.Random(seed)
        return [{"return": rng.gauss(0.0106, 0.031), "date": f"2025-01-{i % 28 + 1:02d}"}
                for i in range(n)]

    def test_produces_more_than_one_unique_final_value(self):
        mc = bt.monte_carlo_simulation(self._trades(), n_simulations=200)
        unique = {round(v, 6) for v in mc["final_values"]}
        assert len(unique) > 1, (
            "The Monte Carlo collapsed to a single final value. That is the classic "
            "permutation bug: random.sample() is a permutation, the equity update is a "
            "product, and a product is invariant under permutation."
        )

    def test_permutation_sampler_would_collapse(self):
        """Prove the bug is real, so the guard is not cargo cult."""
        returns = [t["return"] for t in self._trades()]
        finals = []
        for _ in range(50):
            capital = 100000.0
            for r in random.sample(returns, len(returns)):  # the naive permutation sampler
                capital += capital * 0.02 * r
            finals.append(round(capital, 4))
        assert len(set(finals)) == 1, (
            "random.sample should collapse to one value; if this ever fails the "
            "premise of deviation #6 needs re-examining."
        )

    def test_percentiles_are_strictly_ordered(self):
        import numpy as np
        mc = bt.monte_carlo_simulation(self._trades(), n_simulations=500)
        p5, p50, p95 = (np.percentile(mc["final_values"], q) for q in (5, 50, 95))
        assert p5 < p50 < p95

    def test_sampler_is_declared_in_the_report(self):
        mc = bt.monte_carlo_simulation(self._trades(), n_simulations=20)
        assert "replacement" in mc["sampler"]

    def test_uses_random_choices_not_random_sample(self):
        src = inspect.getsource(bt.monte_carlo_simulation)
        assert "choices(" in src
        assert "random.sample(" not in src

    def test_book_figures_never_appear_as_our_output(self):
        """The book's illustrative report must not be reprinted as this code's output."""
        forbidden = ["108,400", "127,600", "152,300", "$108,400", "$127,600", "$152,300"]
        import pathlib
        root = pathlib.Path(__file__).resolve().parent.parent
        for path in ("backtester/backtester.py", "docs/04-backtester.md", "README.md"):
            target = root / path
            if not target.exists():
                continue
            text = target.read_text()
            for token in forbidden:
                # They may appear ONLY when explicitly labelled as the book's figures.
                if token in text:
                    for line in text.splitlines():
                        if token in line:
                            assert ("book" in line.lower()
                                    or "printed" in line.lower()
                                    or "illustrative" in line.lower()), (
                                f"{path}: '{token}' appears without being marked as "
                                f"the book's own illustrative figure: {line!r}")


# --------------------------------------------------------------------------- #
# #13 — check_exits() must COVER a short, never double it
# --------------------------------------------------------------------------- #
class TestShortSideExitFix:
    def test_profit_target_on_a_short_submits_a_BUY(self, monkeypatch, tmp_path):
        from flow_trader import flow_trader as ft
        from utils.offline import OfflineTradingClient, OrderSide

        client = OfflineTradingClient(paper=True, positions=[{
            "symbol": "TSLA", "qty": -40, "avg_entry_price": 240.0,
            "current_price": 225.6, "market_value": -9024.0,
            "unrealized_pl": 576.0, "unrealized_plpc": 0.06, "side": "short",
        }])
        monkeypatch.setattr(ft, "alpaca", client)
        monkeypatch.setattr(ft, "_load_exit_state", lambda: {})
        monkeypatch.setattr(ft, "_save_exit_state", lambda s: None)

        ft.check_exits()

        assert client.orders, "no scale-out order was placed"
        order = client.orders[-1]
        assert order.side == OrderSide.BUY.value if hasattr(OrderSide.BUY, "value") \
            else order.side == "buy", (
            "A short at +6% was reduced with a SELL. That ADDS to the short — the "
            "capital-destroying bug earlier printings had (2nd ed fixes it, ch05.md:530)."
        )
        assert order.qty == 20  # half of 40

    def test_profit_target_on_a_long_submits_a_SELL(self, monkeypatch):
        from flow_trader import flow_trader as ft
        from utils.offline import OfflineTradingClient

        client = OfflineTradingClient(paper=True, positions=[{
            "symbol": "AMZN", "qty": 106, "avg_entry_price": 188.0,
            "current_price": 199.28, "market_value": 21123.68,
            "unrealized_pl": 1195.68, "unrealized_plpc": 0.06, "side": "long",
        }])
        monkeypatch.setattr(ft, "alpaca", client)
        monkeypatch.setattr(ft, "_load_exit_state", lambda: {})
        monkeypatch.setattr(ft, "_save_exit_state", lambda s: None)
        ft.check_exits()
        assert client.orders[-1].side == "sell"
        assert client.orders[-1].qty == 53

    def test_breakeven_stop_closes_the_remainder_at_zero_pnl(self, monkeypatch):
        from flow_trader import flow_trader as ft
        from utils.offline import OfflineTradingClient

        client = OfflineTradingClient(paper=True, positions=[{
            "symbol": "AMZN", "qty": 53, "avg_entry_price": 188.0,
            "current_price": 187.9, "market_value": 9958.7,
            "unrealized_pl": -5.3, "unrealized_plpc": -0.0005, "side": "long",
        }])
        state = {"AMZN": {"scaled": True, "breakeven": True}}
        monkeypatch.setattr(ft, "alpaca", client)
        monkeypatch.setattr(ft, "_load_exit_state", lambda: dict(state))
        monkeypatch.setattr(ft, "_save_exit_state", lambda s: None)
        actions = ft.check_exits()
        # -0.05% is nowhere near the -3% stop, but IS below breakeven.
        assert ("AMZN", "BREAKEVEN STOP") in actions

    def test_five_day_time_limit_closes_the_position(self, monkeypatch):
        from flow_trader import flow_trader as ft
        from utils.offline import OfflineTradingClient

        client = OfflineTradingClient(paper=True, positions=[{
            "symbol": "MU", "qty": 90, "avg_entry_price": 118.0,
            "current_price": 118.9, "market_value": 10701.0,
            "unrealized_pl": 81.0, "unrealized_plpc": 0.0076, "side": "long",
        }])
        monkeypatch.setattr(ft, "alpaca", client)
        monkeypatch.setattr(ft, "_load_exit_state", lambda: {})
        monkeypatch.setattr(ft, "_save_exit_state", lambda s: None)
        monkeypatch.setattr(ft, "position_age_days", lambda s: 6)
        actions = ft.check_exits()
        assert ("MU", "TIME_LIMIT") in actions

    def test_unknown_age_does_not_close_the_position(self, monkeypatch):
        from flow_trader import flow_trader as ft
        from utils.offline import OfflineTradingClient

        client = OfflineTradingClient(paper=True, positions=[{
            "symbol": "MU", "qty": 90, "avg_entry_price": 118.0,
            "current_price": 118.9, "market_value": 10701.0,
            "unrealized_pl": 81.0, "unrealized_plpc": 0.0076, "side": "long",
        }])
        monkeypatch.setattr(ft, "alpaca", client)
        monkeypatch.setattr(ft, "_load_exit_state", lambda: {})
        monkeypatch.setattr(ft, "_save_exit_state", lambda s: None)
        monkeypatch.setattr(ft, "position_age_days", lambda s: None)
        assert ft.check_exits() == []


# --------------------------------------------------------------------------- #
# #12 / #11 / #10 — the risk module
# --------------------------------------------------------------------------- #
class TestSectorConcentration:
    def test_proposed_position_is_included_in_the_sector_total(self, clean_account):
        """#12: the printed check sums only EXISTING holdings."""
        rm = RiskManager(client=clean_account)
        result = rm.check_sector_concentration("NVDA", proposed_value=66_600)
        assert result["projected_concentration"] == pytest.approx(0.666, abs=0.001)
        assert not result["allowed"], (
            "A $66,600 position in one tech name on a $100K account is 66.6% "
            "concentration. The printed check approves it because concentration "
            "is 0 at the time of the check."
        )

    def test_empty_portfolio_still_blocks_an_oversized_single_name(self, clean_account):
        rm = RiskManager(client=clean_account)
        rm.initialize_day()
        result = rm.evaluate_trade("NVDA", 925.00)
        # 72 shares would be $66,600 = 66.6%. The cap binds; REDUCE, don't approve.
        assert result["verdict"] == "REDUCED"
        assert result["approved_shares"] < 72

    def test_reduce_path_caps_at_remaining_capacity(self, clean_account):
        """#11: Rule 4 promises REDUCE; the printed code only ever BLOCKS."""
        rm = RiskManager(client=clean_account)
        rm.initialize_day()
        result = rm.evaluate_trade("NVDA", 925.00)
        assert result["verdict"] == "REDUCED"
        # 40% of $100K = $40,000 of capacity; $40,000 / $925 = 43 shares.
        assert result["approved_shares"] == 43
        assert "reduce_reason" in result

    def test_remaining_capacity_is_a_float_not_a_string(self, clean_account):
        rm = RiskManager(client=clean_account)
        result = rm.check_sector_concentration("NVDA", proposed_value=0)
        assert isinstance(result["remaining_capacity"], float)

    def test_a_position_that_fits_is_approved_not_reduced(self, clean_account):
        rm = RiskManager(client=clean_account)
        rm.initialize_day()
        # 166 shares x $240 = $39,840 = 39.8% < the 40% cap. Fits.
        result = rm.evaluate_trade("TSLA", 240.00, stop_loss_pct=0.05)
        assert result["verdict"] == "APPROVED"
        assert result["approved_shares"] == 166


class TestStopLossPlumbing:
    """#10: evaluate_trade() had no stop_loss_pct, so ch09's own TSLA advice
    was unreachable through the gatekeeper the book tells every bot to call."""

    def test_evaluate_trade_accepts_stop_loss_pct(self):
        sig = inspect.signature(RiskManager.evaluate_trade)
        assert "stop_loss_pct" in sig.parameters

    def test_custom_stop_is_reported_not_the_default(self, clean_account):
        rm = RiskManager(client=clean_account)
        rm.initialize_day()
        result = rm.evaluate_trade("TSLA", 240.00, stop_loss_pct=0.05)
        assert result["stop_loss"] == "5%", "checks['stop_loss'] hard-coded the default"
        assert result["stop_loss_pct"] == 0.05

    def test_max_loss_uses_the_custom_stop(self, clean_account):
        rm = RiskManager(client=clean_account)
        rm.initialize_day()
        result = rm.evaluate_trade("TSLA", 240.00, stop_loss_pct=0.05)
        # 166 shares x $240 x 5% = $1,992
        assert result["max_loss"] == "$1,992.00"


# --------------------------------------------------------------------------- #
# #9 — suggested_bet ships as the code prints it
# --------------------------------------------------------------------------- #
class TestSuggestedBet:
    def test_49pct_gap_reproduces_the_printed_2450(self):
        assert pa.suggested_bet(0.49) == pytest.approx(24.50)

    def test_17pct_gap_is_850_not_the_printed_50(self):
        """The book prints $50.00 here. No formula produces both printed examples."""
        assert pa.suggested_bet(0.17) == pytest.approx(8.50)

    def test_min_only_binds_at_a_100pct_gap(self):
        """MAX_BET_SIZE is a scaling coefficient, not a cap. That IS the erratum."""
        assert pa.suggested_bet(0.99) < pa.MAX_BET_SIZE
        assert pa.suggested_bet(1.0) == pa.MAX_BET_SIZE

    def test_a_qualifying_10pct_gap_sizes_five_dollars(self):
        assert pa.suggested_bet(pa.MIN_PROBABILITY_GAP) == pytest.approx(5.00)


# --------------------------------------------------------------------------- #
# #7 — profit factor: formatted, and never one name for two formulas
# --------------------------------------------------------------------------- #
class TestProfitFactor:
    def test_backtester_formats_profit_factor_to_two_decimals(self):
        trades = [{"return": 0.0382, "date": "2025-01-01"} for _ in range(20)]
        trades += [{"return": -0.0214, "date": "2025-02-01"} for _ in range(20)]
        mc = bt.monte_carlo_simulation(trades, n_simulations=10)
        report = bt.generate_report(trades, mc, bt.in_out_sample_split(trades))
        pf = report["strategy_stats"]["profit_factor"]
        assert pf == "1.79", f"expected the formatted 1.79, got {pf!r}"
        assert "average win / average loss" in report["strategy_stats"]["profit_factor_definition"]

    def test_tracking_names_the_sum_based_one_distinctly(self):
        from tracking.calculate_metrics import calculate_metrics
        entries = [{
            "date": "2026-04-06", "trades_taken": 2, "trades_blocked_by_risk": 0,
            "wins": 1, "losses": 1, "daily_pnl_dollar": 100.0,
            "daily_pnl_pct": 1.0, "max_drawdown_pct": 0.0,
            "portfolio_value_close": 10100.0,
        }, {
            "date": "2026-04-07", "trades_taken": 2, "trades_blocked_by_risk": 0,
            "wins": 0, "losses": 2, "daily_pnl_dollar": -50.0,
            "daily_pnl_pct": -0.5, "max_drawdown_pct": 0.5,
            "portfolio_value_close": 10050.0,
        }]
        m = calculate_metrics(entries)
        assert "gross_profit_factor" in m
        assert m["gross_profit_factor"] == pytest.approx(2.0)
        assert "profit_factor" not in m, (
            "A bare 'profit_factor' key would let one name carry two formulas."
        )


# --------------------------------------------------------------------------- #
# #1 — MIN_VOLUME is a live filter, not a dead constant
# --------------------------------------------------------------------------- #
class TestMinVolumeFilter:
    def test_zero_volume_markets_are_dropped(self):
        markets = [
            {"question": "liquid", "volume": "50000.0"},
            {"question": "illiquid", "volume": "0.0"},
            {"question": "thin", "volume": "4200.0"},
        ]
        kept = pa.filter_liquid(markets)
        assert [m["question"] for m in kept] == ["liquid"]

    def test_volume_is_cast_from_a_string(self):
        assert pa.filter_liquid([{"question": "q", "volume": "10000.0"}])


# --------------------------------------------------------------------------- #
# #2 — the min-trades gate is 30, not 100
# --------------------------------------------------------------------------- #
class TestMinTradesGate:
    def test_29_trades_is_insufficient_data(self):
        trades = [{"return": 0.03, "date": f"2025-01-{i % 28 + 1:02d}"} for i in range(29)]
        split = bt.in_out_sample_split(trades)
        assert split["overfit"] is None
        mc = bt.monte_carlo_simulation(trades, n_simulations=20)
        assert bt.generate_report(trades, mc, split)["verdict"] == "INSUFFICIENT DATA"

    def test_30_trades_clears_the_hard_gate(self):
        trades = [{"return": 0.01 if i % 2 else -0.005,
                   "date": f"2025-01-{i % 28 + 1:02d}"} for i in range(30)]
        assert bt.in_out_sample_split(trades)["overfit"] is not None

    def test_100_is_documented_as_the_recommended_floor(self):
        assert bt.RECOMMENDED_MIN_TRADES == 100
        assert bt.MIN_TRADES == 30


# --------------------------------------------------------------------------- #
# #4 — the multi-agent None guard
# --------------------------------------------------------------------------- #
class TestMultiAgentNoneGuard:
    def test_unparseable_monitor_response_aborts_without_attributeerror(self, monkeypatch):
        from multi_agent import multi_agent as ma
        monkeypatch.setattr(ma, "agent_monitor", lambda p: None)
        # The printed orchestrator raises AttributeError here.
        assert ma.run_multi_agent_cycle() is None

    def test_unparseable_analyst_response_places_no_trades(self, monkeypatch):
        from multi_agent import multi_agent as ma
        monkeypatch.setattr(ma, "agent_analyst", lambda p, m=None: None)
        cycle = ma.run_multi_agent_cycle()
        assert cycle["execution"] == []

    def test_unparseable_risk_response_places_no_trades(self, monkeypatch):
        from multi_agent import multi_agent as ma
        monkeypatch.setattr(ma, "agent_risk_manager", lambda r, p: None)
        cycle = ma.run_multi_agent_cycle()
        assert cycle["execution"] == [], (
            "The Risk Manager gets the last word. If it cannot speak, nothing trades."
        )


# --------------------------------------------------------------------------- #
# #14 — ch03's three rules exist, and they are default-ON
# --------------------------------------------------------------------------- #
class TestChapter3Rules:
    def test_liquidity_floor_blocks_a_thin_name(self):
        from utils.signals import adjust_confidence
        adj = adjust_confidence("IRNT", 73, "BULLISH")
        assert adj.tradeable is False
        assert adj.confidence == 0

    def test_geopolitical_filter_costs_15_points(self):
        from utils.signals import adjust_confidence
        adj = adjust_confidence("BABA", 77, "BULLISH", dark_pool_read="BULLISH")
        assert adj.confidence == 62
        assert adj.tradeable is True

    def test_tier_conflict_costs_20_points_and_flags_for_review(self):
        from utils.signals import adjust_confidence
        adj = adjust_confidence("AMD", 71, "BULLISH", dark_pool_read="BEARISH")
        assert adj.confidence == 51
        assert adj.manual_review is True

    def test_unknown_dark_pool_read_costs_nothing(self):
        from utils.signals import adjust_confidence
        adj = adjust_confidence("NVDA", 84, "BULLISH", dark_pool_read="UNKNOWN")
        assert adj.confidence == 84
        adj2 = adjust_confidence("NVDA", 84, "BULLISH", dark_pool_read=None)
        assert adj2.confidence == 84

    def test_all_three_penalties_push_toward_fewer_trades(self):
        from utils.signals import adjust_confidence
        for kwargs in [{"ticker": "BABA", "dark_pool_read": "BULLISH"},
                       {"ticker": "AMD", "dark_pool_read": "BEARISH"}]:
            adj = adjust_confidence(confidence=90, direction="BULLISH", **kwargs)
            assert adj.confidence < 90


# --------------------------------------------------------------------------- #
# #5 — NOT a bug. Both 2%s ship, and they mean different things.
# --------------------------------------------------------------------------- #
class TestTheTwoTwoPercents:
    def test_ch05_notional_and_ch09_risk_both_exist_and_differ_in_meaning(self, clean_account):
        from flow_trader.flow_trader import MAX_POSITION_PCT
        from risk.risk_manager import MAX_RISK_PER_TRADE

        assert MAX_POSITION_PCT == 0.02
        assert MAX_RISK_PER_TRADE == 0.02

        # 2% NOTIONAL on $100K = a $2,000 position.
        assert 100_000 * MAX_POSITION_PCT == 2_000
        # 2% RISK on $100K at a 3% stop = a $66,600 position. Same number, and a
        # thirty-three-fold difference in the quantity it sizes.
        rm = RiskManager(client=clean_account)
        shares = rm.calculate_position_size("NVDA", 925.00)
        assert shares * 925.00 == pytest.approx(66_600, abs=1)


# --------------------------------------------------------------------------- #
# #3 — the newer_than polling param
# --------------------------------------------------------------------------- #
class TestNewerThanParam:
    def test_get_live_flow_accepts_newer_than(self):
        from flow_trader.flow_trader import get_live_flow
        sig = inspect.signature(get_live_flow)
        assert "newer_than_ms" in sig.parameters

    def test_newer_than_filters_older_events(self):
        import time

        from flow_trader.flow_trader import get_live_flow
        assert get_live_flow() != []
        future_ms = int((time.time() + 86_400) * 1000)
        assert get_live_flow(newer_than_ms=future_ms) == []


# --------------------------------------------------------------------------- #
# #8 — the Sharpe formula is transcribed as printed, not silently re-annualized
# --------------------------------------------------------------------------- #
class TestSharpeIsTranscribedNotFixed:
    def test_uses_sqrt_252(self):
        src = inspect.getsource(bt.calculate_sharpe)
        assert "sqrt(252)" in src.replace(" ", "")

    def test_risk_free_default_is_five_percent(self):
        assert inspect.signature(bt.calculate_sharpe).parameters[
            "risk_free_rate"].default == 0.05


# --------------------------------------------------------------------------- #
# #16 — prose-arithmetic errata are REPORT-ONLY. Nothing computes them.
# --------------------------------------------------------------------------- #
class TestNoCoinFlipDemo:
    def test_repo_ships_no_binomial_coin_flip_demo(self):
        """Computing it would print 3.8% next to the book's 21%. Don't."""
        import pathlib
        root = pathlib.Path(__file__).resolve().parent.parent
        for py in root.rglob("*.py"):
            if ".venv" in str(py) or "/tests/" in str(py):
                continue
            src = py.read_text()
            assert "binom" not in src.lower(), f"{py} computes a binomial"
