# 06 — Add walk-forward validation

> **Source:** Chapter 6 (Walk-Forward Validation) · `ch06.md:607`
> Quoted **verbatim** from the manuscript; do not edit the prompt body below.

## The prompt

Open Claude Code in your project directory (`cd ~/ai-trading-bot && claude`) and
paste:

```text
"Add a walk-forward validation function to `backtester/backtester.py`. It should: (1) divide the historical data into 3 windows of equal size; (2) for each window N: train filters on windows 1 through N-1, test on window N; (3) print in-sample win rate and out-of-sample win rate for each window. Flag if any test window underperforms its training period by more than 10 percentage points. Run it and show the results."
```

## Expected output schema

In-sample and out-of-sample win rate per window, and a flag on any test window
that underperforms its training period by more than 10 percentage points.

## How deterministic code consumes it

`backtester/backtester.py::walk_forward_validation()`. Three equal windows; train
on 1..N-1, test on N. The result is folded into `report.json` under
`walk_forward`. Two consecutive failed test windows means the strategy gets pulled
from live trading.

## Offline behaviour in this repo

Runs on the same committed CSV fixture. Zero keys, zero network.

## Cost notes

$0. Pure math on data you already have.

---

*Educational software. Not financial advice. Trading carries substantial risk of
loss. See [DISCLAIMER.md](../DISCLAIMER.md).*
