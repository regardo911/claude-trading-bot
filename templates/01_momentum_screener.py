"""Template 1 — Momentum Screener (appendices.md:420-433).

Use case: daily scan for stocks with unusual options activity and positive
momentum signals.

Shipped as: `screener/screener.py`.
Expected output: 5-10 stocks per day with direction, confidence, and reasoning.
"""

VOL_OI_THRESHOLD = 3.0        # volume / open-interest ratio minimum
MIN_PREMIUM = 200000          # $200K minimum transaction size
CONFIDENCE_THRESHOLD = 65     # minimum confidence to include in the watchlist
TRANSACTION_TYPES = ["sweep", "block"]
RUN_TIME = "09:35"            # 5 minutes after the open; the first five are chaos

# WHEN TO ADJUST
#   VIX above 25 ....... VOL_OI_THRESHOLD -> 5.0, MIN_PREMIUM -> 500_000
#   VIX below 15 ....... MIN_PREMIUM -> 150_000
#   Small caps ......... MIN_PREMIUM -> 100_000
#   Too many false +ve . CONFIDENCE_THRESHOLD -> 70
#   Earnings season .... exclude names reporting within 5 days
#   Fed announcement ... skip the run entirely; the flow means nothing that day
