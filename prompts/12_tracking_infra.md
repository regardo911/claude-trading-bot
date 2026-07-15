# 12 — Build the 90-day tracking infrastructure

> **Source:** Chapter 10 (Phase 1: Paper Trading) · `ch10.md:31`
> Quoted **verbatim** from the manuscript; do not edit the prompt body below.

## The prompt

Open Claude Code in your project directory (`cd ~/ai-trading-bot && claude`) and
paste:

```text
"Help me set up the 90-day go-live tracking infrastructure.

1. Create `tracking/daily_metrics.json` that I'll append to nightly. Schema per entry: `{date, trades_taken, trades_blocked_by_risk, wins, losses, daily_pnl_dollar, daily_pnl_pct, max_drawdown_pct, portfolio_value_close}`.
2. Write `tracking/calculate_metrics.py`, reads `daily_metrics.json` and outputs win rate, annualized Sharpe, max drawdown over the period, profit factor, profitable weeks count.
3. Write `tracking/phase1_assessment.py`, runs `calculate_metrics` on the last 30 days and produces a PASS/FAIL verdict against the Phase 1 criteria: win rate > 50% (or > 45% with PF > 1.5), Sharpe > 1.0, max drawdown < 15%, profit factor > 1.5, 3 of 4 profitable weeks.

Use model `claude-sonnet-4-6` for any Claude calls (probably none needed for this). Run `phase1_assessment.py` against an empty `daily_metrics.json` so I can verify it handles the no-data case gracefully."
```

## Expected output schema

No model output ("probably none needed"). The artifacts are
`tracking/daily_metrics.json` (the schema), `tracking/calculate_metrics.py`, and
`tracking/phase1_assessment.py`.

## How deterministic code consumes it

`tracking/calculate_metrics.py` -> win rate, annualized Sharpe, max drawdown,
profit factor, profitable-weeks count. `tracking/phase1_assessment.py` -> the
Day-30 GO / HOLD / NO-GO verdict.

Deviation **#7**: the book defines profit factor two different ways and applies a
>1.5 gate to it. This module implements ch10's sum-based definition under the
distinct name `gross_profit_factor`, so one name never carries two formulas.

## Offline behaviour in this repo

Fully offline. The prompt's own acceptance test, "Run `phase1_assessment.py`
against an empty `daily_metrics.json` so I can verify it handles the no-data case
gracefully", ships as `fixtures/daily_metrics_empty.json` and as a unit test.
There are also GO and HOLD fixtures:

    python tracking/phase1_assessment.py                       # GO
    python tracking/phase1_assessment.py daily_metrics_hold.json   # HOLD
    python tracking/phase1_assessment.py daily_metrics_empty.json  # NO DATA

## Cost notes

$0.

---

*Educational software. Not financial advice. Trading carries substantial risk of
loss. See [DISCLAIMER.md](../DISCLAIMER.md).*
