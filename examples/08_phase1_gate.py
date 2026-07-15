"""Example — the ch10 Day-30 gate on all three fixture states.

GO, HOLD, and the empty-file case the book's own prompt asks you to test:
"Run `phase1_assessment.py` against an empty `daily_metrics.json` so I can verify
it handles the no-data case gracefully." (ch10.md:38)
"""
import _bootstrap  # noqa: F401

from tracking.calculate_metrics import calculate_metrics, load_metrics
from tracking.phase1_assessment import assess

if __name__ == "__main__":
    for fixture in ("daily_metrics_go.json", "daily_metrics_hold.json",
                    "daily_metrics_empty.json"):
        metrics = calculate_metrics(load_metrics(fixture))
        result = assess(metrics)
        print(f"\n=== {fixture} ({metrics['days']} days logged) ===")
        for name, value, state in result["rows"]:
            print(f"  {name:<22}{value:<12}{state}")
        print(f"  VERDICT: {result['verdict']}")
    print("\nA verdict on zero data is not a verdict. That is why the empty case "
          "returns\nNO DATA rather than quietly passing or quietly failing.")
