# 2. Screener: the daily watchlist (Chapter 4)

![Ranked horizontal bar chart of ten tickers by Claude's confidence score, with vertical threshold lines at 65 (watchlist floor) and 70 (trade threshold). Bars are blue for BULLISH and amber for BEARISH. BABA and AMD show dashed markers at their pre-adjustment raw scores; IRNT is struck through and hatched, blocked by the Chapter 3 liquidity floor.](images/02-screener.png)

*Computed by running `screener.py`'s real functions against the bundled synthetic fixtures (regenerate with `python tools/generate_docs_charts.py`).*

## What it is

Runs once a day, a few minutes after the open, and turns the entire options market
into a ranked list of 5-10 names where smart money is moving hardest. Each pick
carries a confidence score and a plain-English reason.

Four stages: **pull → filter → analyze → rank**.

## The rules

| Constant | Value | Why |
|---|---|---|
| `VOL_OI_THRESHOLD` | `3.0` | today's volume is at least 3x the existing open interest |
| `MIN_PREMIUM` | `200_000` | $200K floor. Retail buys options in $1K-$50K chunks; institutions trade in $200K+ blocks. |
| sweep filter | `has_sweep OR has_floor` | aggressive fills, not a series of small orders |
| `CONFIDENCE_THRESHOLD` | `65` | the watchlist floor |
| `MAX_TOKENS` | `800` | on the analysis call |
| `RUN_TIME` | `09:35` | the first five minutes of the open are chaos |

The prompt rule that matters most: **"require 3+ converging signals for 70+."**
Without it, Claude assigns high confidence on options flow alone: a massive call
sweep feels exciting, and the model reflects that excitement.

**Tuning by market condition:** VIX above 25 → vol/OI to 5x and premium to $500K.
VIX below 15 → premium floor to $150K. Fed announcement days → skip the run
entirely.

## How to run it

```bash
python screener/screener.py       # ~90s live; instant offline
python screener/tracker.py        # your hit rate, once picks resolve
```

Cron it for 9:35 AM ET weekdays:

```
35 9 * * 1-5 cd ~/ai-trading-bot && source venv/bin/activate && python screener/screener.py >> screener/log.txt 2>&1
```

## Worked example (offline, real output)

```
Found 12 unusual transactions after filtering.

Analyzing AMD (3/12)...
   ADJUSTED: 71 -> 51 (TIER1<->TIER2 CONFLICT: -20 (ch03) — flow says bullish,
   dark pool says bearish; flagged for manual review.)
Analyzing BABA (10/12)...
   ADJUSTED: 77 -> 62 (GEOPOLITICAL FILTER: -15 (ch03))
Analyzing IRNT (12/12)...
   BLOCKED: LIQUIDITY FLOOR: IRNT average daily volume 417,776 is below the
   1,000,000 floor (ch03)

============================================================
DAILY WATCHLIST (confidence >= 65, after Chapter 3 adjustments)
============================================================

1. [BULL] NVDA | BULLISH | Confidence: 84%
2. [BULL] AMZN | BULLISH | Confidence: 78%
3. [BEAR] TSLA | BEARISH | Confidence: 74%
4. [BEAR] META | BEARISH | Confidence: 72%
5. [BULL] SMCI | BULLISH | Confidence: 69%
6. [BULL] MU   | BULLISH | Confidence: 66%

(12 scored events; 6 cleared 65%.)
```

Those three ADJUSTED / BLOCKED lines are Chapter 3's rules, which appear in **no
code the book prints**. See [book-deviations.md #14](book-deviations.md#14).

## Reading the confidence score

| Band | What it means |
|---|---|
| **85-100** | Rare. Once or twice a week. Pay attention. |
| **70-84** | The sweet spot. Most tradeable setups live here. |
| **50-69** | Interesting, not tradeable. Log it, watch it, don't trade it. |
| **< 50** | Noise. |

**A confidence score is not a probability.** An 80% confidence does not mean an 80%
chance the stock goes up. It means Claude's reasoning across the available inputs
broadly agrees, and the more of those inputs that are *live* rather than
training-data reasoning, the more that agreement is worth.

## What it misses, and that's fine

Stocks moving purely on news with no unusual options flow. Crypto and forex.
Earnings surprises nobody traded options ahead of. Technical breakouts.

It is catching one specific pattern with the highest signal-to-noise ratio
available: someone with a lot of money taking a large, aggressive, time-boxed
position. **The screener is a filter. A very good one. It is not a replacement for
thinking.**

## Cost

1 UW REST call + 1 Anthropic call per filtered event. On a typical day with 15-25
qualifying events, roughly **$0.10-$0.30 per run**. Lower the filters and it scales
linearly. Keep the premium floor at $200K.

## The prompt

[`prompts/03_screener.md`](../prompts/03_screener.md)

---

*Illustrative results on synthetic sample data. Not indicative of real or historical performance. Educational software. Not financial advice. See [DISCLAIMER.md](../DISCLAIMER.md).*
