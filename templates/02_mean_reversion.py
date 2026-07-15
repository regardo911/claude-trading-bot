"""Template 2 — Mean Reversion (appendices.md:435-448). TEMPLATE ONLY.

The book describes this strategy and never builds it, so neither does this repo:
a companion repo that invents modules the book does not have is not a companion
repo. The parameters are here so you can build it yourself.

How it works (the book's description):
    Compute the 20-day simple moving average and standard deviation for each
    name. More than 2 sd BELOW the mean (oversold) signals a buy; more than 2 sd
    ABOVE (overbought) signals a sell. Claude adds a layer on top: is the
    deviation caused by news (likely to persist) or panic (likely to revert)?
"""

LOOKBACK_DAYS = 20            # rolling average period
DEVIATION_THRESHOLD = 2.0     # standard deviations from the mean
MIN_DAILY_VOLUME = 1000000    # minimum average daily volume (ch03's floor)
HOLD_PERIOD = 5               # trading days to hold
STOP_LOSS = 0.03              # 3% stop-loss

# WHEN TO ADJUST
#   Swing trading ...... LOOKBACK_DAYS -> 50
#   More signals ....... DEVIATION_THRESHOLD -> 1.5 (lower conviction, though)
