# 7. Risk management: the chapter that keeps you alive (Chapter 9)

![Piecewise chart of approved shares against entry price on a $100K account at a 3% stop, on a log scale. The blue curve (53.7% win / 1.79 profit factor) is bound by the 2% risk cap; the green dashed curve (51% / 1.1) sits below it, bound by quarter-Kelly at 1.6%; a flat red line at zero marks the no-edge case (48% / 0.9, Kelly -9.8%) labelled REJECTED-NO-EDGE: zero is the right answer, not "round up to 1 share". Black dots mark F at $12 (5,555 shares), TSLA at $240 (277 shares) and NVDA at $925 (72 shares).](images/07-risk.png)

*Computed by calling `RiskManager.calculate_position_size()` across a price sweep (regenerate with `python tools/generate_docs_charts.py`).*

## What it is

A trader on r/algotrading posted a **61% win rate**, a **1.4 Sharpe**, and average
winners twice the size of his losers. On paper, a great system.

He lost $14,000 in two weeks. No position sizing. His bot put 15% of the account into
a single TSLA options trade; TSLA gapped down 8% on an earnings miss. Then he tried to
make it back by increasing size. Account down 40% from peak.

**The strategy was fine. The risk management was nonexistent.** That is the story
behind every "I lost everything to my trading bot" post on the internet.

This module is not a bot. It is the **gatekeeper** that sits between every bot's
decision and Alpaca's order API. If `evaluate_trade()` doesn't say APPROVED or
REDUCED, the trade does not happen.

## The five rules

1. **Never risk more than 2% of the account on a single trade.**
2. **Never lose more than 6% of the account in a single day.** After that, no new
   positions until tomorrow. This is what stops the revenge-trading spiral.
3. **Every position gets a stop-loss at entry.** Default 3%. It can be moved *closer*
   (a trailing stop). **Never wider.**
4. **No single sector above 40% of portfolio value.**
5. **No trading within 3 days of earnings.** Earnings are binary events. Claude cannot
   reliably predict the direction, and the risk/reward is terrible.

| Constant | Value |
|---|---|
| `MAX_RISK_PER_TRADE` | `0.02`, 2% **as RISK** (position × stop width) |
| `MAX_DAILY_LOSS` | `0.06` |
| `DEFAULT_STOP_LOSS` | `0.03` |
| `MAX_SECTOR_CONCENTRATION` | `0.40` |
| `EARNINGS_BLACKOUT_DAYS` | `3` |
| `USE_KELLY` / `KELLY_FRACTION` | `True` / `0.25` (quarter-Kelly) |

## It makes zero Claude calls. On purpose.

**Every check is math or public data.**

* **Sector** ← `yfinance.Ticker(s).info['sector']`, with a cache. Asking Claude costs
  real money on every multi-agent cycle for a public data field.
* **Earnings** ← `yf.Ticker(s).calendar`. This one is worse: the vanilla Messages API
  has **no live earnings calendar**, so Claude either refuses or guesses from training
  data that is months stale by publication. Use the authoritative source.

A test asserts that `get_anthropic` and `messages.create` appear nowhere in this
module.

## Kelly Criterion

    Kelly % = W − (1 − W) / R

W is your win rate; R is your average win divided by your average loss.

| Scenario | Inputs | Full Kelly | Quarter-Kelly | Verdict |
|---|---|---|---|---|
| **S1** the screener strategy | 53.7% / 1.79 | **+27.8%** | 6.95% | size it |
| **S2** a weaker strategy | 52% / 1.3 | **+15.1%** | 3.8% | size it smaller |
| **S3** no edge | 48% / 0.9 | **−9.8%** | — | **bet ZERO** |

Full Kelly says risk 27.8% per trade. That's insane. Every professional uses half- or
quarter-Kelly. **This module uses quarter-Kelly with a 2% hard cap.**

### The zero floor

> "If your Kelly calculation ever returns a negative number, `calculate_position_size()`
> returns 0 shares and the caller skips the trade automatically… the function will not
> silently round up to 'at least 1 share.'" (ch09.md:77)

**Zero is the right answer.** Rounding "no edge" up to one share defeats the entire
rule. The verdict is `REJECTED-NO-EDGE`.

## The two 2%s are not the same 2%

`flow_trader.MAX_POSITION_PCT = 0.02` is 2% as **notional** → $2,000 on a $100K
account.

`risk_manager.MAX_RISK_PER_TRADE = 0.02` is 2% as **risk** (position × stop width) →
at a 3% stop, **$66,600** on the same account.

**Same number. Thirty-three-fold difference.** The book reconciles them deliberately:
this module is the override. **Do not unify them.**
([book-deviations.md #5](book-deviations.md#5))

## How to run it

```bash
python risk/risk_manager.py
```

## Worked example (offline, real output)

```
--- Part 1: position sizing (Rule 1 only) ---
  NVDA  $ 925.00 @ 3% stop -> $ 27.75/share risk ->     72 shares ($66,600 position)
  F     $  12.00 @ 3% stop -> $  0.36/share risk ->  5,555 shares ($66,660 position)
  TSLA  $ 240.00 @ 5% stop -> $ 12.00/share risk ->    166 shares ($39,840 position)

--- Part 2: the same trades through evaluate_trade() ---
  NVDA at $925, default 3% stop
    Verdict: REDUCED
    Approved shares: 43  | Position: $39,775.00  | Stop: 3%  | Max loss: $1,193.25
    Reduced: Capped at 43 shares to keep Technology under the 40% cap

  TSLA at $240, WIDENED 5% stop (ch09.md:417 -- 'Use it.')
    Verdict: APPROVED
    Approved shares: 166  | Position: $39,840.00  | Stop: 5%  | Max loss: $1,992.00

  NVDA with no-edge inputs (48% win / 0.9 PF)
    Verdict: REJECTED-NO-EDGE

  MU at $118 (earnings inside the 3-day blackout)
    Verdict: BLOCKED
    Reason: MU has earnings in 2 day(s). Blackout period active.
```

**Part 1 reproduces the chapter's printed arithmetic exactly: 72 / 5,555 / 166
shares.** Every one is asserted in
[`tests/test_worked_examples.py`](../tests/test_worked_examples.py).

**The gap between Part 1 and Part 2 is deviation [#12](book-deviations.md#12).** A
$66,600 position in one name on a $100K account is **66.6% concentration**. The
printed `check_sector_concentration()` approves it, because it sums only *existing*
holdings and the portfolio is empty. This repo includes the proposed position, so the
40% cap binds and the trade is REDUCED to 43 shares.

Notice TSLA gets **APPROVED at the full 166 shares**: the wider 5% stop shrinks the
position to $39,840, which fits under the cap. Wider stop, smaller position, **same
dollar risk**. That is the whole point of percentage-based risk management.

## Four deviations land in this module

| # | What |
|---|---|
| [#10](book-deviations.md#10) | `evaluate_trade()` had no `stop_loss_pct`, so the chapter's own "widen TSLA to 5%. **Use it.**" advice was unreachable through the gatekeeper the book tells every bot to call. |
| [#11](book-deviations.md#11) | Rule 4 promises REDUCE; the printed code only BLOCKS, and `remaining_capacity` is computed, returned as a *string*, and never read. |
| [#12](book-deviations.md#12) | The sector check ignored the position you're about to open. |
| [#5](book-deviations.md#5) | **NOT a bug.** Both 2%s ship. |

## Verdicts

| Verdict | Meaning |
|---|---|
| `APPROVED` | trade it at `approved_shares` |
| `REDUCED` | trade it, but smaller: the sector cap bound first |
| `BLOCKED` | a hard rule said no (daily loss, earnings, sector) |
| `REJECTED-NO-EDGE` | Kelly ≤ 0, or the risk budget can't buy one share |

Check order: **daily loss → earnings blackout → sector concentration → position sizing
→ positive-edge gate.**

## Integration

```python
from risk.risk_manager import RiskManager

rm = RiskManager()
rm.initialize_day()

risk_check = rm.evaluate_trade(ticker, entry_price)
if risk_check["verdict"] in ("APPROVED", "REDUCED"):
    shares = risk_check["approved_shares"]
    # place the trade with 'shares'
else:
    print(f"{risk_check['verdict']}: {risk_check['block_reason']}")
```

For the multi-agent system, add it as a **hard check after the Risk Manager agent's
soft evaluation.** The agent uses judgment and reasoning. The code module uses math and
hard limits. **Both must approve.**

## Circuit breakers

1. **Daily loss**: 6% from the day's open → all bots stop for the day.
2. **Consecutive losses**: 5 in a row → 24-hour pause. Five losses in a row suggests
   the market changed or the data feed broke. Either way, stopping beats bleeding.
3. **API anomaly**: 3 consecutive unparseable Claude responses → pause + alert.

**Scale the daily-loss limit to your account size** (ch09.md:549-552):

| Account | Daily loss limit |
|---|---|
| Under $2,000 | 10% (you need room to learn) |
| $2,000-$10,000 | 8% |
| $10,000-$50,000 | **6% (the default)** |
| Above $50,000 | 4% |

This is a **reference table you act on**, not an automatic override: the chapter says
*"Adjust the `MAX_DAILY_LOSS` constant in `risk_manager.py` as your capital grows."*
`check_daily_loss_limit()` enforces the constant exactly as printed. The
**consecutive-loss breaker stays fixed at 5** regardless of account size.

## Trailing stops

Set one on every position **after it reaches 2% profit**. Below 2%, the fixed stop
protects the downside. Above it, the trailing stop ratchets up while giving the trade
room to run. `trail_percent=3.0`, `TimeInForce.GTC`.

## The prompt

[`prompts/11_risk_manager.md`](../prompts/11_risk_manager.md)

---

*Illustrative results on synthetic sample data. Not indicative of real or historical performance. Educational software. Not financial advice. See [DISCLAIMER.md](../DISCLAIMER.md).*
