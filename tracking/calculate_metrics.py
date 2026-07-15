"""90-day tracking metrics — Chapter 10 (ch10.md:31-38).

Reads `tracking/daily_metrics.json` and reports win rate, annualized Sharpe, max
drawdown, profit factor, and profitable-weeks count.

    python tracking/calculate_metrics.py [path-to-daily_metrics.json]

Schema per entry (ch10.md:34):
    {date, trades_taken, trades_blocked_by_risk, wins, losses,
     daily_pnl_dollar, daily_pnl_pct, max_drawdown_pct, portfolio_value_close}

TWO PROFIT FACTORS, TWO NAMES (docs/book-deviations.md #7)
----------------------------------------------------------
The book defines profit factor twice, differently, and applies a >1.5 go/no-go
gate to it:

* **ch06** (backtester, and what ch09's Kelly consumes): *average* win / *average*
  loss. On the book's own numbers, 1.79.
* **ch10** (this file) and Appendix D: *sum* of winning profits / *sum* of losing
  losses. On the same numbers, 2.07.

They are different quantities. This module computes the ch10/Appendix-D
definition and calls it **`gross_profit_factor`** so one name never carries two
formulas. Never let one name carry two formulas.

One honest limitation: the `daily_metrics.json` schema the book specifies carries
only *daily* P&L, not per-trade P&L. So both profit factors here are computed
over **days**, not trades. The trade-level `R = avg win / avg loss` that ch09's
Kelly formula needs comes from the ch06 backtester's `report.json`, not from this
file. Swapping the sum-based value into Kelly silently breaks ch09's printed
example (0.537 - 0.463/2.07 = 0.313, not the printed 0.278).

Educational software. Not financial advice. See DISCLAIMER.md.
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils import artifact, banner, fixture  # noqa: E402

METRICS_FILE = "tracking/daily_metrics.json"
FIXTURE_METRICS = fixture("daily_metrics_go.json")

TRADING_DAYS_PER_YEAR = 252


def load_metrics(path=None) -> list[dict]:
    """Load the daily metrics log. Missing or empty is a valid state, not a crash."""
    if path is None:
        target = artifact(METRICS_FILE)
        if not target.exists():
            print(f"[offline] {METRICS_FILE} not found. Falling back to the "
                  f"bundled synthetic fixture: {FIXTURE_METRICS.name}")
            print("[offline] synthetic sample data — illustrative mechanics only.\n")
            target = FIXTURE_METRICS
    else:
        target = Path(path)
        if not target.is_absolute() and not target.exists():
            candidate = fixture(target.name)
            target = candidate if candidate.exists() else target
    try:
        with open(target) as f:
            data = json.load(f)
    except FileNotFoundError:
        return []
    except json.JSONDecodeError:
        print(f"WARNING: {target} is not valid JSON. Treating as no data.")
        return []
    return data if isinstance(data, list) else []


def _week_key(iso_date: str) -> tuple[int, int]:
    y, w, _ = date.fromisoformat(iso_date).isocalendar()
    return (y, w)


def calculate_metrics(entries: list[dict]) -> dict:
    """Compute the Phase-1 metric set. Handles the empty case gracefully."""
    if not entries:
        return {
            "days": 0, "trades": 0, "trades_blocked_by_risk": 0,
            "wins": 0, "losses": 0,
            "win_rate": None, "sharpe": None, "max_drawdown_pct": None,
            "gross_profit_factor": None, "avg_profit_factor": None,
            "profitable_weeks": 0, "total_weeks": 0,
            "total_pnl_dollar": 0.0,
            "note": "No data. Log at least one trading day before assessing.",
        }

    wins = sum(int(e.get("wins", 0)) for e in entries)
    losses = sum(int(e.get("losses", 0)) for e in entries)
    trades = sum(int(e.get("trades_taken", 0)) for e in entries)
    blocked = sum(int(e.get("trades_blocked_by_risk", 0)) for e in entries)
    decided = wins + losses
    win_rate = (wins / decided) if decided else None

    daily_pct = [float(e.get("daily_pnl_pct", 0.0)) / 100.0 for e in entries]
    daily_dollar = [float(e.get("daily_pnl_dollar", 0.0)) for e in entries]

    arr = np.array(daily_pct, dtype=float)
    sharpe = None
    if len(arr) > 1 and np.std(arr) > 0:
        sharpe = float(np.mean(arr) / np.std(arr) * np.sqrt(TRADING_DAYS_PER_YEAR))

    # Max drawdown recomputed from the equity curve rather than trusting the
    # per-row `max_drawdown_pct` field, which is a running value, not a period max.
    closes = [float(e.get("portfolio_value_close", 0.0)) for e in entries]
    max_dd = 0.0
    peak = closes[0] if closes else 0.0
    for value in closes:
        peak = max(peak, value)
        if peak > 0:
            max_dd = max(max_dd, (peak - value) / peak)

    # SUM-based (ch10.md:54, appendices.md:677). Named distinctly on purpose.
    # Computed over DAYS, because that is all the schema carries.
    gross_profit = sum(d for d in daily_dollar if d > 0)
    gross_loss = abs(sum(d for d in daily_dollar if d < 0))
    gross_pf = (gross_profit / gross_loss) if gross_loss > 0 else float("inf")

    # AVERAGE-based (ch06) — this is the R that ch09's Kelly formula needs.
    up_days = [d for d in daily_dollar if d > 0]
    down_days = [d for d in daily_dollar if d < 0]
    avg_pf = (abs(float(np.mean(up_days)) / float(np.mean(down_days)))
              if up_days and down_days else float("inf"))

    weeks: dict[tuple[int, int], float] = {}
    for e in entries:
        weeks.setdefault(_week_key(e["date"]), 0.0)
        weeks[_week_key(e["date"])] += float(e.get("daily_pnl_dollar", 0.0))
    profitable_weeks = sum(1 for v in weeks.values() if v > 0)

    return {
        "days": len(entries), "trades": trades,
        "trades_blocked_by_risk": blocked,
        "wins": wins, "losses": losses,
        "win_rate": win_rate,
        "sharpe": sharpe,
        "max_drawdown_pct": max_dd * 100,
        "gross_profit_factor": gross_pf,
        "avg_profit_factor": avg_pf,
        "profitable_weeks": profitable_weeks,
        "total_weeks": len(weeks),
        "total_pnl_dollar": sum(daily_dollar),
    }


def print_metrics(metrics: dict) -> None:
    banner()
    print("=== 90-DAY TRACKING METRICS ===\n")
    if metrics["days"] == 0:
        print(metrics["note"])
        print("\nSchema per entry: {date, trades_taken, trades_blocked_by_risk, "
              "wins, losses,\n  daily_pnl_dollar, daily_pnl_pct, "
              "max_drawdown_pct, portfolio_value_close}")
        return

    def fmt(x, spec="{:.2f}"):
        return "n/a" if x is None else spec.format(x)

    print(f"  Days logged:            {metrics['days']}")
    print(f"  Trades taken:           {metrics['trades']}")
    print(f"  Trades blocked by risk: {metrics['trades_blocked_by_risk']}")
    print(f"  Wins / losses:          {metrics['wins']} / {metrics['losses']}")
    print(f"  Win rate:               {fmt(metrics['win_rate'], '{:.1%}')}")
    print(f"  Sharpe (annualized):    {fmt(metrics['sharpe'])}")
    print(f"  Max drawdown:           {fmt(metrics['max_drawdown_pct'], '{:.1f}%')}")
    print(f"  Gross profit factor:    {fmt(metrics['gross_profit_factor'])}"
          f"   (sum of up days / sum of down days — the ch10 go/no-go metric)")
    print(f"  Avg profit factor:      {fmt(metrics['avg_profit_factor'])}"
          f"   (avg up day / avg down day)")
    print("\n  Both profit factors above are computed over DAYS: the "
          "daily_metrics.json\n  schema carries no per-trade P&L. The "
          "trade-level R that Kelly needs\n  comes from the ch06 backtester's "
          "report.json.")
    print(f"  Profitable weeks:       {metrics['profitable_weeks']} of "
          f"{metrics['total_weeks']}")
    print(f"  Total P&L:              ${metrics['total_pnl_dollar']:+,.2f}")


def main(argv: list[str]) -> int:
    path = argv[1] if len(argv) > 1 else None
    entries = load_metrics(path)
    print_metrics(calculate_metrics(entries))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
