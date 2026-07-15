"""Calibration tracker — Chapter 7 (ch07.md:523-559).

Calibration means checking whether Claude's probability estimates match reality.
If Claude says 60% on 100 contracts, about 60 should resolve YES. If 80 do, it is
systematically underconfident (the edge is bigger than you thought). If 40 do, it
is overconfident and you are betting on false signals.

Run this after 30+ resolved contracts:

    python prediction/calibration.py

Educational software. Not financial advice. See DISCLAIMER.md.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils import artifact  # noqa: E402

CALIBRATION_FILE = "prediction/calibration.json"
MIN_RESOLVED = 30


def _load() -> list:
    try:
        with open(artifact(CALIBRATION_FILE)) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def update_calibration(question, claude_estimate, resolved_yes) -> dict:
    """Record one resolved contract: what Claude said, and what happened."""
    data = _load()
    entry = {
        "question": question,
        "estimate": claude_estimate,
        "actual": 1 if resolved_yes else 0,
    }
    data.append(entry)
    with open(artifact(CALIBRATION_FILE), "w") as f:
        json.dump(data, f, indent=2)
    return entry


def print_calibration() -> None:
    """Bucket the estimates by decile and compare to the realized YES rate."""
    data = _load()
    if not data:
        print("No calibration data yet.")
        print("Log resolved contracts with "
              "update_calibration(question, estimate, resolved_yes).")
        return

    buckets: dict[float, dict[str, int]] = {}
    for d in data:
        bucket = round(d["estimate"], 1)
        buckets.setdefault(bucket, {"total": 0, "yes": 0})
        buckets[bucket]["total"] += 1
        buckets[bucket]["yes"] += d["actual"]

    print(f"=== CALIBRATION ({len(data)} resolved contracts) ===")
    if len(data) < MIN_RESOLVED:
        print(f"NOTE: fewer than {MIN_RESOLVED} resolved contracts. These buckets "
              f"are noise, not calibration. Keep logging.\n")
    for b in sorted(buckets):
        t = buckets[b]["total"]
        y = buckets[b]["yes"]
        print(f"  {b:.0%} bucket: {t} bets, {y / t:.0%} resolved YES")
    print("\nWell calibrated means the 60% bucket resolves YES about 60% of the "
          "time. Consistently off? Raise MIN_PROBABILITY_GAP.")


if __name__ == "__main__":
    print_calibration()
