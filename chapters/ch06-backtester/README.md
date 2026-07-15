# Chapter 6 lab: the backtester

Sixteen trades and a 75% win rate feels like proof. It isn't; a random strategy could
produce exactly that over exactly that sample. This is the one lab where the point is
to watch the tool fail a strategy, not pass one: 1,000 Monte Carlo simulations, an
in/out-of-sample split, and a single verdict, with no LLM anywhere in it.

## The prompt
Paste [`prompts/05_backtester.md`](../../prompts/05_backtester.md), and
[`prompts/06_walk_forward.md`](../../prompts/06_walk_forward.md) for the add-on. You
get [`backtester/backtester.py`](../../backtester/backtester.py).

## Three strategies, three verdicts
```bash
make demo-ch06-no-edge          # -> NO EDGE
make demo-ch06-overfit          # -> OVERFIT
make demo-ch06-edge-candidate   # -> EDGE CONFIRMED
```
```
SCENARIO: edge_candidate  (expected verdict: EDGE CONFIRMED)
  ...
VERDICT: EDGE CONFIRMED
```
The no-edge and overfit scenarios print `NO EDGE` and `OVERFIT` respectively.

## Two things worth inspecting
The sampler is `random.choices`, a bootstrap with replacement. Permuting the same
trades (`random.sample`) would collapse all 1,000 runs to one number and the fan chart
to a flat line; the 2nd edition and this repo both avoid that
([#6](../../docs/book-deviations.md#6)). And an `EDGE CONFIRMED` on a synthetic fixture
is the mechanism working, not an edge existing. Ask which check produced each verdict:
the 5th percentile, the split, or the trade count.

---
Reference: [docs/04-backtester.md](../../docs/04-backtester.md)
