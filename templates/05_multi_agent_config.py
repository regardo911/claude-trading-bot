"""Template 5 — Multi-Agent Configuration (appendices.md:475-488).

Use case: configure the four-agent system from Chapter 8.

Shipped as: `multi_agent/multi_agent.py`.
"""

CYCLE_INTERVAL = 1800             # 30 minutes between cycles
MAX_RECOMMENDATIONS = 3           # the Analyst returns 3 max
RISK_OVERRIDE_THRESHOLD = 0.40    # sector concentration limit
DAILY_LOSS_HALT = 0.06            # 6% daily loss triggers a halt
MONITOR_ALERT_THRESHOLD = 0.03    # 3% position loss triggers an alert
REVISION_ENABLED = False          # one-loop revision cycle; DOUBLES the API calls
MODEL = "claude-sonnet-4-6"       # default

# ADVANCED_MODEL = "claude-opus-4-7"
#   Optional production upgrade for the Analyst + Risk Manager. Roughly 1.7x the
#   cost of Sonnet 4.6, but noticeably tighter on edge-case risk evaluations.
#   Default to Sonnet; upgrade selectively.
#
# Do NOT use the old Sonnet 4 dated alias -- it is deprecated and retires
# June 15, 2026. See docs/troubleshooting.md.

# WHEN TO ADJUST
#   Risk rejected trades that later proved profitable . REVISION_ENABLED = True
#   High-volatility days ............................. CYCLE_INTERVAL -> 900
