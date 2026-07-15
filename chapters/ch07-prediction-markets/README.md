# Chapter 7 lab: prediction markets

Rank Polymarket and Kalshi contracts where the market probability and the model's
estimate disagree. It finds mispricings and never bets them: read-only, by design.

## Read-only, and it stays that way
Paste [`prompts/07_prediction_analyzer.md`](../../prompts/07_prediction_analyzer.md).
The Kalshi client and the estimate ranker are
[`08_kalshi_client.md`](../../prompts/08_kalshi_client.md) and
[`09_live_data_estimates.md`](../../prompts/09_live_data_estimates.md). You get
[`prediction/prediction_analyzer.py`](../../prediction/prediction_analyzer.py) plus
`calibration.py` and `kalshi_client.py`.

## Run it
```bash
python prediction/prediction_analyzer.py
```
```
=== PREDICTION MARKET ANALYZER ===
Read-only: this script never submits an order.
Found 11 active markets.
... ranked opportunities by probability gap ...
```

## The guarantee, in code
The analyzer has no order-submission path at all. A test proves it imports nothing
named `kalshi` and contains no `submit_order`, `place_order`, or `requests.post`. The
book refuses to ship an unauthenticated trading bot for a CFTC-regulated venue, and
this repo enforces that refusal in code. Note the `$50 (see erratum #9)` line too:
`MAX_BET_SIZE` is a scaling coefficient, not a cap
([book-deviations.md #9](../../docs/book-deviations.md#9)).

---
Reference: [docs/05-prediction.md](../../docs/05-prediction.md)
