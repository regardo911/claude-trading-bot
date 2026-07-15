# Errata & reconciliation

The printed book is a fixed snapshot; this repository is live and maintained. When the two
disagree, **this file is the tie-breaker.** It has two parts: **corrections**, where the book
is simply wrong, and **reconciliation**, where the repo has moved past the pages and you just
need the two lined up.

Every correction below links to [`docs/book-deviations.md`](docs/book-deviations.md) for the
full arithmetic and chapter cites (machine-readable status:
[`docs/deviation-manifest.json`](docs/deviation-manifest.json)). Repo code changes are logged
in [`CHANGELOG.md`](CHANGELOG.md).

---

## Corrections (the printed book is wrong)

### If your Chapter 6 backtester prints identical percentiles / a flat fan chart

Your printing uses `random.sample()` in the Monte Carlo loop:

```python
shuffled = random.sample(returns, n_trades)   # a permutation
```

`random.sample` reorders the *same* trades, and the equity update is a product, so **every one
of the 1,000 simulations lands on the identical final value**: five identical percentiles and
a fan chart with no fan. Resample **with** replacement instead:

```python
shuffled = random.choices(returns, k=n_trades)   # a bootstrap
```

The corrected manuscript already does this, and so does
[`backtester/backtester.py`](backtester/backtester.py). Detail:
[book-deviations.md #6](docs/book-deviations.md#6).

### If your Chapter 5 `check_exits()` "takes profit" on a short by selling

Reducing a **short** means *buying it back*. The printed profit-target branch submits
`OrderSide.SELL` unconditionally: on a short at +6% P&L that **adds to the short** instead of
covering it. The fix:

```python
side = OrderSide.BUY if is_short else OrderSide.SELL   # cover a short; sell a long
```

The corrected manuscript covers shorts and adds the breakeven-stop move and 5-day time limit;
[`flow_trader/flow_trader.py`](flow_trader/flow_trader.py) matches. Detail:
[book-deviations.md #13](docs/book-deviations.md#13).

> The two corrections above were fixed in the manuscript source but may not yet be in the
> printing you hold. They are listed here so a reader on any printing can make the code work.

### Chapter 6: "a 21% chance of 12 or more heads in 16 flips" is 3.84%

The rhetorical point (16 trades is far too small a sample to conclude anything) is exactly
right. The number is not: for a fair coin, P(X ≥ 12 in 16) = 2517/65536 = **3.84%**. (21% is
about P(X ≥ 10).) [book-deviations.md #16](docs/book-deviations.md#16).

### Chapter 9: the risk module has three gaps its own prose contradicts

- **The sector cap ignores the trade you're about to open.** `check_sector_concentration()`
  sums only *existing* positions, so the chapter's own worked example approves a **$66,600
  NVDA position on a $100K account** (66.6% in one name) against a 40% cap. Count the proposed
  trade too. [#12](docs/book-deviations.md#12)
- **Rule 4 promises to *reduce* an oversized position; the code only *blocks*.**
  `remaining_capacity` is computed, returned as a formatted string, and never read. The repo
  ships a `REDUCED` verdict. [#11](docs/book-deviations.md#11)
- **`evaluate_trade()` takes no `stop_loss_pct`,** so the chapter's own "widen TSLA to a 5%
  stop. **Use it.**" advice is unreachable through the gatekeeper every bot is told to call.
  [#10](docs/book-deviations.md#10)

### Chapter 7: `suggested_bet` disagrees with itself three ways

The code (`min(MAX_BET_SIZE, MAX_BET_SIZE * abs(gap))`), the prose ("a 20% gap gets the full
$50"), and the two printed examples ($24.50 at a 49% gap; $50.00 at a 17% gap) are mutually
irreconcilable: **no single formula produces both examples.** The repo ships the code as
printed, with the erratum stated: `MAX_BET_SIZE` is a scaling coefficient, not a cap.
[#9](docs/book-deviations.md#9)

### Chapter 7: `MIN_VOLUME` is declared and never used

`MIN_VOLUME = 10000` is presented as a liquidity filter (and Appendix B lists it as a live
tunable) but is referenced nowhere. Without it the analyzer scores $0-volume markets you could
never fill. The repo implements the filter. [#1](docs/book-deviations.md#1)

### Chapter 3: the three "my bot now includes" rules exist in no code

The 1M-share liquidity floor, the −15 geopolitical penalty, and the −20 Tier1/Tier2 conflict
penalty are stated as already running, but appear in **no printed script anywhere in the
book.** The repo implements all three in
[`utils/signals.py`](utils/signals.py), default-ON. [#14](docs/book-deviations.md#14)

### Smaller ones

- **Ch 11** cites bracket orders to "Chapter 9"; they live in **Chapter 8**'s Executor.
  [#15](docs/book-deviations.md#15)
- **Ch 10**: "$50K at 2–5% → $1,000–$1,600/mo": 2–5% of $50K is **$1,000–$2,500**; the upper
  bound is off. [#16](docs/book-deviations.md#16)
- **Ch 8**: the multi-agent orchestrator crashes on an unparseable agent response (the other
  chapters guard it; ch08 doesn't). The repo adds the guard. [#4](docs/book-deviations.md#4)
- **Ch 6**: `profit_factor` prints unformatted, and the book uses two different definitions of
  it under one name (avg-based in ch06, sum-based in ch10). The repo keeps both, distinctly
  named. [#7](docs/book-deviations.md#7)
- **Ch 6 / App B**: minimum-trades gate is 30 in code, 100 in Appendix B. 30 is the hard gate.
  [#2](docs/book-deviations.md#2)

---

## Reconciling the book with the current repo

### Everything runs offline, against synthetic fixtures

The book's code hits paid, keyed APIs (Anthropic, Unusual Whales, Alpaca, Kalshi). This repo
serves deterministic synthetic fixtures by default, so `make demo` and every command run with
no keys and no network. Every printed number here is illustrative and predicts nothing.

### The backtester takes a scenario; the book shows one run

The book's ch06 walkthrough shows a single `EDGE CONFIRMED` run. This repo also ships three
diagnostic scenarios so you can watch the tool *fail* a strategy, which is the actual skill:

```bash
make demo-ch06-no-edge      make demo-ch06-overfit      make demo-ch06-edge-candidate
```

### The flow trader and multi-agent bots run one cycle by default

The book runs the flow trader "for one cycle." So does a bare `python flow_trader/flow_trader.py`;
add `--loop` for the real polling loop.

### Not a bug: do not "fix" it

Chapter 5's `MAX_POSITION_PCT` (2% **notional**) and Chapter 9's `MAX_RISK_PER_TRADE` (2%
**risk**) are different quantities that share a numeral: a 33× difference. The book reconciles
them deliberately; the risk gatekeeper is the override. Both ship, un-unified.
[#5](docs/book-deviations.md#5)

---

*Educational software. Not financial advice. See [DISCLAIMER.md](DISCLAIMER.md).*
