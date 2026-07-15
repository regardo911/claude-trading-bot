"""Screener outcome tracker — Chapter 4 (ch04.md:362-406).

Each evening after the close, check which screener picks moved in the predicted
direction over the next 1-5 trading days and record the result. After two weeks,
`print_stats()` gives you a hit rate — overall, and for the 70%+ band that is the
only one you should be trading. This data feeds the Chapter 6 backtester.

Educational software. Not financial advice. See DISCLAIMER.md.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils import artifact  # noqa: E402

TRACKING_FILE = "screener/tracking.json"


def load_tracking() -> list:
    try:
        with open(artifact(TRACKING_FILE)) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def record_outcome(date, ticker, direction, confidence, actual_move) -> dict:
    """Record what a pick actually did. `actual_move` is a percentage."""
    tracking = load_tracking()
    correct = ((direction == "BULLISH" and actual_move > 0) or
               (direction == "BEARISH" and actual_move < 0))
    entry = {
        "date": date, "ticker": ticker,
        "direction": direction, "confidence": confidence,
        "actual_move_pct": actual_move, "correct": correct,
        "recorded_at": datetime.now().isoformat(),
    }
    tracking.append(entry)
    with open(artifact(TRACKING_FILE), "w") as f:
        json.dump(tracking, f, indent=2)
    return entry


def print_stats() -> None:
    tracking = load_tracking()
    if not tracking:
        print("No tracking data yet.")
        print("Record outcomes with record_outcome(date, ticker, direction, "
              "confidence, actual_move) as your picks resolve.")
        return
    total = len(tracking)
    correct = len([t for t in tracking if t["correct"]])
    high = [t for t in tracking if t["confidence"] >= 70]
    high_correct = len([t for t in high if t["correct"]])
    print(f"Total predictions: {total}")
    print(f"Overall win rate: {correct / total * 100:.1f}%")
    if high:
        print(f"High confidence (70%+): {len(high)} predictions, "
              f"{high_correct / len(high) * 100:.1f}% correct")
    else:
        print("High confidence (70%+): no resolved picks yet.")


if __name__ == "__main__":
    print_stats()
