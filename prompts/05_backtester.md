# 05 — Build the Monte Carlo backtester

> **Source:** Chapter 6 (The Code: backtester.py) · `ch06.md:63`
> Quoted **verbatim** from the manuscript; do not edit the prompt body below.

## The prompt

Open Claude Code in your project directory (`cd ~/ai-trading-bot && claude`) and
paste:

```text
"Build me a Monte Carlo backtester for the screener strategy. This is an **offline deterministic backtester**; it never calls Claude or any other LLM. The reasoning happens in the Monte Carlo math, not in a model. Do NOT import or initialize `anthropic`; the code should be pure pandas + numpy + yfinance + matplotlib.

1. Load historical unusual options flow from a local CSV at `backtester/historical_flow.csv`. Expected columns: `date` (YYYY-MM-DD), `ticker`, `strike`, `expiry`, `type` (call/put), `volume`, `open_interest`, `volume_oi_ratio`, `total_premium`, `has_sweep` (bool), `has_floor` (bool). Apply the same Chapter 4 filters: `volume_oi_ratio` > 3.0, `total_premium` > $200K, `has_sweep` OR `has_floor`. If the CSV is missing, print clear instructions on how to populate it (UW Data Shop download or a day-by-day loop over `GET /api/option-trades/full-tape/{date}`).
2. For each filtered event, calculate the 5-day forward return on the underlying stock by fetching the close price on the event date and the close 5 trading days later from yfinance. If yfinance returns no data for that ticker/date, skip the event.
3. **In-sample vs out-of-sample split.** Sort trades chronologically. Split at the midpoint: first half = in-sample, second half = out-of-sample. Compute win rate and Sharpe ratio for each half separately, plus the gap in percentage points. If `abs(in_sample_win_rate - out_of_sample_win_rate) > 5pp` OR `out_of_sample_sharpe < in_sample_sharpe - 0.5`, flag `overfit=True` in the report. Print both rows under an "OVERFITTING CHECK" section before the Monte Carlo runs.
4. Run 1,000 Monte Carlo simulations on the FULL trade set: randomly shuffle the trade-return sequence, simulate the equity curve with 2% position sizing, track the final value and max drawdown.
5. Report: Strategy stats (total trades, win rate, avg winner, avg loser, profit factor, Sharpe ratio); Overfitting check (in-sample/out-of-sample win rates, gap, Sharpe in/out, overfit flag); Monte Carlo results (5th/25th/50th/75th/95th percentile final values, median + worst max drawdown); VERDICT: 'EDGE CONFIRMED' if 5th percentile > starting capital AND overfit flag is False, 'OVERFIT' if the split fails, else 'NO EDGE'.
6. Plot the fan chart (1,000 equity curves overlaid) with median + 5th + 95th percentile bands. Save as `backtester/monte_carlo.png`.
7. Save the full report (including the overfitting-check section) as `backtester/report.json`.

Important: do not invent a 180-day REST range query against UW. That endpoint does not exist. Historical options flow comes from UW Data Shop downloads or a loop over `GET /api/option-trades/full-tape/{date}` (one date per call). The backtester reads from a local CSV that I populate before running.

No LLM model is required for this script. Save as `backtester/backtester.py` and run it."
```

## Expected output schema

No model output at all. **This is the one artifact in the book with no LLM in it**:
"Do NOT import or initialize `anthropic`". The output is `backtester/report.json`
plus `backtester/monte_carlo.png`.

## How deterministic code consumes it

`backtester/backtester.py`, end to end. The Monte Carlo bootstraps **with**
replacement (`random.choices`), matching the 2nd-edition book (ch06.md:205). The
prompt above says "shuffle," but with-replacement resampling is what the chapter's
code and prose settle on. Permuting the same trades would collapse all 1,000
simulations to the identical final value. See deviation **#6** (resolved in book)
for the full story.

## Offline behaviour in this repo

Already offline by design: the backtester reads a local CSV and never calls a
model. The repo ships `fixtures/historical_flow.csv` (560 rows -> 487 that clear
the ch04 filters -> 423 with usable forward returns, calibrated to the 423-trade
report the chapter prints) and a deterministic price fixture that stands in for
yfinance.

## Cost notes

$0 of Anthropic spend. The data is the cost: UW Data Shop bundles ship with the
Advanced tier ($375/mo) or the $250/mo historical-options-trades add-on. There is
**no 180-day range query**: historical flow is one trading day per call via
`GET /api/option-trades/full-tape/{date}`, or a Data Shop download.

---

*Educational software. Not financial advice. Trading carries substantial risk of
loss. See [DISCLAIMER.md](../DISCLAIMER.md).*
