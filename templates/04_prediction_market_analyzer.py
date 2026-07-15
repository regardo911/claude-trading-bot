"""Template 4 — Prediction Market Analyzer (appendices.md:463-473).

Use case: daily scan of Polymarket / Kalshi for mispriced contracts.

Shipped as: `prediction/prediction_analyzer.py` -- READ-ONLY. It never bets.
"""

MIN_PROBABILITY_GAP = 0.10    # 10% minimum gap between market and our estimate
MAX_BET_SIZE = 50             # see the erratum below
MIN_VOLUME = 10000            # minimum market volume for liquidity
CONFIDENCE_FILTER = ["HIGH", "MEDIUM"]   # skip LOW-confidence estimates

# ERRATUM (docs/book-deviations.md #9): under the formula the chapter prints,
#   suggested_bet = min(MAX_BET_SIZE, MAX_BET_SIZE * abs(gap))
# the min() only binds at a 100% gap. MAX_BET_SIZE is therefore a scaling
# COEFFICIENT, not a cap -- which contradicts both its own comment and the word
# "cap" in the prose. A qualifying 10% gap sizes a $5 bet, not $25.

# ERRATUM (docs/book-deviations.md #1): MIN_VOLUME is declared in the chapter and
# referenced by nothing. Appendix B lists it as a live tunable. The repo actually
# filters on it.

# WHEN TO ADJUST
#   Volatile news periods ... MIN_PROBABILITY_GAP -> 0.15 (markets are efficient)
#   30+ days of calibration . MAX_BET_SIZE -> 100-200, but only if the buckets
#                             show Claude beating the market price
