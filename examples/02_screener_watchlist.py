"""Example — the ch04 screener, and the ch03 rules the book never coded.

Watch three post-filters bite:
  * BABA takes a -15 geopolitical penalty and drops out of the watchlist.
  * AMD takes a -20 Tier1/Tier2 conflict penalty (flow says up, dark pool says
    down) and drops from 71 to 51.
  * IRNT is blocked outright: 418K average daily shares is below the 1M floor.
"""
import _bootstrap  # noqa: F401

from screener.screener import CONFIDENCE_THRESHOLD, run_screener

if __name__ == "__main__":
    watchlist = run_screener()
    print(f"\n{len(watchlist)} name(s) cleared the {CONFIDENCE_THRESHOLD}% floor.")
    for r in watchlist:
        flag = "  [MANUAL REVIEW]" if r.get("manual_review") else ""
        print(f"  {r['ticker']:<6} {r['direction']:<8} {r['confidence']:.0f}%{flag}")
