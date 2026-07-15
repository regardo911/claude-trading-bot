"""Template 3 — Options Flow Follower (appendices.md:450-461).

Use case: real-time monitoring and automatic trading on institutional options
flow.

Shipped as: `flow_trader/flow_trader.py`.
"""

POLL_INTERVAL = 30            # seconds between UW REST polls
MIN_PREMIUM = 500000          # $500K for real-time trading
CONFIDENCE_THRESHOLD = 70     # the trade gate
MAX_POSITION_PCT = 0.02       # 2% of account per trade -- NOTIONAL, not risk.
EXPIRATION_MAX_DAYS = 14      # only trade options expiring within 2 weeks

# MAX_POSITION_PCT (2% notional) and risk_manager.MAX_RISK_PER_TRADE (2% RISK)
# are different quantities that happen to share a number. The book reconciles
# them deliberately: the risk module is the gatekeeper that overrides this naive
# sizing. Do not unify them. (docs/book-deviations.md #5)

# WHEN TO ADJUST
#   Higher-tier UW API . POLL_INTERVAL -> 15 (doubles UW calls, not Anthropic)
#   Earnings season .... MIN_PREMIUM -> 1_000_000
#   Quiet market ....... CONFIDENCE_THRESHOLD -> 65
