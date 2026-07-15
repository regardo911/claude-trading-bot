# Chapter 3 lab: the signal hierarchy

Chapter 3 is criteria, not a script. It sets what counts as a tradeable signal before
any bot acts: a five-tier hierarchy, a 70% trade threshold, and three hard rules the
author says his bots run. Those three rules are the interesting part, because they
appear in no printed code anywhere in the book.

## Where the rules live
The screener prompt ([`prompts/03_screener.md`](../../prompts/03_screener.md)) carries
the tiering, and [`utils/signals.py`](../../utils/signals.py) implements the three
hard rules as code: the 1M-share liquidity floor, the -15 geopolitical penalty, and
the -20 Tier-1/Tier-2 conflict penalty.

## Watch them fire
The rules run inside the screener:
```bash
python screener/screener.py
```
```
   ADJUSTED: 71 -> 51 (TIER1<->TIER2 CONFLICT: -20 (ch03) — flow says bullish, dark pool says bearish; flagged for manual review.)
   BLOCKED: LIQUIDITY FLOOR: IRNT average daily volume 417,776 is below the 1,000,000 floor (ch03)
```

## This is deviation #14
Chapter 3 states these rules as already running, yet no printed script in the book
implements any of them. This repo does, default-ON, and all three push toward fewer
trades: the conservative direction. See
[book-deviations.md #14](../../docs/book-deviations.md#14).

---
Reference: [docs/02-screener.md](../../docs/02-screener.md) · [utils/signals.py](../../utils/signals.py)
