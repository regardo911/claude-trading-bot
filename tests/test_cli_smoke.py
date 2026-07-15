"""Every reader-facing command in section 3.5, run as a subprocess.

No key. No .env. No network. Exit 0, and the expected output shape.
"""
from __future__ import annotations

import os
import pathlib
import subprocess
import sys

import pytest

ROOT = str(pathlib.Path(__file__).resolve().parent.parent)

COMMANDS = [
    ("setup/verify_setup.py", ["Result: 4/4 checks passed"]),
    ("setup/test_claude.py", []),
    ("setup/test_alpaca.py", ["Account status: ACTIVE", "Cash: $100,000.00"]),
    ("screener/screener.py", ["unusual transactions after filtering",
                              "DAILY WATCHLIST"]),
    ("screener/tracker.py", []),
    ("flow_trader/flow_trader.py", ["OPTIONS FLOW TRADER STARTED",
                                    "Confidence threshold: 70%"]),
    ("flow_trader/check_positions.py", ["POSITIONS"]),
    ("backtester/backtester.py", ["BACKTEST RESULTS", "VERDICT:",
                                  "Monte Carlo Results"]),
    ("prediction/prediction_analyzer.py", ["active markets",
                                           "analyzable contracts"]),
    ("prediction/calibration.py", []),
    ("multi_agent/multi_agent.py", ["[MONITOR]", "[ANALYST]", "[RISK]",
                                    "[EXECUTOR]"]),
    ("risk/risk_manager.py", ["RISK MANAGEMENT MODULE", "REJECTED-NO-EDGE"]),
    ("tracking/calculate_metrics.py", ["TRACKING METRICS"]),
    ("tracking/phase1_assessment.py", ["VERDICT:"]),
]


def _run(args, timeout=120):
    env = dict(os.environ)
    env["CTB_OFFLINE"] = "1"
    for key in ("ANTHROPIC_API_KEY", "UW_API_KEY", "ALPACA_API_KEY",
                "ALPACA_SECRET_KEY", "KALSHI_KEY_ID"):
        env.pop(key, None)
    return subprocess.run([sys.executable, *args], cwd=ROOT, env=env,
                          capture_output=True, text=True, timeout=timeout)


@pytest.mark.parametrize("script,expected", COMMANDS,
                         ids=[c[0] for c in COMMANDS])
def test_reader_facing_command_runs_offline(script, expected):
    result = _run([script])
    assert result.returncode == 0, (
        f"{script} exited {result.returncode}\n"
        f"stdout:\n{result.stdout[-2000:]}\nstderr:\n{result.stderr[-2000:]}"
    )
    for token in expected:
        assert token in result.stdout, f"{script} did not print {token!r}"


def test_multi_agent_cycle_completes_in_under_60_seconds():
    """ch08.md:703 — 'The cycle completes in under 60 seconds.'"""
    import time
    start = time.time()
    result = _run(["multi_agent/multi_agent.py"], timeout=60)
    assert result.returncode == 0
    assert time.time() - start < 60


def test_phase1_assessment_handles_an_empty_metrics_file():
    result = _run(["tracking/phase1_assessment.py", "daily_metrics_empty.json"])
    assert result.returncode == 0
    assert "NO DATA" in result.stdout


def test_backtester_never_prints_the_books_illustrative_figures():
    result = _run(["backtester/backtester.py"])
    for figure in ("108,400", "127,600", "152,300"):
        assert figure not in result.stdout, (
            f"The backtester printed {figure}, one of the book's illustrative "
            f"Monte Carlo figures. It must print what THIS code computes."
        )


def test_every_run_is_labelled_synthetic():
    result = _run(["backtester/backtester.py"])
    combined = result.stdout + result.stderr
    assert "synthetic" in combined.lower()
