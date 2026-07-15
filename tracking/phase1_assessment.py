"""Phase-1 go/no-go assessment — Chapter 10 (ch10.md:36-38, 58-68).

Runs the metrics on the last 30 days and produces a PASS/FAIL verdict against the
Phase-1 criteria. Run it on Day 30. If the verdict is GO, switch `.env`
`ALPACA_BASE_URL` from the paper URL to the live URL and deposit $500 — not
before.

    python tracking/phase1_assessment.py                       # bundled GO fixture
    python tracking/phase1_assessment.py daily_metrics_hold.json
    python tracking/phase1_assessment.py daily_metrics_empty.json   # the no-data case

| Metric           | Go                        | No-Go            |
|------------------|---------------------------|------------------|
| Win rate         | >50% (or >45% with PF>1.5)| <45%             |
| Sharpe ratio     | >1.0                      | <0.8             |
| Max drawdown     | <15%                      | >20%             |
| Profit factor    | >1.5                      | <1.2             |
| Profitable weeks | 3 of 4+                   | 1 of 4           |

Anything between Go and No-Go: extend Phase 1 by two weeks and recheck.

The profit factor gated here is the **sum-based** one (`gross_profit_factor`) —
which is what ch10 and Appendix D define. See docs/book-deviations.md (#7).

Educational software. Not financial advice. See DISCLAIMER.md.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tracking.calculate_metrics import calculate_metrics, load_metrics  # noqa: E402
from utils import banner  # noqa: E402

PHASE1_DAYS = 30

GO = {"win_rate": 0.50, "win_rate_with_pf": 0.45, "sharpe": 1.0,
      "max_drawdown_pct": 15.0, "profit_factor": 1.5, "profitable_weeks": 3}
NO_GO = {"win_rate": 0.45, "sharpe": 0.8, "max_drawdown_pct": 20.0,
         "profit_factor": 1.2, "profitable_weeks": 1}


def assess(metrics: dict) -> dict:
    """GO / HOLD / NO-GO against the Phase-1 table. Handles no data gracefully."""
    if metrics["days"] == 0:
        return {
            "verdict": "NO DATA",
            "rows": [],
            "message": (
                "No trading days logged yet. There is nothing to assess.\n"
                "Log a row into tracking/daily_metrics.json every night of Phase 1, "
                "then run this again on Day 30.\n"
                "A verdict on zero data is not a verdict."
            ),
        }

    wr = metrics["win_rate"]
    sharpe = metrics["sharpe"]
    dd = metrics["max_drawdown_pct"]
    pf = metrics["gross_profit_factor"]
    weeks = metrics["profitable_weeks"]

    rows = []

    # Win rate: >50%, OR >45% when the profit factor is above 1.5.
    if wr is None:
        rows.append(("Win rate", "n/a", "NO-GO"))
    elif wr > GO["win_rate"] or (wr > GO["win_rate_with_pf"] and pf is not None
                                 and pf > GO["profit_factor"]):
        rows.append(("Win rate", f"{wr:.1%}", "GO"))
    elif wr < NO_GO["win_rate"]:
        rows.append(("Win rate", f"{wr:.1%}", "NO-GO"))
    else:
        rows.append(("Win rate", f"{wr:.1%}", "HOLD"))

    if sharpe is None:
        rows.append(("Sharpe ratio", "n/a", "HOLD"))
    elif sharpe > GO["sharpe"]:
        rows.append(("Sharpe ratio", f"{sharpe:.2f}", "GO"))
    elif sharpe < NO_GO["sharpe"]:
        rows.append(("Sharpe ratio", f"{sharpe:.2f}", "NO-GO"))
    else:
        rows.append(("Sharpe ratio", f"{sharpe:.2f}", "HOLD"))

    if dd < GO["max_drawdown_pct"]:
        rows.append(("Max drawdown", f"{dd:.1f}%", "GO"))
    elif dd > NO_GO["max_drawdown_pct"]:
        rows.append(("Max drawdown", f"{dd:.1f}%", "NO-GO"))
    else:
        rows.append(("Max drawdown", f"{dd:.1f}%", "HOLD"))

    pf_label = "inf" if pf == float("inf") else f"{pf:.2f}"
    if pf > GO["profit_factor"]:
        rows.append(("Gross profit factor", pf_label, "GO"))
    elif pf < NO_GO["profit_factor"]:
        rows.append(("Gross profit factor", pf_label, "NO-GO"))
    else:
        rows.append(("Gross profit factor", pf_label, "HOLD"))

    weeks_label = f"{weeks} of {metrics['total_weeks']}"
    if weeks >= GO["profitable_weeks"]:
        rows.append(("Profitable weeks", weeks_label, "GO"))
    elif weeks <= NO_GO["profitable_weeks"]:
        rows.append(("Profitable weeks", weeks_label, "NO-GO"))
    else:
        rows.append(("Profitable weeks", weeks_label, "HOLD"))

    states = [r[2] for r in rows]
    if "NO-GO" in states:
        verdict = "NO-GO"
        message = ("At least one metric hit No-Go. Stop and fix the problem. Do "
                   "not deposit real money.")
    elif all(s == "GO" for s in states):
        verdict = "GO"
        message = ("All five metrics cleared. You may proceed to Phase 2: switch "
                   "ALPACA_BASE_URL to the live URL and deposit $500 — $500, not "
                   "$5,000.\nThe live path also needs the code-level opt-in: "
                   'set_live_mode(True, confirm="I_HAVE_REVIEWED_THIS").')
    else:
        verdict = "HOLD"
        message = ("Metrics fall between Go and No-Go. Extend Phase 1 by two "
                   "weeks and recheck. There is no rush; the strategies work "
                   "every trading day.")

    if metrics["days"] < PHASE1_DAYS:
        message = (f"NOTE: only {metrics['days']} of {PHASE1_DAYS} days logged. "
                   f"This verdict is provisional.\n" + message)

    return {"verdict": verdict, "rows": rows, "message": message}


def main(argv: list[str]) -> int:
    banner()
    path = argv[1] if len(argv) > 1 else None
    entries = load_metrics(path)
    metrics = calculate_metrics(entries[-PHASE1_DAYS:] if entries else [])
    result = assess(metrics)

    print("=== PHASE 1 GO/NO-GO ASSESSMENT (Day 30) ===\n")
    if result["rows"]:
        print(f"  {'Metric':<22}{'Value':<12}{'State'}")
        print(f"  {'-' * 40}")
        for name, value, state in result["rows"]:
            print(f"  {name:<22}{value:<12}{state}")
        print()
    print(f"VERDICT: {result['verdict']}\n")
    print(result["message"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
