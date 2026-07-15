# Chapter 4 lab: the screener

Point it at the day's unusual options flow and it hands back a ranked watchlist of
5-10 names worth a human's attention. Filter, score, rank.

## Build it
Paste [`prompts/03_screener.md`](../../prompts/03_screener.md) into Claude Code. You
get [`screener/screener.py`](../../screener/screener.py) and `tracker.py`, which
records how the picks resolve.

## Run it
```bash
python screener/screener.py
```
```
=== AI Stock Screener ===
Found 12 unusual transactions after filtering.
Analyzing NVDA (1/12)...
  1. [BULL] NVDA | BULLISH | Confidence: 84%
  ...
```
A ranked 5-10 name watchlist, written to `screener/watchlist_YYYYMMDD.json`.

## What to watch for
The BLOCKED line, where a name gets dropped by the liquidity floor. The screener ranks
by raw score first, so a blocked name still shows where it would have ranked; you see
the filter working, not just its result. The `vol/OI > 3x`, `premium > $200K` and
sweep/floor filters are the funnel, and the fixture deliberately includes rows that
fail each one so every filter is provably exercised.

---
Reference: [docs/02-screener.md](../../docs/02-screener.md)
