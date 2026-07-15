# 8. Going live: your first 90 days (Chapter 10)

![Phased timeline over 90 days. A synthetic equity curve runs through Phase 1 (days 1-30, paper, $100K virtual) and stops there; Phases 2 and 3 are shaded but empty. Dashed vertical lines mark the Day-30 and Day-60 gates. A green box reads "DAY-30 GATE / GO". Below the equity curve, a drawdown panel shows the account never approaching the 15% max-drawdown gate. The five Phase-1 criteria are listed with their values, all GO.](images/08-going-live.png)

*Computed by running `tracking/phase1_assessment.py` against the bundled synthetic GO fixture (regenerate with `python tools/generate_docs_charts.py`).*

## What it is

Not a vague "trade for a while then go live." **Specific numbers. Specific criteria.
Specific go/no-go decisions.**

The author paper-traded for **47 days** before risking a single real dollar. Because he
waited, he caught two problems that would have cost real money: a persistent
semiconductor bias that looked like skill and was actually a three-week bull run in
semis, and a backtest that assumed instant fills and overstated real performance by
~1.2% per trade.

**Both were only findable with 47 days of data to analyze.**

## The three phases

| Phase | Days | Capital | What you're learning |
|---|---|---|---|
| **1** | 1-30 | paper, $100K virtual | does the strategy work at all? |
| **2** | 31-60 | **live, $500** | slippage, latency, and your own stomach |
| **3** | 61-90 | $2K → $5K → $10K | does it hold up as size grows? |

## Set up on Day 1, not Day 30

Two things will save you a week:

1. **Start Alpaca live-account identity verification on Day 1.** It takes 1-3 business
   days, plus a separate funding step. Waiting until Day 30 adds a week between your GO
   decision and your first live trade.
2. **Set up the tracking infrastructure on Day 1**: you need 30 days of it.

## The Phase-1 gate (Day 30)

| Metric | **Go** | **No-Go** |
|---|---|---|
| Win rate | > 50% (or > 45% with PF > 1.5) | < 45% |
| Sharpe ratio | > 1.0 | < 0.8 |
| Max drawdown | < 15% | > 20% |
| Profit factor | > 1.5 | < 1.2 |
| Profitable weeks | 3 of 4+ | 1 of 4 |

**If ALL metrics hit Go → Phase 2. If ANY metric hits No-Go → stop and fix it.** If
they fall between → extend Phase 1 by two weeks and recheck.

## How to run it

```bash
python tracking/calculate_metrics.py
python tracking/phase1_assessment.py                         # the bundled GO fixture
python tracking/phase1_assessment.py daily_metrics_hold.json # a HOLD
python tracking/phase1_assessment.py daily_metrics_empty.json # the no-data case
```

`daily_metrics.json` schema, one row per night:

```json
{"date": "2026-04-01", "trades_taken": 3, "trades_blocked_by_risk": 1,
 "wins": 2, "losses": 1, "daily_pnl_dollar": 41.20, "daily_pnl_pct": 0.41,
 "max_drawdown_pct": 1.2, "portfolio_value_close": 10041.20}
```

## Worked example (offline, real output)

```
=== PHASE 1 GO/NO-GO ASSESSMENT (Day 30) ===

  Metric                Value       State
  ----------------------------------------
  Win rate              56.2%       GO
  Sharpe ratio          3.10        GO
  Max drawdown          3.9%        GO
  Gross profit factor   1.60        GO
  Profitable weeks      5 of 7      GO

VERDICT: GO
```

And on an empty file, the case the book's own prompt asks you to test:

```
VERDICT: NO DATA

No trading days logged yet. There is nothing to assess.
A verdict on zero data is not a verdict.
```

## Two profit factors, two names

The book defines profit factor **twice**: *average* win / *average* loss in ch06
(**1.79** on its numbers), and *sum* of wins / *sum* of losses in ch10 and Appendix D
(**2.07** on the same numbers), and then applies a **> 1.5 gate** to it.

This module implements ch10's sum-based definition under the distinct name
**`gross_profit_factor`**. **Never let one name carry two formulas.**
([book-deviations.md #7](book-deviations.md#7))

**One honest limitation:** the schema carries only *daily* P&L, not per-trade P&L, so
both profit factors here are computed over **days**. The trade-level `R` that Kelly
needs comes from the backtester's `report.json`.

## Phase 2: $500. Not $5,000.

Switching to live is mechanically one line:

```
# Paper:  ALPACA_BASE_URL=https://paper-api.alpaca.markets
# Live:   ALPACA_BASE_URL=https://api.alpaca.markets
```

> ⚠️ **In this repo, changing that line does not enable live trading, and it cannot.**
> You also need the code-level opt-in:
>
> ```python
> from utils.offline import set_live_mode
> set_live_mode(True, confirm="I_HAVE_REVIEWED_THIS")
> ```
>
> There is deliberately no environment variable and no CLI flag. An env var is one
> stray `export` away from trading your savings.

**Why $500?** Because the first week of live trading always reveals surprises. Your
fills will be worse than paper. Some orders that filled instantly on paper will take
2-3 seconds live. **You want to discover that with $500 at risk, not $5,000.**

The $500 phase teaches you three things paper cannot:

* **Slippage.** Under $0.05/share on AAPL and NVDA; $0.10-$0.30 on mid-caps. Your
  backtested returns have to survive that drag.
* **Execution reliability.** API connections drop. Rate limits get hit. Market data
  lags. Paper trading is more forgiving and hides all of it.
* **Emotional reality.** *This is the one that gets people.*

> **Boring is the part that pays.** The exciting part was the weekend you built the
> bot. The profitable part is the quiet months of letting it run.

The first time your bot takes a losing trade with real money, you will feel it. **The
urge to override will be powerful. Don't.** Write down the feeling. Note the time.
Check the trade log the next day. Nine times out of ten the bot was right and your
panic was the error. The second loss is easier. By the tenth you trust the system.

**Pre-commit to 30 days.** Write it down: *"I will run the bot for 30 days without
changing any parameters or overriding any trades."* Sign it. Put it next to your
monitor. Read it around day 4, when the urge hits.

**Keep a temptation log.** Every time you want to change something, don't; write it
down instead. After 30 days, review. Most entries look foolish in hindsight. The few
good ideas can be tested on paper next cycle.

## The Phase-2 gate (Day 60)

**Go:** Phase-2 Sharpe within 0.3 of Phase 1 · win rate within 5pp · max DD < 15% · no
API failures that caused missed exits · **you did not override the bot.**

**No-Go:** Sharpe < 0.5 or win rate < 40% · API failures caused missed stop-losses ·
you overrode the bot more than once.

## Phase 3: the capital ladder

* **Week 1-2:** → $2,000. If drawdown exceeds 10% at any point, **pause and diagnose.**
* **Week 3-4:** → $5,000. This is where position sizing starts to matter.
* **Week 5-6:** → your target, typically $5,000-$10,000. Beyond that, **$5,000
  increments with a two-week observation period between each step.**

**There is no rush.** The strategies work every trading day. The alpha does not expire
if you take an extra two weeks to scale safely. **The money you lose by scaling too
fast absolutely does expire. It's gone.**

## The Sunday ritual (30 minutes)

1. **Did the risk module block any trades?** Were the blocks correct? If it blocked a
   trade that would have been profitable, **that's fine**: the module protects capital,
   it doesn't optimize returns. If it blocked *zero* trades all week, your position
   sizes might be too small.
2. **What's the rolling 30-day Sharpe?** Trending down for 3+ weeks means something
   changed.
3. **What's the sector breakdown?** 80% in tech is concentration risk whether the module
   caught it or not.
4. **What was average slippage?** Consistently above 0.1% → switch from market to limit
   orders.
5. **What was the biggest single-trade loss?** It should be at or near the 2% cap. If
   it's meaningfully above, investigate why the stop didn't fire.

## When to pull the plug

* Drawdown exceeds **20%** at any capital level.
* Rolling-30-day Sharpe drops below **0.5**.
* **Three consecutive losing weeks.**
* **Claude's API or model changes.** Go back to paper immediately and re-run a full
  30-day Phase 1 before resuming.

These are not failure signals. **They are protection signals.** The traders who survive
long-term are the ones who stop when the data says stop.

## Honest expectations

* **First 30 days paper:** 50-55% win rate, 8-15% annualized, and at least one
  gut-punch day where the portfolio drops 3-4%. Normal.
* **First 30 days live ($500):** expect **15-25% worse than paper** from slippage and
  execution. If your paper Sharpe was 1.3, your live Sharpe will be 0.9-1.1. Normal and
  expected.
* **Months 3-6 at $5K-$10K:** 2-5% monthly. Some months flat or slightly negative.

**If someone tells you they're making 20% per month consistently, they are lying, using
dangerous amounts of margin, or on a hot streak that will end badly.**

## Regulatory

**Pattern Day Trader, in transition.** FINRA's new intraday margin rule replaces the old PDT framework on **June 4,
2026**. Brokers have until **October 20, 2027** to fully switch over. **Your broker may continue
applying the old $25,000 restriction during the transition.** Check your specific
broker before relying on the change.

## The prompt

[`prompts/12_tracking_infra.md`](../prompts/12_tracking_infra.md)

---

*Illustrative results on synthetic sample data. Not indicative of real or historical performance. Educational software. Not financial advice. See [DISCLAIMER.md](../DISCLAIMER.md).*
