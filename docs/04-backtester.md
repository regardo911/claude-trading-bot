# 4. Backtester: the difference between gambling and trading (Chapter 6)

![Two-panel figure. Left: a Monte Carlo fan chart of 1,000 bootstrapped equity curves spreading from $100,000 to a 5th percentile of $106,786, a median of $109,037 and a 95th percentile of $111,197, with a green EDGE CONFIRMED stamp and a note that all 1,000 simulations produced distinct final values. Right: two small bar panels comparing in-sample and out-of-sample win rate (53.08% vs 52.83%) and Sharpe (5.28 vs 5.24), with overfit_flag False.](images/04-backtester.png)

*Computed by `backtester.py` on the bundled 423-trade synthetic fixture (regenerate with `python tools/generate_docs_charts.py`).*

## What it is

**The chapter that separates the people who make money from the people who think
they're going to.**

Sixteen trades and a 75% win rate feels like proof. It isn't: a *random* strategy
had a real chance of producing exactly those results over exactly that sample. You
need hundreds of trades across bull, bear, sideways, volatile and calm markets
before the signal separates from the noise.

This module gives you those hundreds of trades without risking a dollar, and then
shuffles them a thousand times to ask what *else* could have happened.

## It never calls Claude. On purpose.

> "This is an **offline deterministic backtester**; it never calls Claude or any
> other LLM. The reasoning happens in the Monte Carlo math, not in a model. Do NOT
> import or initialize `anthropic`." (ch06.md:64)

If you copy this pattern for another strategy, **resist the urge to add an Anthropic
client.**

## The sampler: bootstrap WITH replacement (resolved in the 2nd edition)

The current book samples **with** replacement, and so does this repo:

```python
shuffled = random.choices(returns, k=n_trades)   # ch06.md:205 — a BOOTSTRAP
```

That is the only sampler that produces the fan of outcomes the chapter's argument
requires. Sampling *without* replacement (`random.sample`) is a permutation; the
equity update reduces to `capital *= (1 + 0.02 * ret)`, a **product**; and a
product is invariant under permutation, so every simulation lands on the identical
final value and the fan chart is a flat line. Earlier printings had that bug. The
2nd edition and this repo both avoid it.

**See it yourself:**

```bash
python examples/04_backtest_verdict.py
```

```
423 trades from the synthetic fixture.

random.sample  (the naive permutation):  1 distinct final values out of 200 sims
random.choices (book + this repo):     200 distinct final values out of 200 sims
```

Full history and arithmetic (status: *resolved in book*):
[book-deviations.md #6](book-deviations.md#6).

**This page does not reprint the book's illustrative Monte Carlo figures.** Every
number here is what this code computed on this fixture.

## The rules

| Constant | Value |
|---|---|
| `CSV_PATH` | `backtester/historical_flow.csv` |
| `OVERFIT_GAP_PP` | `5.0` (in/out win-rate gap, in percentage points) |
| `OVERFIT_SHARPE_DROP` | `0.5` |
| Monte Carlo | `n_simulations=1000, initial_capital=100000, position_pct=0.02` |
| Forward horizon | `5` trading days (put sweeps flipped negative) |
| **Minimum trades** | **`30`** → below it, `INSUFFICIENT DATA` |
| Recommended floor | `100` (Appendix B), see [#2](book-deviations.md#2) |

**The four verdicts:**

| Verdict | Meaning |
|---|---|
| `EDGE CONFIRMED` | 5th percentile > starting capital **AND** the split passes. The only verdict that supports going live. |
| `OVERFIT` | The MC math looks fine, but performance collapsed out-of-sample. The parameters were fit to one regime. |
| `NO EDGE` | Consistent across halves, and consistently losing. |
| `INSUFFICIENT DATA` | Under 30 valid trades. **"Not enough data to validate" is not the same as "validated."** |

## How to run it

```bash
python backtester/backtester.py
```

With no CSV of your own, it falls back to the bundled synthetic fixture and says so.

## Worked example (offline, real output)

```
Loaded 487 filtered historical events.
Calculated returns for 423 valid trades.

Strategy Statistics:
  Total Trades: 423
  Win Rate: 53.0%
  Avg Winner: 3.77%
  Avg Loser: -2.06%
  Profit Factor: 1.83          (average win / average loss — the R Kelly needs)
  Sharpe Ratio: 5.26           (see the caveat below)

Overfitting Check:
  In Sample Win Rate: 53.1%    Out Of Sample Win Rate: 52.8%
  Win Rate Gap Pp: 0.3         Sharpe Drop: 0.04
  Overfit Flag: False

Walk-Forward Validation (3 windows, flag at >10pp):
  Window 2: train 56.0% -> test 49.6% | underperformance 6.4pp [ok]
  Window 3: train 52.8% -> test 53.2% | underperformance -0.4pp [ok]

Monte Carlo Results (1,000 simulations):
  Sampler: random.choices (bootstrap with replacement)
  5th Percentile:  $106,786 (+6.8%)
  Median:          $109,037 (+9.0%)
  95th Percentile: $111,197 (+11.2%)
  Unique Final Values: 1000
  Worst Max Drawdown: 1.0%

VERDICT: EDGE CONFIRMED
```

**There is no edge here. There is no real data here at all.** The fixture is
synthetic and calibrated to reproduce the chapter's own 423-trade report so the
`EDGE CONFIRMED` path is demonstrable.

## About that Sharpe of 5.26

`√252` annualizes *daily* returns. These are *per-trade* returns on a 5-day
horizon. **The annualization factor is wrong in kind**, and it inflates the number
by roughly 16x.

The repo **transcribes the formula exactly as the book prints it** and does not
silently re-annualize, because ch09's Kelly and ch10's go/no-go gate both consume
"Sharpe" from it. Read it as a relative score across runs of this repo, not as a
portable Sharpe. (The book's own printed 1.24 is not reachable from its own printed
stats either, [book-deviations.md #8](book-deviations.md#8).)

## Reading the fan chart

* **The median line** is your expected outcome if you're average-lucky. Use it for
  planning, not for expectations.
* **The 5th percentile is the number that matters.** It is what happens when the bad
  trades cluster. If it stays above your starting capital, the strategy makes money
  even in the worst 5% of orderings. **That is a real edge.**
* **The 95th percentile is useless for planning.** It's what happens when all your
  winners come first.
* If your live results fall **below the 5th percentile for more than two consecutive
  months**, something changed. Investigate.

## Overfitting: the four pictures

1. **Both halves agree** → `overfit_flag: False` + positive p5 → `EDGE CONFIRMED`.
2. **The halves disagree but the MC looks good** → `OVERFIT`. Disqualified, even
   though the full dataset averages over both regimes and looks fine.
3. **Both halves are weak** → `NO EDGE`. Not a regime problem. Just no edge.
4. **Under 30 trades** → `INSUFFICIENT DATA`. The fix is more data, not more tuning.

**The rule of thumb:** if removing a parameter drops your backtest by **less than 2
percentage points, remove it.** Fewer parameters means less room to fit noise. A
three-parameter version will underperform a seven-parameter version on historical
data every time, and outperform it on live data almost every time.

## Getting real historical data

**There is no 180-day range query.** Historical options flow comes from two places:

1. The **UW Data Shop**: downloadable CSV/zip bundles (Advanced tier $375/mo, or
   the $250/mo historical-options-trades add-on).
2. A one-time day-by-day loop over `GET /api/option-trades/full-tape/{date}` (**one
   trading day per call**), cached to disk.

Either lands as `backtester/historical_flow.csv`.

## The prompts

* [`prompts/05_backtester.md`](../prompts/05_backtester.md)
* [`prompts/06_walk_forward.md`](../prompts/06_walk_forward.md)

---

*Illustrative results on synthetic sample data. Not indicative of real or historical performance. Educational software. Not financial advice. See [DISCLAIMER.md](../DISCLAIMER.md).*
