"""`make demo` — the offline demo. Two modes, zero keys, one command.

Default (`make demo`) is a **diagnostic**: it runs the backtester across three
synthetic scenarios — no edge, overfit, and an edge candidate — so the first
thing you see is the tool telling strategies apart, not a single green verdict.
A trading tool that only ever says "EDGE CONFIRMED" teaches the wrong reflex.

`make tour` (`python tools/demo.py --tour`) runs every catalog item end to end.

Nothing here touches the network, and nothing here can place a real order.
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

TOUR_STEPS = [
    ("Setup gate (ch02)", ["setup/verify_setup.py"],
     "four connections, one script"),
    ("Screener (ch04)", ["screener/screener.py"],
     "scan the flow, rank a watchlist"),
    ("Flow trader (ch05)", ["flow_trader/flow_trader.py"],
     "one polling cycle: detect, analyze, decide, execute"),
    ("Positions (ch05)", ["flow_trader/check_positions.py"],
     "what the bot is holding"),
    ("Backtester (ch06)", ["backtester/backtester.py"],
     "1,000 Monte Carlo sims and a verdict"),
    ("Prediction analyzer (ch07)", ["prediction/prediction_analyzer.py"],
     "rank mispriced contracts — read-only, never bets"),
    ("Multi-agent (ch08)", ["multi_agent/multi_agent.py"],
     "Monitor -> Analyst -> Risk -> Executor"),
    ("Risk manager (ch09)", ["risk/risk_manager.py"],
     "five hard rules, quarter-Kelly, a zero floor"),
    ("Tracking (ch10)", ["tracking/phase1_assessment.py"],
     "the Day-30 go/no-go gate"),
]

DIAGNOSE_STEPS = [
    ("No edge (ch06)", ["backtester/backtester.py", "--scenario", "no_edge"],
     "a consistent strategy that still isn't worth trading"),
    ("Overfit (ch06)", ["backtester/backtester.py", "--scenario", "overfit"],
     "great in-sample, falls apart out-of-sample"),
    ("Edge candidate (ch06)", ["backtester/backtester.py", "--scenario", "edge_candidate"],
     "the one shape that clears the gate — a fixture property, not proof"),
]

BANNER = """
==============================================================================
  claude-trading-bot — offline demo

  No API keys. No .env. No network. No broker account.
  Every number below is computed by this repo's own code against committed
  synthetic fixtures, and predicts nothing about real markets.

  Educational software. Not financial advice. See DISCLAIMER.md.
==============================================================================
"""


def _run(steps) -> list[str]:
    failures = []
    for i, (name, argv, blurb) in enumerate(steps, 1):
        print(f"\n{'-' * 78}")
        print(f"[{i}/{len(steps)}] {name} — {blurb}")
        print(f"    $ python {' '.join(argv)}")
        print(f"{'-' * 78}\n")
        result = subprocess.run([sys.executable, *argv], cwd=ROOT)
        if result.returncode != 0:
            failures.append(name)
    return failures


def diagnose() -> int:
    print(BANNER)
    print("  DIAGNOSTIC DEMO — the backtester on three different strategies.")
    print("  Watch the verdict change. That is the whole skill: telling a real")
    print("  edge from a lucky sample from an overfit fit.\n")
    started = time.time()
    failures = _run(DIAGNOSE_STEPS)
    elapsed = time.time() - started
    print(f"\n{'=' * 78}")
    if failures:
        print(f"  {len(failures)} step(s) FAILED: {', '.join(failures)}")
        print(f"{'=' * 78}")
        return 1
    print(f"  Three scenarios ran offline in {elapsed:.1f}s, with no API keys.")
    print()
    print("  Three strategies, three verdicts: NO EDGE, OVERFIT, EDGE CONFIRMED.")
    print("  The interesting question is not 'did it pass?' It is: which check")
    print("  produced each verdict, and what would you need to see before you")
    print("  trusted any of them with real money?")
    print()
    print("  Next:")
    print("    make tour                # every bot end to end")
    print("    make demo-ch06-no-edge   # one scenario at a time, with full output")
    print("    docs/book-deviations.md  # where this repo and the book differ")
    print(f"{'=' * 78}")
    return 0


def tour() -> int:
    print(BANNER)
    print("  FULL TOUR — every catalog item, end to end.\n")
    started = time.time()
    failures = _run(TOUR_STEPS)
    elapsed = time.time() - started
    print(f"\n{'=' * 78}")
    if failures:
        print(f"  {len(failures)} step(s) FAILED: {', '.join(failures)}")
        print(f"{'=' * 78}")
        return 1
    print(f"  All {len(TOUR_STEPS)} items ran offline in {elapsed:.1f}s, with no API "
          f"keys.")
    print("  That is the whole claim of this repository, and you just checked it.")
    print()
    print("  Every verdict you saw is computed on a synthetic fixture chosen to")
    print("  exercise the happy path — it is NOT evidence of an edge. To see what")
    print("  the tools do when a strategy DOESN'T work:")
    print("    make demo                # the diagnostic: no-edge vs overfit vs edge")
    print("    make demo-ch06-overfit   # one failing scenario, full output")
    print(f"{'=' * 78}")
    return 0


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if "--tour" in argv:
        return tour()
    return diagnose()


if __name__ == "__main__":
    raise SystemExit(main())
