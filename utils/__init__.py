"""Shared utilities — Chapter 2 ("Shared code (API connections, data formatting, logging)", ch02.md:361).

Nothing in here is a strategy. It is the plumbing every bot in the book leans
on: where the repo root is, where artifacts get written, and the one-line
disclaimer banner that any risk-carrying entry point prints on startup.

The offline switch itself lives in `utils.offline`.
"""

from __future__ import annotations

import sys
from pathlib import Path

__all__ = [
    "ROOT",
    "FIXTURES",
    "artifact",
    "fixture",
    "banner",
    "SHORT_DISCLAIMER",
]

#: Repository root. Every book path (`screener/watchlist_*.json`,
#: `flow_trader/trade_log.json`, ...) is written relative to this, so
#: `python screener/screener.py` behaves the same from any working directory.
ROOT = Path(__file__).resolve().parent.parent

#: Bundled deterministic synthetic fixtures. Zero keys, zero network.
FIXTURES = ROOT / "fixtures"

SHORT_DISCLAIMER = (
    "Educational software. Not financial advice. Paper mode by default. "
    "Figures below are computed on synthetic sample data and do not predict "
    "real results. See DISCLAIMER.md."
)

_BANNER_SHOWN = False


def artifact(relative: str) -> Path:
    """Resolve one of the book's artifact paths against the repo root.

    The book writes `screener/watchlist_YYYYMMDD.json`, `backtester/report.json`,
    and friends as bare relative paths, which only works when the reader's shell
    happens to sit in the project root. Routing them through here keeps the exact
    filenames the book prints while making the scripts runnable from anywhere.
    """
    path = ROOT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def fixture(name: str) -> Path:
    """Resolve a bundled synthetic fixture by filename."""
    return FIXTURES / name


def banner(stream=sys.stdout) -> None:
    """Print the one-line disclaimer banner. Idempotent per process."""
    global _BANNER_SHOWN
    if _BANNER_SHOWN:
        return
    _BANNER_SHOWN = True
    print(f"[!] {SHORT_DISCLAIMER}", file=stream)
