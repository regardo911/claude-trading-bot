# 11 — Build the risk-management module

> **Source:** Chapter 9 (The Code: risk_manager.py) · `ch09.md:84`
> Quoted **verbatim** from the manuscript; do not edit the prompt body below.

## The prompt

Open Claude Code in your project directory (`cd ~/ai-trading-bot && claude`) and
paste:

```text
"Build me a risk-management module that bolts onto every trading bot from chapters 4-8. The module's job is to enforce 5 hard rules that nothing else can override:

1. Max 2% account risk per trade (calculated as `position_size × stop_loss_pct`)
2. Max 6% daily loss → after that, no new positions until next day
3. Every position gets a 3% stop-loss at entry (default; parameterizable per trade)
4. No single sector above 40% of portfolio value
5. No trades within 3 days of earnings

Also implement:
- Kelly Criterion position sizing: use quarter-Kelly as the recommended risk size, capped by the 2% hard limit. If Kelly is zero or negative, return 0 shares and let the caller reject the trade as `REJECTED-NO-EDGE`. Do NOT round 0 up to 1 share; the whole point of negative-Kelly-means-bet-zero is that zero is the right answer.
- Sector lookup via `yfinance.Ticker(symbol).info.get('sector')` with a local instance cache. Sector is a public data field, not a judgment call; don't burn Anthropic API calls on it.
- Earnings check via yfinance's calendar (`yf.Ticker(symbol).calendar`). Do NOT ask Claude 'does X have earnings within 3 days?'; vanilla Messages API has no live earnings calendar; Claude will guess from training data which is months stale by publication.
- A demo function that runs a sample trade through `evaluate_trade()` and shows what gets blocked vs approved

Use alpaca-py for portfolio fetches and yfinance for sector + earnings lookups. Save as `risk/risk_manager.py`. (No Claude calls needed for this module; every check is math or public data.)

Run the demo to verify the module works. Then show me a 10-line integration snippet I can paste into `flow_trader.py` to actually gate trades."
```

## Expected output schema

**No model output.** "No Claude calls needed for this module; every check is math or
public data." Sector comes from `yfinance.Ticker(s).info['sector']`; earnings from
`yf.Ticker(s).calendar`. Asking Claude for either is the wrong tool: sector is a
public field, and the vanilla Messages API has no live earnings calendar.

## How deterministic code consumes it

`risk/risk_manager.py`. `evaluate_trade()` is the gatekeeper every bot calls before
it orders. Verdicts: `APPROVED` / `REDUCED` / `BLOCKED` / `REJECTED-NO-EDGE`.

Four deviations land here: **#10** (`stop_loss_pct` plumbed into
`evaluate_trade`), **#11** (the REDUCE path Rule 4 promises), **#12** (sector
concentration now includes the *proposed* position), and **#5** (which is NOT a
bug: ch05's 2% notional and ch09's 2% risk are different quantities and both
ship).

## Offline behaviour in this repo

Fully offline. This is the highest-value offline test surface in the book: every
check is pure math or public data, so `APPROVED`, `REDUCED`, `BLOCKED` and
`REJECTED-NO-EDGE` are all deterministically assertable. `python risk/risk_manager.py`
reproduces ch09's printed Kelly scenarios (0.278 / 0.151 / **-0.098 -> bet zero**)
and its position sizes (**72 / 5,555 / 166 shares**) exactly.

## Cost notes

$0 of Anthropic spend, by design. yfinance is free.

---

*Educational software. Not financial advice. Trading carries substantial risk of
loss. See [DISCLAIMER.md](../DISCLAIMER.md).*
