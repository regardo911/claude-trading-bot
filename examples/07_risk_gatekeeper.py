"""Example — the ch09 gatekeeper, and the 40% cap the book's own check misses.

Rule 1 sizes NVDA at 72 shares — exactly what the chapter prints. That is a
$66,600 position on a $100K account: 66.6% of the portfolio in one tech name.

The printed `check_sector_concentration()` approves it, because it sums only
*existing* holdings and the portfolio is empty. This repo includes the proposed
position, so the 40% cap binds and the trade is REDUCED. The chapter's own
`check_correlation()` helper does exactly this — the sector check just forgot to.
"""
import _bootstrap  # noqa: F401

from risk.risk_manager import demo_risk_check

if __name__ == "__main__":
    demo_risk_check()
