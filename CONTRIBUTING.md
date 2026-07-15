# Contributing

Thanks for looking. Here's the deal.

## What this repo is

The **reference implementation** of *Use Claude to Build an AI Trading Bot*. Someone who
just finished the book should be able to open any file here and recognize it: same module
names, same function signatures, same constants, same commands.

That constraint is the whole point, and it drives everything below.

## Fixes: yes, please

* **Bugs** in the repo's own code.
* **Drift**: the book says X and the repo does Y, and it isn't in
  [`docs/book-deviations.md`](docs/book-deviations.md).
* **A new contradiction between the book and its own code.** This is the most
  valuable thing you can find. Sixteen are documented; there may be more. Open an issue
  with the chapter cite and the arithmetic.
* **API drift.** Alpaca, Unusual Whales, Polymarket and Kalshi all change. If an endpoint,
  a field name or an auth flow has moved, say so, with a link to the current docs.
* **Docs, typos, clearer explanations.** Always welcome.
* **More tests.** Especially around a deviation.

## New features: no

Not out of grumpiness. Out of purpose.

The book does not ship a mean-reversion bot (Appendix B describes one and never builds it),
so neither does this repo. It does not ship a reinforcement-learning position sizer, a Kafka
pipeline or a TimescaleDB backend, even though ch12 names all three as things to learn next.
**If this repo grows features the book doesn't have, it stops being a companion and starts
being someone else's trading system**, and the reader who came here from the book can no
longer trust that what they're reading is what they typed.

Build those things. Please. In your own repo.

## Three rules that are not negotiable

1. **The prediction analyzer never gets an order-submission path.** The book explicitly
   refuses to ship an unauthenticated trading bot for a CFTC-regulated venue (ch07.md:39,
   and "**Do NOT submit any orders**" in its own build prompt). A PR that adds one will be
   closed. A test enforces it.

2. **No flag and no environment variable may enable live trading.** Ever. Live mode is a
   code-level opt-in with a confirmation string, and it stays that way. An env var is one
   stray `export` away from trading someone's savings.

3. **No fabricated results.** Every number this repo prints must be **computed by this
   repo's code** on the committed synthetic fixtures. Never present the book's illustrative
   figures as this code's output. Never hand-draw a chart. A hand-drawn Monte Carlo fan
   would have hidden the worst bug in the manuscript. That rule is load-bearing, not
   cosmetic.

## Before you open a PR

```bash
pip install -e ".[dev]"
make lint          # ruff
make test          # the full suite, offline, green
```

Both must pass. CI runs them on Python 3.11, 3.12 and 3.13, **with core deps only**, which
is how the zero-key claim stays true instead of merely being asserted.

If you touched anything that produces a figure:

```bash
pip install -e ".[viz]"
make figures
```

…and then **actually open the PNGs and look at them.** Overlapping labels and clipped text
are defects.

## If you change behaviour the book describes

Add it to [`docs/book-deviations.md`](docs/book-deviations.md) with:

* the **chapter and line cite**,
* the **arithmetic** or the grep that proves it,
* what the repo does instead, and **why**,
* a **regression test** in `tests/test_book_deviations.py` that pins the decision.

That last one matters. The tests exist so that a future contributor who "helpfully" reverts
a deviation back to what the book printed gets a red build and an explanation, rather than
quietly reintroducing a capital-destroying bug.

## The fixtures

`fixtures/` is deterministic, seeded and synthetic. Nothing in it is real market data.

If you change a fixture, expect several tests to move: the worked-example assertions, the
watchlist counts, and the backtest verdict all read from it. That is intentional: the
fixtures are calibrated to reproduce the book's own printed report (487 filtered events →
423 valid trades, 53.7% / 1.79), because ch09's Kelly examples consume those exact numbers.

## Style

* Python 3.11+, type hints where they help, docstrings that say *why* rather than *what*.
* `ruff` is the arbiter. Line length 90.
* **Every artifact header cites its source chapter.** That is how a reader coming from the
  book finds their way around.

## Code of conduct

Be decent. Assume good faith. Nobody here is your enemy, least of all the author of a book
whose bugs we happen to be cataloguing, in a document that exists to make his book *more*
useful, not less.

---

*Educational software. Not financial advice. See [DISCLAIMER.md](DISCLAIMER.md).*
