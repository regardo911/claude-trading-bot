# Parameter cheat sheet: Appendix B (appendices.md:490-510)

Starting values for each strategy. **Change one parameter at a time and re-run
the Chapter 6 backtest after each change. Never change several at once.**

| Strategy | Parameters |
|---|---|
| **Screener** | Volume/OI: `3.0` · Premium: `$200K` · Confidence: `65` |
| **Flow trader** | Poll: `30s` · Premium: `$500K` · Confidence: `70` · Position: `2%` |
| **Backtester** | Simulations: `1,000` · Position: `2%` · Minimum trades: `100` |
| **Risk module** | Per-trade risk: `2%` · Daily loss cap: `6%` · Stop-loss: `3%` · Sector cap: `40%` · Kelly fraction: `25%` |
| **Prediction market** | Gap: `10%` · Bet size: `$50` · Volume: `10,000+` |
| **Multi-agent** | Cycle: `30 min` · Max recs: `3` · Sector cap: `40%` · Daily halt: `-6%` · Model: Sonnet 4.6 |

## One conflict, resolved

**Minimum trades: 100 here, 30 in the code.** The cheat sheet says 100. The
backtester gates at 30, and Chapter 6 repeats "fewer than 30 valid trades" three
separate times. The worked example wins: **30 is the hard gate** in this repo,
and it is what triggers `VERDICT: INSUFFICIENT DATA`. Treat **100 as the
recommended floor** before you believe any verdict at all. The backtester prints
a note when your trade count falls between the two. (docs/book-deviations.md #2)

## The three ch03 rules that are in no template

Chapter 3 states three rules the author's bots run, and none of them appear in
any parameter block or any printed code:

| Rule | Value | Where it lives in this repo |
|---|---|---|
| Liquidity floor | average daily volume `>= 1,000,000` shares | `utils/signals.py` |
| Geopolitical filter | `-15` confidence points | `utils/signals.py` |
| Tier-1 / Tier-2 conflict | `-20` confidence points + manual review | `utils/signals.py` |

All three are **default-ON** and all three make the bot trade *less*.
(docs/book-deviations.md #14)

## Signal hierarchy (ch03.md:117-125)

1. **Options flow**: the strongest signal.
2. **Dark pool activity**: prints above VWAP = accumulation; below = distribution.
3. **Implied volatility context**: context, not direction.
4. **Sector / market correlation**: moving *against* its sector is the meaningful case.
5. **News and sentiment**: the weakest. By the time it is a headline, it is priced in.

> "Two-tier convergence is interesting. Three-tier convergence is tradeable."
> (ch03.md:151)

The trade gate is **70% confidence**, everywhere in the book.

*Educational software. Not financial advice. See [DISCLAIMER.md](../DISCLAIMER.md).*
