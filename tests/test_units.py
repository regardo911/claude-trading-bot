"""Unit tests for every core artifact."""
from __future__ import annotations

import json

import pytest

from prediction.prediction_analyzer import (
    calculate_expected_value,
    parse_outcome_prices,
)


class TestParseOutcomePrices:
    """ch07.md:91-109 — Gamma returns BOTH shapes. Handle both."""

    def test_real_array_shape(self):
        assert parse_outcome_prices(["0.515", "0.485"]) == [0.515, 0.485]

    def test_json_encoded_string_shape(self):
        assert parse_outcome_prices('["0.20", "0.80"]') == [0.20, 0.80]

    def test_garbage_defaults_to_a_coin_flip(self):
        assert parse_outcome_prices("not json") == [0.5, 0.5]
        assert parse_outcome_prices(None) == [0.5, 0.5]
        assert parse_outcome_prices([]) == [0.5, 0.5]
        assert parse_outcome_prices(["a", "b"]) == [0.5, 0.5]

    def test_wrong_length_defaults(self):
        assert parse_outcome_prices(["0.1", "0.2", "0.7"]) == [0.5, 0.5]

    def test_always_unpacks_into_two(self):
        yes, no = parse_outcome_prices("whatever")
        assert yes + no == 1.0

    def test_there_is_no_current_price_field(self):
        """appendices.md:205 — reading `current_price` silently returns 0.5 forever."""
        from utils import fixture
        for market in json.loads(fixture("gamma_markets.json").read_text()):
            assert "current_price" not in market


class TestExpectedValue:
    """ch07.md:240-258."""

    def test_underpriced_yes_is_a_buy(self):
        # Claude 50%, market 30c -> EV of YES = 0.20/share
        r = calculate_expected_value(
            {"estimated_probability": 0.50, "market_price": 0.30})
        assert r["side"] == "YES"
        assert r["ev"] == pytest.approx(0.20)
        assert r["gap"] == pytest.approx(0.20)

    def test_overpriced_yes_is_a_no_buy(self):
        # Claude 25%, market 30c -> YES is -0.05; NO is +0.05
        r = calculate_expected_value(
            {"estimated_probability": 0.25, "market_price": 0.30})
        assert r["side"] == "NO"
        assert r["ev"] == pytest.approx(0.05)

    def test_a_fairly_priced_contract_is_skipped(self):
        r = calculate_expected_value(
            {"estimated_probability": 0.30, "market_price": 0.30})
        assert r["side"] == "SKIP"
        assert r["ev"] == 0

    def test_the_scotus_fixture_reproduces_the_analyzers_own_output(self):
        r = calculate_expected_value(
            {"estimated_probability": 0.71, "market_price": 0.22})
        assert r["side"] == "YES"
        assert r["gap"] == pytest.approx(0.49)


class TestScreener:
    def test_filters_leave_only_sweeps_and_floor_prints(self):
        from screener.screener import get_unusual_flow
        flow = get_unusual_flow()
        assert flow
        assert all(f["is_sweep"] or f["is_floor"] for f in flow)
        assert all(f["total_premium"] >= 200_000 for f in flow)
        assert all(f["volume_oi_ratio"] >= 3.0 for f in flow)

    def test_the_non_sweep_non_floor_row_is_dropped(self):
        from screener.screener import get_unusual_flow
        assert "DIS" not in [f["ticker"] for f in get_unusual_flow()]

    def test_markdown_fenced_json_is_parsed(self):
        """ch04.md:159-165 — Claude sometimes wraps its JSON in a code fence."""
        from screener.screener import analyze_signal
        result = analyze_signal({"ticker": "AMD", "strike": 175.0, "type": "call"})
        assert result is not None
        assert result["ticker"] == "AMD"
        assert result["confidence"] == 71

    def test_watchlist_only_contains_names_above_the_confidence_floor(self):
        from screener.screener import CONFIDENCE_THRESHOLD, run_screener
        watchlist = run_screener()
        assert all(r["confidence"] >= CONFIDENCE_THRESHOLD for r in watchlist)
        assert 5 <= len(watchlist) <= 10, "the book promises a 5-10 name watchlist"


class TestFlowTrader:
    def test_max_dte_drops_the_45_day_expiry(self):
        from flow_trader.flow_trader import get_live_flow
        assert "SMCI" not in [e["ticker"] for e in get_live_flow()]

    def test_pre_935_flow_is_ignored(self):
        """ch05.md:550 — pre-9:35 flow references a stale underlying price."""
        from flow_trader.flow_trader import get_live_flow
        assert "F" not in [e["ticker"] for e in get_live_flow()]

    def test_no_quote_returns_zero_zero_rather_than_guessing(self, monkeypatch):
        """ch05.md:248 — skip the trade rather than price it at $0."""
        from flow_trader import flow_trader as ft
        assert ft.calculate_position_size("ILLQ") == (0, 0)

    def test_deduplication_key_is_ticker_strike_timestamp(self):
        from flow_trader.flow_trader import run_flow_trader
        traded = run_flow_trader(single_cycle=True)
        assert len(traded) == len(set(traded)), "the same sweep traded twice"


class TestBacktester:
    def test_the_bundled_fixture_clears_the_30_trade_gate(self):
        from backtester.backtester import (
            calculate_trade_returns,
            load_historical_flow_from_csv,
        )
        trades = calculate_trade_returns(load_historical_flow_from_csv())
        assert len(trades) > 100

    def test_put_sweeps_flip_the_underlying_return(self):
        import backtester.backtester as bt
        from backtester.backtester import calculate_trade_returns

        call = calculate_trade_returns([
            {"date": "2025-03-03", "ticker": "NVDA", "type": "call",
             "total_premium": 500_000, "volume_oi_ratio": 5.0}])
        put = calculate_trade_returns([
            {"date": "2025-03-03", "ticker": "NVDA", "type": "put",
             "total_premium": 500_000, "volume_oi_ratio": 5.0}])
        assert call and put
        assert call[0]["return"] == pytest.approx(-put[0]["return"])

    def test_missing_price_data_is_skipped_not_crashed(self):
        """The survivorship-bias hole: delisted names have no forward return."""
        from datetime import date

        from backtester.backtester import fetch_forward_return
        assert fetch_forward_return("SIVB", date(2025, 3, 3)) is None

    def test_a_losing_strategy_gets_no_edge(self):
        import backtester.backtester as bt
        trades = [{"return": -0.01 if i % 3 else 0.005,
                   "date": f"2025-0{i % 6 + 1}-01"} for i in range(60)]
        mc = bt.monte_carlo_simulation(trades, n_simulations=200)
        report = bt.generate_report(trades, mc, bt.in_out_sample_split(trades))
        assert report["verdict"] in ("NO EDGE", "OVERFIT")

    def test_zero_trades_fails_closed(self, monkeypatch):
        import backtester.backtester as bt
        monkeypatch.setattr(bt, "calculate_trade_returns", lambda r: [])
        assert bt.run_backtest() is None


class TestMultiAgent:
    def test_a_cycle_places_bracket_orders(self):
        from multi_agent.multi_agent import run_multi_agent_cycle
        cycle = run_multi_agent_cycle()
        filled = [r for r in cycle["execution"] if r["status"] == "FILLED"]
        assert filled
        assert all(r["order_class"] == "bracket" for r in filled), (
            "The BRACKET-ORDER CHECKPOINT (ch08.md:705): if you see only the "
            "parent, the bracket submission silently downgraded."
        )

    def test_long_bracket_arms_straddle_the_entry(self):
        from multi_agent.multi_agent import run_multi_agent_cycle
        cycle = run_multi_agent_cycle()
        for r in cycle["execution"]:
            if r["status"] != "FILLED" or r["direction"] != "BUY":
                continue
            assert r["bracket_stop_price"] < r["entry_price"]
            assert r["bracket_take_profit_price"] > r["entry_price"]

    def test_short_bracket_arms_are_mirrored(self):
        from multi_agent.multi_agent import agent_executor
        results = agent_executor([{
            "ticker": "META", "direction": "SELL", "action": "APPROVE",
            "approved_shares": 10, "stop_loss_pct": 3.0, "profit_target_pct": 6.0,
        }], {})
        r = results[0]
        assert r["status"] == "FILLED"
        assert r["bracket_stop_price"] > r["entry_price"]
        assert r["bracket_take_profit_price"] < r["entry_price"]

    def test_risk_manager_overrides_the_analyst(self):
        """ch08.md:582-591 — the chapter's headline moment."""
        from multi_agent.multi_agent import run_multi_agent_cycle
        cycle = run_multi_agent_cycle()
        actions = [d["action"] for d in cycle["risk"]["decisions"]]
        assert "REDUCE" in actions
        assert "REJECT" in actions

    def test_rejected_trades_are_never_executed(self):
        from multi_agent.multi_agent import run_multi_agent_cycle
        cycle = run_multi_agent_cycle()
        rejected = {d["ticker"] for d in cycle["risk"]["decisions"]
                    if d["action"] == "REJECT"}
        filled = {r["ticker"] for r in cycle["execution"] if r["status"] == "FILLED"}
        assert not (rejected & filled)

    def test_portfolio_is_fetched_once_per_cycle(self, monkeypatch):
        import multi_agent.multi_agent as ma
        calls = []
        original = ma.get_portfolio_state
        monkeypatch.setattr(ma, "get_portfolio_state",
                            lambda: (calls.append(1), original())[1])
        ma.run_multi_agent_cycle()
        assert len(calls) == 1, (
            "Four agents each calling get_portfolio_state() quadruples the Alpaca "
            "request rate and buys nothing (ch08.md:645)."
        )


class TestRiskManager:
    def test_earnings_blackout_blocks_a_name_reporting_in_two_days(self, clean_account):
        from risk.risk_manager import RiskManager
        rm = RiskManager(client=clean_account)
        rm.initialize_day()
        assert rm.evaluate_trade("MU", 118.00)["verdict"] == "BLOCKED"

    def test_a_name_reporting_in_three_weeks_is_not_blocked(self, clean_account):
        from risk.risk_manager import RiskManager
        rm = RiskManager(client=clean_account)
        assert rm.check_earnings_blackout("NVDA")["allowed"] is True

    def test_no_claude_calls_anywhere_in_the_module(self):
        """ch09.md:99 — 'every check is math or public data'."""
        import pathlib
        root = pathlib.Path(__file__).resolve().parent.parent
        src = (root / "risk/risk_manager.py").read_text()
        assert "get_anthropic" not in src
        assert "messages.create" not in src

    def test_sector_comes_from_yfinance(self, clean_account):
        from risk.risk_manager import RiskManager, get_sector
        assert get_sector("NVDA") == "Technology"
        assert RiskManager(client=clean_account)._get_sector("XOM") == "Energy"

    def test_daily_loss_limit_uses_the_printed_constant(self, clean_account):
        from risk.risk_manager import MAX_DAILY_LOSS, RiskManager
        rm = RiskManager(client=clean_account)
        rm.initialize_day()
        assert MAX_DAILY_LOSS == 0.06
        assert rm.check_daily_loss_limit()["allowed"] is True


class TestTracking:
    def test_empty_daily_metrics_is_handled_gracefully(self):
        """The prompt's own acceptance test (ch10.md:38)."""
        from tracking.calculate_metrics import calculate_metrics, load_metrics
        from tracking.phase1_assessment import assess

        entries = load_metrics("daily_metrics_empty.json")
        assert entries == []
        metrics = calculate_metrics(entries)
        assert metrics["days"] == 0
        result = assess(metrics)
        assert result["verdict"] == "NO DATA"
        assert "not a verdict" in result["message"]

    def test_the_go_fixture_produces_go(self):
        from tracking.calculate_metrics import calculate_metrics, load_metrics
        from tracking.phase1_assessment import assess
        assert assess(calculate_metrics(
            load_metrics("daily_metrics_go.json")))["verdict"] == "GO"

    def test_the_hold_fixture_produces_hold(self):
        from tracking.calculate_metrics import calculate_metrics, load_metrics
        from tracking.phase1_assessment import assess
        assert assess(calculate_metrics(
            load_metrics("daily_metrics_hold.json")))["verdict"] == "HOLD"


class TestTracker:
    def test_records_a_correct_bullish_call(self, tmp_path, monkeypatch):
        import screener.tracker as tracker
        monkeypatch.setattr(tracker, "artifact",
                            lambda rel: tmp_path / "tracking.json")
        entry = tracker.record_outcome("2026-05-12", "NVDA", "BULLISH", 84, 3.2)
        assert entry["correct"] is True

    def test_records_an_incorrect_bearish_call(self, tmp_path, monkeypatch):
        import screener.tracker as tracker
        monkeypatch.setattr(tracker, "artifact",
                            lambda rel: tmp_path / "tracking.json")
        entry = tracker.record_outcome("2026-05-12", "TSLA", "BEARISH", 74, 1.1)
        assert entry["correct"] is False


class TestCalibration:
    def test_buckets_group_by_decile(self, tmp_path, monkeypatch, capsys):
        import prediction.calibration as cal
        monkeypatch.setattr(cal, "artifact",
                            lambda rel: tmp_path / "calibration.json")
        for _ in range(6):
            cal.update_calibration("q", 0.6, True)
        for _ in range(4):
            cal.update_calibration("q", 0.6, False)
        cal.print_calibration()
        out = capsys.readouterr().out
        assert "60% bucket: 10 bets, 60% resolved YES" in out


class TestBacktesterScenarios:
    """The mixed teaching fixtures must each reach their labeled verdict, so a
    reader who runs `make demo-ch06-*` sees the diagnosis the demo promises."""

    import pytest as _pytest

    @_pytest.mark.parametrize("scenario,expected", [
        ("no_edge", "NO EDGE"),
        ("overfit", "OVERFIT"),
        ("edge_candidate", "EDGE CONFIRMED"),
    ])
    def test_scenario_reaches_its_labeled_verdict(self, scenario, expected):
        import backtester.backtester as bt
        data = bt.load_scenario(scenario)
        assert data["expected_verdict"] == expected
        trades = data["trades"]
        assert len(trades) >= bt.MIN_TRADES
        mc = bt.monte_carlo_simulation(trades)
        split = bt.in_out_sample_split(trades)
        report = bt.generate_report(trades, mc, split,
                                    bt.walk_forward_validation(trades))
        assert report["verdict"] == expected, (
            f"scenario {scenario!r} reached {report['verdict']!r}, not {expected!r}")

    def test_scenarios_are_marked_synthetic(self):
        import backtester.backtester as bt
        for scenario in bt.SCENARIOS:
            data = bt.load_scenario(scenario)
            assert data.get("synthetic") is True

    def test_default_demo_is_the_diagnostic_not_a_celebration(self):
        """`make demo` must not end on a lone triumphant verdict."""
        import tools.demo as demo
        assert [s[1][0] for s in demo.DIAGNOSE_STEPS].count("backtester/backtester.py") == 3
        assert any("--scenario" in s[1] and "no_edge" in s[1] for s in demo.DIAGNOSE_STEPS)
