# Where this repo differs from the book

This document is a **feature**, not an apology.

*Use Claude to Build an AI Trading Bot* is a build-along guide, and this
repository is the reference implementation its readers are promised. Where the
book's printed code contradicts the book's own prose, its own worked example, or
its own printed output, **something has to give**. Rather than quietly picking
one and hoping nobody notices, every one of those decisions is listed here, with
the chapter cite, the arithmetic, and the reasoning.

**The rule: where a printed snippet contradicts its own chapter's prose or worked
example, the worked example wins.** Implement the honest version. Log it.

If you just finished the book and something in this repo looks different from
what you typed, this page tells you exactly why. Every decision below is pinned
by a regression test in [`tests/test_book_deviations.py`](../tests/test_book_deviations.py),
so a future contributor who "fixes" one of them back gets a red build and an
explanation.

## Which book this repo tracks

> **Edition:** 2nd edition · **manuscript snapshot:** 2026-07-13
> · **content hash:** `596ace56…c584fed4`
> · machine-readable: [`deviation-manifest.json`](deviation-manifest.json)

**Books get revised. This list is pinned to a specific printing.** Each entry
below carries a **status** so you always know whether it describes *your* copy:

| status | meaning |
|---|---|
| **resolved in book** | The current book does the correct thing, and this repo matches it. Kept here as a historical note for anyone holding an earlier printing. |
| **still current** | The current book still carries this. The repo implements the honest version and says so. |
| **repo improvement** | The repo deliberately does something the book does not, for a stated reason. Not a book bug. |
| **not a bug** | Looks like one, is not. Do not "fix" it. |

**Two things the 2nd edition fixed**: the repo agreed with the book here even
before the edit, so nothing in the code changed; only this page's framing did.
See [#6](#6) and [#13](#13). They are no longer deviations. **The list below
still worth your time is the *still current* one.**

| # | What | Severity | Status |
|---|---|---|---|
| [12](#12) | Sector concentration ignores the proposed position | High | still current |
| [11](#11) | Rule 4 promises REDUCE; the code only BLOCKS | High | still current |
| [10](#10) | `evaluate_trade()` can't take a custom stop width | High | still current |
| [9](#9) | `suggested_bet` is a three-way contradiction | Medium | still current |
| [7](#7) | Profit factor: unformatted, and two formulas under one name | Medium | still current |
| [1](#1) | `MIN_VOLUME` is a dead constant | Medium | still current |
| [14](#14) | ch03's three rules exist in no code | Medium | still current |
| [4](#4) | Multi-agent JSON parsers can return `None`, unguarded | Medium | still current |
| [2](#2) | Minimum trades: 30 in code, 100 in Appendix B | Low | still current |
| [3](#3) | The "last 5 minutes" poll window is prose-only | Low | still current |
| [8](#8) | ch06's Sharpe of 1.24 is not reachable from its own stats | Low | repo improvement |
| [15](#15) | ch11 mis-cites bracket orders to "Chapter 9" | Low | still current |
| [16](#16) | Two prose-arithmetic errata with no code path | Low | still current |
| [6](#6) | Monte Carlo dispersion | ~~Critical~~ | **resolved in book** |
| [13](#13) | `check_exits()` short handling | ~~Critical~~ | **resolved in book** |
| [5](#5) | **NOT A BUG**: a trap you must not "fix" | — | not a bug |

---

<a name="6"></a>
## #6. Monte Carlo dispersion. **RESOLVED IN THE 2ND EDITION.**

> **Chapter 6** · `ch06.md:200-205, 611` · **Status: resolved in book, this repo already matched**

**The current book is correct here, and this repo agrees with it.** No code
changed when the book was revised; only this page's framing did. It stays on the
list as a historical note, because it is the most instructive bug in the
whole build and anyone holding an earlier printing should understand it.

### What the current book does (and this repo does too)

```python
shuffled = random.choices(returns, k=n_trades)   # ch06.md:205 — bootstrap WITH replacement
```

The chapter now spells out *why* in prose (ch06.md:611): resample **with**
replacement, never permute.

### The subtle bug earlier printings had

Earlier drafts sampled **without** replacement:

```python
shuffled = random.sample(returns, n_trades)      # the old, wrong sampler
```

`random.sample` is a **permutation**. And the equity update is:

```python
position_size = capital * position_pct           # ch06.md:209-211
pnl = position_size * ret
capital += pnl
```

which reduces to `capital *= (1 + 0.02 * ret)`. Final capital is therefore

    initial × Π(1 + 0.02·rᵢ)

over the *same* set of returns in every simulation. **A product is invariant
under permutation.** Every one of the 1,000 simulations ends at the *identical*
final value: min final = max final, spread 5e-10, float noise. Five identical
percentiles, a fan chart with no fan, and an `EDGE CONFIRMED` gate that never
tested anything. It looked completely reasonable while reporting a spread of
exactly zero. That is what makes it worth keeping on this page.

### What this repo does

```python
resampled = rng.choices(returns, k=n_trades)     # bootstrap WITH replacement
```

Same as the 2nd edition. **This repo prints what its own code computes on its own
synthetic fixture**. It does not reprint any illustrative report from the book. A
test (`test_book_figures_never_appear_as_our_output`) enforces that no stale
illustrative figures leak into the repo's output, and the regression test below
guards the sampler itself:

```python
def test_produces_more_than_one_unique_final_value(self):
    mc = bt.monte_carlo_simulation(self._trades(), n_simulations=200)
    assert len({round(v, 6) for v in mc["final_values"]}) > 1
```

A second test *proves the bug still exists* under `random.sample`, so the guard is
not cargo cult.

### A related note on magnitude

At 2% position sizing, the mean per-trade return
`0.537 × 3.82% + 0.463 × (−2.14%) = 1.0605%` compounds over 423 trades to roughly
**+9.4%**, which is what both the current book (ch06.md:566-574) and this repo
now report. (Some earlier printings quoted a ~+27.6% median, which never followed
from the stated stats.) `max_drawdown` is genuinely path-dependent, so it is the
one Monte Carlo statistic a resample legitimately moves.

---

<a name="13"></a>
## #13. `check_exits()` short handling. **RESOLVED IN THE 2ND EDITION.**

> **Chapter 5** · `ch05.md:500-550` · **Status: resolved in book, this repo already matched**

**The current book covers shorts correctly, and this repo agrees with it.** As
with #6, no code changed when the book was revised; only this framing did.

### What the current book does (and this repo does too)

`execute_trade()` opens shorts (`SELL_SHORT` → `OrderSide.SELL`, ch05.md:277-283).
Reducing a short therefore means **buying it back**, and the 2nd edition does
exactly that (ch05.md:530-531):

```python
side = OrderSide.BUY if is_short else OrderSide.SELL   # cover a short; sell a long
```

The current book also implements the two things earlier printings only promised in
prose: it **moves the stop to breakeven** after scaling out (ch05.md:507-538,
tracked in an `exit_state` dict) and it **closes on a 5-day time limit**
(ch05.md:544-550).

### The capital-destroying bug earlier printings had

Earlier drafts submitted the profit-target order **unconditionally**:

```python
order = MarketOrderRequest(
    symbol=pos.symbol, qty=half,
    side=OrderSide.SELL, time_in_force=TimeInForce.DAY)   # the old, wrong branch
```

On a *short* position at +6% P&L, `OrderSide.SELL` **adds to the short** instead of
covering half of it. The bot thinks it is taking profit; it is doubling down. This
is the one deviation on the whole list that would have shipped **real losses**, so
it stays here as a warning even though the book now gets it right. (The stop-loss
branch was always safe: `alpaca.close_position()` is side-agnostic.)

### This repo's implementation notes

`flow_trader/exit_state.json` persists the breakeven state across restarts. A
breakeven stop that resets on every restart is not a stop. Positions the bot did
not open have unknown age and are exempt from the time limit; the repo will not
close a position whose age it cannot establish.

---

<a name="12"></a>
## #12. Sector concentration ignores the position you are about to open

> **Chapter 9** · `ch09.md:232-236` · **CONFIRMED**

`check_sector_concentration()` sums only *existing* positions:

```python
for pos in portfolio["positions"]:
    if self._get_sector(pos["symbol"]) == sector:
        sector_value += pos["market_value"]
concentration = sector_value / total_value
```

The trade being evaluated is never added.

**Why this matters:** the module's own worked example sizes a **$66,600** NVDA
position on a **$100K** account (ch09.md:413). That is 66.6% of the portfolio in a
single tech name. With an empty portfolio, `concentration = 0` → **APPROVED**. The
40% sector cap is only ever enforced against the *next* trade, after the cap has
already been blown through.

Rule 4's own scenario passes too: already 35% tech → 0.35 < 0.40 → approved at
full size, which is exactly the trade Rule 4 exists to stop.

**The chapter contradicts itself 270 lines later.** Its standalone
`check_correlation()` helper (ch09.md:519-524) starts from
`sector_total = proposed_value`. It *does* include the proposed trade.

**This repo:** `sector_total = proposed_value + existing`. Matching the chapter's
own guard.

Run `python risk/risk_manager.py` to see the consequence: Rule 1 sizes NVDA at 72
shares (the book's number, exactly), and then the gatekeeper cuts it to 43 because
72 shares is 66.6% concentration.

---

<a name="11"></a>
## #11. Rule 4 promises REDUCE. The code only ever BLOCKS.

> **Chapter 9** · `ch09.md:23, 246-252` · **CONFIRMED**

The prose:

> "If you're already 35% in tech and the Analyst recommends another tech stock, the
> Risk Manager **reduces the position to fit within the 40% cap, or rejects it
> entirely**." (ch09.md:23)

The code computes `remaining_capacity`, returns it as a **formatted string**
(`f"${remaining_capacity:,.0f}"`), and then `evaluate_trade()` **never reads it**.
Its only sector branch is a hard block. The reduce path does not exist, and the
value that would have implemented it is not even usable as a number without
re-parsing it.

**This repo:**
* `remaining_capacity` is a **float**.
* When the Kelly/2% size exceeds it, `shares` is capped at
  `int(remaining_capacity / entry_price)`.
* A **`REDUCED`** verdict joins `APPROVED` / `BLOCKED` / `REJECTED-NO-EDGE`.
* It only BLOCKS when nothing at all fits.

This is transcription of intent, not invention: ch08's Risk *agent* already has a
first-class `REDUCE` action with `approved_shares`, and its Executor honors it.
REDUCE is the book's own idiom.

---

<a name="10"></a>
## #10. The chapter's own TSLA advice is unreachable through its own gatekeeper

> **Chapter 9** · `ch09.md:301-302, 360-361` · **CONFIRMED**

```python
def evaluate_trade(self, ticker, entry_price, direction="BUY",
                   win_rate=0.537, profit_factor=1.79):     # no stop_loss_pct
```

`calculate_position_size()` *does* accept `stop_loss_pct`. `evaluate_trade()` does
not, and never forwards one, so `sl = stop_loss_pct or DEFAULT_STOP_LOSS` is
**always 3%**.

Meanwhile the chapter says, in bold:

> "The risk module in the code above lets you pass a custom `stop_loss_pct` per
> trade. **Use it.** Don't apply the same stop width to NVDA and TSLA."
> (ch09.md:419)

But `evaluate_trade()` is the documented gatekeeper every bot must call ("Before
any trade gets placed, it passes through `evaluate_trade()`", ch09.md:423), and
the integration snippet the book tells you to paste calls
`rm.evaluate_trade(ticker, entry_price)`. **The reader cannot reach the TSLA 5%
stop through the path the book sanctions.**

Second-order: `checks["stop_loss"]` and `checks["max_loss"]` hard-code
`DEFAULT_STOP_LOSS`, so even a plumbed-through custom stop would be **misreported**
in the verdict dict.

**This repo:** `evaluate_trade(..., stop_loss_pct=None, ...)`, forwarded to
`calculate_position_size()` and threaded through both `checks` fields.

The ch09 **arithmetic is all correct**: NVDA $925/3% → 72 shares; F $12/3% →
5,555 shares; TSLA $240/5% → 166 shares; Kelly 0.278 → quarter-Kelly 6.95%. Every
one reproduces exactly, and every one is asserted in
[`tests/test_worked_examples.py`](../tests/test_worked_examples.py). Only the
plumbing to reach the TSLA row was missing.

---

<a name="9"></a>
## #9. `suggested_bet`: the code, the prose, and the two examples all disagree

> **Chapter 7** · `ch07.md:303-304, 581` · **CONFIRMED**

Three claimants, mutually irreconcilable:

* **The code:** `min(MAX_BET_SIZE, MAX_BET_SIZE * abs(gap))`
* **The prose** (ch07.md:581): "A 20% gap gets the full $50. A 10% gap gets $25."
  A *different* formula: `min(50, 50 · gap/0.20)`
* **The two printed examples:** $24.50 at a 49% gap; $50.00 at a 17% gap.

| gap | the code gives | the prose ladder gives | the book prints |
|---|---|---|---|
| 10% (the `MIN_PROBABILITY_GAP` floor) | **$5.00** | $25.00 | — |
| 17% (ch07.md:443-449) | **$8.50** | $42.50 | **$50.00** |
| 20% | **$10.00** | $50.00 | — |
| 49% (ch07.md:387-395) | **$24.50** | $50.00 | **$24.50** |

Read that table carefully. The +49% example matches the **code** digit-for-digit
($24.50 = 50 × 0.49). The +17% example matches **neither**. **No single formula
produces both printed examples**: a bet that *falls* from $50 at a 17% gap to
$24.50 at a 49% gap is not a function of gap size. "Worked example wins" cannot
resolve this, so the tiebreak has to be principled.

**This repo ships the code as printed.** Three reasons:

1. It is the only formula any printed output reproduces exactly, and that output
   (ch07.md:395) is printed as the output of the very function that contains the
   formula.
2. The $50.00 at ch07.md:449 appears under the *interactive* path, whose printed
   code (`rank_estimates_file`) **does not compute `suggested_bet` at all**. It
   returns `{**est, **ev}`. That line is untraceable to any code the book prints.
3. In a finance repo, the smaller-risk branch wins ties.

### The erratum you need to know

Under this formula, `min()` binds **only at a 100% gap**. So `MAX_BET_SIZE` is a
**scaling coefficient, not a cap**, which contradicts both its own inline comment
("$50 max per contract") and the word "cap" in the prose. A qualifying 10% gap
sizes a **$5** bet. A realistically large 49% gap sizes **$24.50**. The $50 the
prose promises is unreachable in practice.

If you want the prose ladder instead, it is
`min(MAX_BET_SIZE, MAX_BET_SIZE * abs(gap) / 0.20)`, and note that it reproduces
*neither* printed example.

---

<a name="7"></a>
## #7. Profit factor: unformatted, and two different formulas under one name

> **Chapters 6 & 10** · `ch06.md:343-344`, `ch10.md:54`, `appendices.md:677` · **CONFIRMED**

**The small half.** `profit_factor` is the only entry in `strategy_stats` that is
not f-string formatted. Every sibling is (`f"{win_rate:.1%}"`, `f"{sharpe:.2f}"`).
`abs(0.0382 / −0.0214)` = `1.7850467289719627`, and that is what the printed code
prints. The report shows `1.79`. Fixed with `.2f`.

**The substantive half.** The book defines profit factor **twice**:

* **ch06** (the backtester, and what ch09's Kelly consumes): *average* win /
  *average* loss → **1.79** on the book's numbers.
* **ch10** (the Phase-1 go/no-go gate) and **Appendix D**: *sum* of winning profits
  / *sum* of losing losses → **2.07** on the same numbers.

And ch10 applies a **> 1.5 go/no-go gate** to it. Which one?

**This repo keeps both, under different names.**

* The backtester keeps the **avg-based** one, because ch09's Kelly formula needs
  `R = avg win / avg loss`. Swapping in the sum-based value silently breaks the
  chapter's own printed Kelly example: `0.537 − 0.463/2.07 = 0.313`, not the
  printed `0.278`.
* `tracking/calculate_metrics.py` implements the **sum-based** metric under the
  distinct name **`gross_profit_factor`**.

**Never let one name carry two formulas.** A test asserts that a bare
`profit_factor` key does not exist in the tracking metrics.

**One honest limitation:** the `daily_metrics.json` schema the book specifies
carries only *daily* P&L, not per-trade P&L. So the tracking module's profit
factors are computed over **days**, not trades. The trade-level `R` that Kelly
needs comes from the backtester's `report.json`.

---

<a name="1"></a>
## #1. `MIN_VOLUME` is declared and then never used

> **Chapter 7** · `ch07.md:88` · **CONFIRMED by grep**

```python
MIN_VOLUME = 10000  # Minimum market volume
```

It is **never referenced** anywhere in `prediction_analyzer.py`: not in
`get_active_markets()`, not in `filter_analyzable()`, and not in the opportunity
gate, which checks only `side != SKIP`, `abs(gap) >= MIN_PROBABILITY_GAP` and
`confidence in [HIGH, MEDIUM]`.

Appendix B lists it as a **live tunable**: "`MIN_VOLUME = 10000` (minimum market
volume for liquidity)" (appendices.md:470), implying it filters. And
`research/polymarket-gamma-truth.md` even specifies the fix
("Filter `MIN_VOLUME` comparison needs `float(contract.get("volume", 0))`"), a
migration step that evidently never got applied.

**This repo implements the filter.** Without it, the analyzer happily scores
$0-volume markets you could never get filled in. The bundled Gamma fixture
contains two of them so you can watch the filter drop them.

`volume` arrives as a **stringified float**, so the cast is load-bearing.

---

<a name="14"></a>
## #14. Chapter 3's three rules exist in no code anywhere in the book

> **Chapter 3** · `ch03.md:87, 111, 147` · **CONFIRMED by grep across ch04/05/07/08/09**

Chapter 3 is the analysis *contract* the later chapters consume. It states three
rules as already running:

* "**My bot now includes** a 'geopolitical filter' that **reduces confidence by 15
  points** for any Chinese ADR…" (ch03.md:111)
* "I added a manual rule: if Tier 1 and Tier 2 signals conflict in opposite
  directions, **reduce overall confidence by 20 points** and flag for manual
  review." (ch03.md:147)
* "I don't let my bots trade anything with **average daily volume below 1 million
  shares**, and you shouldn't either." (ch03.md:87)

**None of the three appears in any printed script.** No chapter's code ever adjusts
a Claude-returned confidence score after the fact, and no chapter filters on
average daily volume.

**This repo implements all three**, in [`utils/signals.py`](../utils/signals.py),
**default-ON**, wired into both the screener and the flow trader. All three push
the bot toward *fewer* trades, the conservative direction.

Three implementation notes, so you know exactly what you're getting:

1. **The liquidity floor** uses yfinance volume, the same argument ch09 makes for
   sector and earnings: it is a public data field, not a judgment call. An
   *unknown* ADV is a pass-with-a-warning, not a silent block; refusing every
   ticker yfinance has never heard of would disable the bot rather than protect it.
2. **The geopolitical filter** needs a list, and ch03 defines the *category*
   ("any Chinese ADR, any Russian-exposed company, any company with more than 40%
   revenue from a single foreign government's jurisdiction") without printing one.
   There is no free API that answers "is this a Chinese ADR", so the repo ships an
   explicit, editable, **obviously incomplete** roster (`GEOPOLITICAL_TICKERS`)
   rather than fabricating a data source. Edit it for your own universe.
3. **The Tier1/Tier2 conflict rule** needs a Tier-2 (dark pool) read. ch04's and
   ch05's prompts already *ask* Claude about dark-pool context; they just throw
   the answer away. This repo adds one optional field to the analysis schema,
   `dark_pool_read` (`BULLISH` / `BEARISH` / `UNKNOWN`), and applies the −20 only
   on a clean opposite-direction call. **An absent or `UNKNOWN` value costs
   nothing**, so a response in the book's exact printed schema still works.

This is the only deviation in this document that adds a field to a schema the book
prints. It is additive, optional, and degrades to the book's behaviour.

---

<a name="4"></a>
## #4. The multi-agent orchestrator crashes on an unparseable agent response

> **Chapter 8** · `ch08.md:225-233, 292-299, 449-457, 476, 493` · **CONFIRMED**

Each of the four agents' `except json.JSONDecodeError` branches returns a parsed
value **only if** the response contains a code fence. Otherwise it falls through
and returns `None`.

`run_multi_agent_cycle()` then calls `health.get(...)` and `analysis.get(...)`
with no `None` check.

ch04, ch05 and ch07 **all** guard this (`if not analysis: continue`). ch08 does
not. The chapter's own TROUBLESHOOT block anticipates a `JSONDecodeError`
(ch08.md:707) but not the `AttributeError: 'NoneType' object has no attribute
'get'` that this path actually raises.

**This repo adds the guard**, matching the book's own established idiom. If the
Risk Manager cannot speak, nothing trades, which is the correct failure mode for
an agent whose entire job is to say no.

---

<a name="2"></a>
## #2. Minimum trades: 30 in the code, 100 in Appendix B

> **Chapter 6 / Appendix B** · `ch06.md:253`, `appendices.md:501`

The code gates at 30 (`if len(trades) < 30:` → `INSUFFICIENT DATA`), and the BUILD
STEP repeats "fewer than 30 valid trades" three separate times. Appendix B's
parameter cheat sheet says "**Minimum trades: 100**".

**Worked example wins → 30 is the hard gate.** Appendix B's 100 reads as an
editorial guideline ("don't trust a backtest under 100 trades") rather than a
constant.

This repo ships 30 as `MIN_TRADES` and 100 as `RECOMMENDED_MIN_TRADES`, and the
backtester prints a note when your trade count falls between the two.

---

<a name="3"></a>
## #3. The "last 5 minutes" poll window is prose-only

> **Chapter 5** · `ch05.md:43, 127-132`

The prose says the bot polls "asking for events from the last 5 minutes." The
printed `get_live_flow()` passes `min_premium`, `min_volume_oi_ratio`, `max_dte`
and `is_sweep`, and **no time-window param at all**. Freshness comes from the
`seen_events` dedup set downstream instead.

The behaviour is *correct but not as described*: dedup achieves the same net
effect, at the cost of re-pulling and re-filtering the whole window every poll.

`research/uw-api-truth.md` documents the real param: **`newer_than`** (Unix ms,
"for polling — use last seen `created_at`").

**This repo adds `newer_than`**, which is both what the prose describes and what
the API actually supports.

---

<a name="8"></a>
## #8. ch06's Sharpe of 1.24 is not reachable from its own printed stats

> **Chapter 6** · `ch06.md:237-240, 548` · **PLAUSIBLE, not proven**

`np.mean(excess) / np.std(excess) * np.sqrt(252)` applied to *per-trade* 5-day
returns.

The printed stats fix the mean per-trade return at 1.0605%. Printing
`Sharpe Ratio: 1.24` therefore requires a per-trade standard deviation of
**13.32%**, implausible for 5-day equity returns whose average winner is +3.82%
and average loser is −2.14%. A two-point-mass reconstruction of that distribution
gives σ = 2.97% → Sharpe **5.56**.

This cannot be *proven* impossible (σ is not fully determined by a win rate plus
two averages), so it is flagged, not resolved.

**A separate method note the repo owes you:** `√252` annualizes *daily* returns.
These are *per-trade* returns on a 5-day horizon over a six-month window. **The
annualization factor is wrong in kind**, regardless of the σ question.

**This repo transcribes the formula exactly as printed** and does not silently
re-annualize. It is the book's stated convention, and ch09's Kelly and ch10's
go/no-go gate both consume "Sharpe" from it; quietly changing it here would break
their worked examples instead of fixing anything.

Read the Sharpe this repo prints as a **relative score across runs of this repo**,
not as a portable Sharpe ratio. On the bundled fixture it prints around 5.3, which
is the honest consequence of the formula as written.

---

<a name="15"></a>
## #15. ch11 mis-cites bracket orders to "Chapter 9"

> **Chapter 11** · `ch11.md:133` · **CONFIRMED. No code impact.**

> "If your stop-losses are set as **bracket orders (Chapter 9)**, they'll execute at
> the exchange level without your API."

Bracket orders live in **ch08**'s Executor (`OrderClass.BRACKET`, ch08.md:380-388).
ch09's `risk_manager.py` contains no bracket order: its only broker-side
protective order is a `TrailingStopOrderRequest`, and ch05 explicitly says its stop
is "a *soft stop in code*, not a hard stop order placed with the broker."

**This repo's docs cite ch08 for brackets.** Logged for a future edition.

---

<a name="16"></a>
## #16. Two prose-arithmetic errata with no code path

> **Report-only. The repo deliberately computes neither.**

**The coin-flip claim is wrong by about 5x.** "If you flip a fair coin 16 times,
there's a **21% chance** you'll get **12 or more** heads." (ch06.md:17)
Binomial(16, 0.5): P(X ≥ 12) = 2517/65536 = **3.84%**. (21% is approximately
P(X ≥ **10**) = 22.7%.)

The *rhetorical* point (16 trades is far too small a sample to conclude anything)
survives completely. The number does not.

**This repo ships no demo that computes it.** A `binom.sf` one-liner would print
3.8% right next to the book's 21%, which helps nobody. A test asserts that no
module in this repo imports a binomial.

**ch10's $50K projection doesn't follow from its own band.** "expect $200-$500 per
month… on $10K capital (**2-5% monthly**)… at $50K, **those same percentages**
produce **$1,000-$1,600 per month**" (ch10.md:194). 2-5% of $50K is
**$1,000-$2,500**. The lower bound is right; the upper bound is not derivable.

Everything else checked reconciles: ch12's compounding, ch12's business math,
ch11's slippage percentages, ch11's "6% loss on a 2%-risk position costs 4% of
account" (correct), every ch09 position-size figure, and ch02's UW $50/wk ≈
$215/mo.

---

<a name="5"></a>
## #5. NOT A BUG. A trap you must not "fix".

> **Chapters 5 & 9** · `ch05.md:110`, `ch09.md:121`

```python
MAX_POSITION_PCT   = 0.02     # ch05 — 2% of account, as NOTIONAL
MAX_RISK_PER_TRADE = 0.02     # ch09 — 2% of account, as RISK
```

Same number. **Completely different quantities.**

* ch05's 2% is **notional**: "With a $100K paper account, that's $2,000 **per
  position**" (ch05.md:422).
* ch09's 2% is **risk**: position × stop-loss width. On a $100K account at a 3%
  stop, that supports a **$66,600** position (ch09.md:17).

A thirty-three-fold difference, from the same numeral.

The book **reconciles them deliberately**: "Chapter 9 replaces this with Kelly
Criterion for optimal sizing" (ch05.md:422), and the risk module is "a gatekeeper
that sits between every bot's decision and Alpaca's order API" (ch09.md:423).

**This repo ships both, unchanged, and lets `risk_manager.evaluate_trade()` be the
override, exactly as ch09.md:427-442 shows.** A test pins both constants and
asserts the thirty-three-fold gap, so nobody "helpfully" unifies them.

---

## A note on the synthetic fixture

`fixtures/historical_flow.csv` is calibrated to the **423-trade report** the
chapter prints (ch06.md:532-534), not to the "all 2,800 trades" its narrative
mentions (ch06.md:51). The 423-trade report is the one ch09's Kelly examples
consume (53.7% / 1.79), so it is the one the repo has to reproduce.

The fixture is **stratified**: the chronological first half and second half are
drawn from the same distribution. Without that, the in/out-of-sample split flags
`overfit=True` on pure sampling noise and the fixture never demonstrates the
`EDGE CONFIRMED` path at all. The fixture is *meant* to be a strategy whose edge
generalizes, which is exactly what the chapter's own worked example is. The
`OVERFIT`, `NO EDGE` and `INSUFFICIENT DATA` verdicts are covered by unit tests
instead.

**This is a property of the fixture, not evidence of an edge.** There is no edge
here. There is no real data here at all.

---

*Educational software. Not financial advice. See [DISCLAIMER.md](../DISCLAIMER.md).*
