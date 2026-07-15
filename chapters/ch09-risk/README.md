# Chapter 9 lab: risk management

The module that sits between every bot's decision and the broker. Five hard rules,
quarter-Kelly sizing, and a zero floor for no-edge strategies. Nothing trades if the
gatekeeper says no.

## The prompt
Paste [`prompts/11_risk_manager.md`](../../prompts/11_risk_manager.md) into Claude Code
for [`risk/risk_manager.py`](../../risk/risk_manager.py).

## Run it
```bash
python risk/risk_manager.py
```
```
--- Kelly Criterion (ch09.md:59-77) ---
  S1 screener strategy: 53.7% win / 1.79 PF -> Kelly +0.278 -> quarter-Kelly 6.96%
  S3 no edge          : 48.0% win / 0.9 PF -> Kelly -0.098 -> bet ZERO
  NVDA  $925.00 @ 3% stop -> 72 shares ($66,600 position)
  ... APPROVED / REDUCED / BLOCKED / REJECTED-NO-EDGE ...
```

## Three still-live book bugs, all visible
This chapter carries three bugs the current book still has, and the repo shows each
one. Rule 1 sizes NVDA at the book's exact 72 shares, then the gatekeeper REDUCES it,
because 72 shares is 66.6% of the account against a 40% sector cap
([#12](../../docs/book-deviations.md#12)). A `REDUCED` verdict exists because the
book's prose promises "reduce, or reject" while its printed code only ever blocked
([#11](../../docs/book-deviations.md#11)). And `evaluate_trade()` now takes a custom
stop width, so ch09's own "widen TSLA to 5%" advice is reachable
([#10](../../docs/book-deviations.md#10)).

---
Reference: [docs/07-risk.md](../../docs/07-risk.md)
