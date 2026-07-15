"""Safety is not a policy here, it is an invariant. These tests enforce it."""
from __future__ import annotations

import ast
import os
import pathlib
import socket

import pytest

from utils.offline import LiveModeError, is_live_mode, offline_enabled, set_live_mode

ROOT = pathlib.Path(__file__).resolve().parent.parent


class TestLiveModeCannotBeFlippedByAFlag:
    def test_default_is_paper(self):
        assert is_live_mode() is False

    def test_env_var_alone_does_not_enable_live_mode(self, monkeypatch):
        for var in ("LIVE", "CTB_LIVE", "LIVE_MODE", "TRADING_MODE",
                    "CTB_LIVE_MODE", "REAL_MONEY", "PAPER"):
            monkeypatch.setenv(var, "1")
        monkeypatch.setenv("ALPACA_BASE_URL", "https://api.alpaca.markets")
        assert is_live_mode() is False, "an env var flipped live mode"

    def test_ctb_offline_zero_does_not_enable_live_trading(self, monkeypatch):
        """CTB_OFFLINE=0 is a DATA switch. It must not be a MONEY switch."""
        monkeypatch.setenv("CTB_OFFLINE", "0")
        assert offline_enabled() is False
        assert is_live_mode() is False

    def test_set_live_mode_without_confirm_raises(self):
        with pytest.raises(LiveModeError):
            set_live_mode(True)

    def test_set_live_mode_with_wrong_confirm_raises(self):
        with pytest.raises(LiveModeError):
            set_live_mode(True, confirm="yes")

    def test_set_live_mode_refuses_while_offline(self):
        with pytest.raises(LiveModeError, match="offline"):
            set_live_mode(True, confirm="I_HAVE_REVIEWED_THIS")

    def test_set_live_mode_refuses_without_credentials(self, monkeypatch):
        monkeypatch.setenv("CTB_OFFLINE", "0")
        monkeypatch.delenv("ALPACA_API_KEY", raising=False)
        with pytest.raises(LiveModeError, match="ALPACA_API_KEY"):
            set_live_mode(True, confirm="I_HAVE_REVIEWED_THIS")

    def test_offline_client_refuses_paper_false(self):
        from utils.offline import OfflineTradingClient
        with pytest.raises(LiveModeError):
            OfflineTradingClient(paper=False)

    def test_no_cli_argument_anywhere_enables_live_trading(self):
        """Grep the argv handling. --loop is the only flag any entry point takes."""
        suspicious = {"--live", "--real", "--real-money", "--production", "--prod"}
        for py in ROOT.rglob("*.py"):
            if ".venv" in str(py) or "/tests/" in str(py):
                continue
            src = py.read_text()
            for flag in suspicious:
                assert flag not in src, f"{py} accepts {flag}"


class TestPredictionAnalyzerHasNoOrderPath:
    """ch07.md:39 — 'The book is not going to ship an unauthenticated trading bot
    for a CFTC-regulated venue.' Honor the refusal. Forever."""

    def test_analyzer_does_not_import_the_kalshi_client(self):
        src = (ROOT / "prediction/prediction_analyzer.py").read_text()
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                names = [a.name for a in node.names]
                mod = getattr(node, "module", "") or ""
                assert "kalshi" not in mod.lower()
                assert not any("kalshi" in n.lower() for n in names)

    def test_analyzer_source_contains_no_order_submission_call(self):
        src = (ROOT / "prediction/prediction_analyzer.py").read_text()
        for token in ("submit_order", "place_order", "place_kalshi_order",
                      "post_order", "create_order", "requests.post",
                      "py_clob_client", "ClobClient"):
            assert token not in src, (
                f"prediction_analyzer.py contains {token!r}. It is READ-ONLY."
            )

    def test_analyzer_never_touches_the_clob_write_surface(self):
        src = (ROOT / "prediction/prediction_analyzer.py").read_text()
        assert "clob.polymarket.com" not in src

    def test_place_kalshi_order_refuses_without_the_code_level_optin(self):
        from prediction.kalshi_client import KalshiClient
        client = KalshiClient(key_id="not-a-real-key")
        with pytest.raises(LiveModeError, match="live mode is off"):
            client.place_kalshi_order("TICKER", "yes", 1, 50)


class TestNoNetwork:
    """The default path must not open a socket. Not one."""

    @pytest.fixture(autouse=True)
    def block_the_network(self, monkeypatch):
        def refuse(*args, **kwargs):
            raise AssertionError(
                "The offline path opened a network socket. The zero-key claim "
                "is the headline promise of this repo; it must be literally true."
            )
        monkeypatch.setattr(socket, "socket", refuse)
        monkeypatch.setattr(socket, "create_connection", refuse)

    def test_screener_makes_no_network_call(self):
        from screener.screener import run_screener
        assert run_screener() is not None

    def test_flow_trader_makes_no_network_call(self):
        from flow_trader.flow_trader import run_flow_trader
        run_flow_trader(single_cycle=True)

    def test_backtester_makes_no_network_call(self):
        from backtester.backtester import run_backtest
        assert run_backtest()["verdict"]

    def test_prediction_analyzer_makes_no_network_call(self):
        from prediction.prediction_analyzer import run_analyzer
        run_analyzer()

    def test_multi_agent_makes_no_network_call(self):
        from multi_agent.multi_agent import run_multi_agent_cycle
        assert run_multi_agent_cycle()

    def test_risk_manager_makes_no_network_call(self):
        from risk.risk_manager import demo_risk_check
        assert demo_risk_check()

    def test_verify_setup_makes_no_network_call(self):
        from setup.verify_setup import run
        assert run() == 0


class TestNoSecrets:
    def test_no_env_file_is_committed(self):
        assert not (ROOT / ".env").exists() or ".env" in (
            ROOT / ".gitignore").read_text()

    def test_gitignore_excludes_the_dangerous_paths(self):
        ignored = (ROOT / ".gitignore").read_text()
        for pattern in (".env", "venv/", "*.pem", "*.key"):
            assert pattern in ignored, f".gitignore is missing {pattern}"

    def test_no_pem_files_anywhere_in_the_tree(self):
        pems = [p for p in ROOT.rglob("*.pem") if ".venv" not in str(p)]
        assert pems == []

    def test_env_example_holds_only_obvious_placeholders(self):
        text = (ROOT / ".env.example").read_text()
        # No real-looking Anthropic key.
        assert "sk-ant-" not in text.replace("sk-ant-your-key-here", "")
        safe = {"CTB_OFFLINE": {"0", "1"}}
        for line in text.splitlines():
            if "=" not in line or line.strip().startswith("#"):
                continue
            key, value = (part.strip() for part in line.split("=", 1))
            if value in safe.get(key, set()):
                continue   # a documented non-secret switch, not a credential
            assert (
                value == ""
                or "your" in value.lower()
                or "example" in value.lower()
                or "paper-api" in value
                or "/path/to/" in value
            ), f"suspicious .env.example value: {line!r}"

    def test_deprecated_model_never_appears_in_code(self):
        for py in ROOT.rglob("*.py"):
            if ".venv" in str(py) or "/tests/" in str(py):
                continue
            assert "claude-sonnet-4-20250514" not in py.read_text(), (
                f"{py} uses the deprecated model. It retires June 15, 2026."
            )

    def test_no_mcp_config_json_anywhere(self):
        """ch02.md:353 exists specifically to kill this file. Do not resurrect it."""
        assert list(ROOT.rglob("mcp_config.json")) == []

    def test_unusual_whales_mcp_is_never_an_actual_dependency(self):
        """It may appear in a comment warning you off it — that mirrors the book
        (appendices.md:330). It must never appear as a real requirement."""
        for path in ("requirements.txt", "pyproject.toml"):
            for line in (ROOT / path).read_text().splitlines():
                stripped = line.strip()
                if stripped.startswith("#") or not stripped:
                    continue
                assert "unusual-whales-mcp" not in stripped, (
                    f"{path}: unusual-whales-mcp is a COMMUNITY FORK, not the "
                    f"official UW MCP server. It must never be installed. "
                    f"Offending line: {line!r}"
                )
