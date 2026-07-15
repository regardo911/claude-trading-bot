# Chapter 10 lab: going live

Track paper-trading performance for 30 days, clear a five-metric gate, then step onto
real capital $500 at a time. This lab is the ladder and its first gate.

## The prompt
Paste [`prompts/12_tracking_infra.md`](../../prompts/12_tracking_infra.md) into Claude
Code for [`tracking/phase1_assessment.py`](../../tracking/phase1_assessment.py) and
`calculate_metrics.py`.

## Run the gate
```bash
python tracking/phase1_assessment.py
```
```
=== PHASE 1 GO/NO-GO ASSESSMENT (Day 30) ===
  Win rate              56.2%       GO
  Sharpe ratio          3.10        GO
  Max drawdown          3.9%        GO
  Gross profit factor   1.60        GO
  Profitable weeks      5 of 7      GO
VERDICT: GO
```

## A GO is a fixture, not a green light
This `GO` runs on a fixture built to pass. It is not permission to trade your savings.
Read the gate itself: all five metrics must clear, and the next step is $500, not
$5,000. Going live is a three-step, deliberately awkward, code-level opt-in
(`set_live_mode(True, confirm=...)`) that no flag or env var can trigger, so this repo
is safer here than earlier printings that let an env var flip real trading. The gross
profit factor is the sum-based metric (ch10), kept distinct from the backtester's
avg-based one ([#7](../../docs/book-deviations.md#7)).

---
Reference: [docs/08-going-live.md](../../docs/08-going-live.md)
