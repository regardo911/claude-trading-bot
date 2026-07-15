# 3. Flow trader: following the whales in real time (Chapter 5)

![Time-series of a trading session. Each qualifying flow alert is plotted at the minute it printed, with confidence on the vertical axis and a red dashed line at the 70% trade threshold. Filled blue triangles above the line are trades (NVDA, AMZN, TSLA, META); hollow circles below it are passes (MU, COIN, BABA, AMD); a grey X marks IRNT, blocked by the Chapter 3 liquidity floor. The long horizontal gaps between markers are the point.](images/03-flow-trader.png)

*Computed by running `flow_trader.py`'s real functions against the bundled synthetic fixtures (regenerate with `python tools/generate_docs_charts.py`).*

## What it is

The screener is a morning newspaper. This is a police scanner.

It polls Unusual Whales' flow endpoint every 30 seconds, and when a whale drops
$500K+ into a short-dated options position, it sees it within seconds, evaluates it,
and trades before most humans know the sweep happened.

**Five stages:** Poll → Filter → Analyze → Decide → Execute.

## The bot trades **shares**, not options

The options flow is the **signal**. The execution is **stock**. Placing actual
options contracts needs contract-symbol lookup, strike/expiry selection, liquidity
checks and a broker with an options API: out of scope for the chapter, and out of
scope here.

`suggested_action` is one of `BUY_SHARES` / `SELL_SHORT` / `NO_TRADE`.

## The rules

| Constant | Value |
|---|---|
| `CONFIDENCE_THRESHOLD` | `70` |
| `MIN_PREMIUM` | `500000` ($500K for real-time trading) |
| `MAX_POSITION_PCT` | `0.02` (2% of account, **as notional**) |
| `POLL_INTERVAL` | `30` seconds |
| `MAX_DTE` | `14` days |
| stop-loss | `-3.0%` → close |
| profit target | `+6.0%` → scale out half, move the stop to breakeven |
| time limit | 5 trading days → close at market |

Dedup key: `f"{ticker}_{strike}_{timestamp}"` in a `seen_events` set, pruned to the
last 500 when it exceeds 1000. Flow timestamped before **9:35 AM ET** is ignored:
it references a stale underlying price.

> ⚠️ `MAX_POSITION_PCT = 0.02` here is 2% as **notional** ($2,000 on a $100K
> account). `risk/risk_manager.py`'s `MAX_RISK_PER_TRADE = 0.02` is 2% as **risk**
> ($66,600 at a 3% stop). Same number, thirty-three-fold difference.
> **This is deliberate and you must not unify them**. See
> [book-deviations.md #5](book-deviations.md#5).

## How to run it

```bash
python flow_trader/flow_trader.py            # one cycle, then exit
python flow_trader/flow_trader.py --loop     # the real 30-second polling loop
python flow_trader/check_positions.py        # what you're holding
```

## Your first hour

* **Minutes 0-5**: banner, then silence. Normal.
* **Minutes 5-15**: poll cycles complete silently. **Resist the urge to lower your
  filters.** The silence means they're working.
* **Minutes 15-30**: the first alert usually fires. Most score below the threshold
  and log as PASS. That is the system working correctly.
* **Minutes 30-60**: 2-5 alerts on an active day; maybe one trades.

On a slow day you might go 2-3 hours with no qualifying alert. **The bot is patient
by design. Boredom trades are how accounts die.**

## The exit rules (and the short-side bug the 2nd edition fixed)

`check_exits()` sells half a position at its +6% profit target, but reducing a
**short** means *buying it back*, not selling. The current book gets this right
(`OrderSide.BUY if is_short else OrderSide.SELL`), and so does this repo. Earlier
printings submitted `OrderSide.SELL` unconditionally, which on a short at +6% P&L
*adds to the short*: the bot thinks it is taking profit while doubling down. That
one would have cost real money, which is why it is worth showing.

This repo (like the 2nd edition) also implements the breakeven stop and the 5-day
time limit the chapter's prose promises.

```bash
python examples/03_flow_trader_exits.py
```

```
[..] STOP-LOSS: NVDA at -3.0%
[..] PROFIT TARGET: Scaling out 53 of 106 AMZN (sell) at +6.0%
[..] STOP -> BREAKEVEN on the remaining 53 AMZN
[..] PROFIT TARGET: Scaling out 20 of 40 TSLA (cover) at +6.0%
[..] STOP -> BREAKEVEN on the remaining 20 TSLA

Orders the bot actually submitted:
  SELL    53 AMZN
  BUY     20 TSLA      <- covering the short, not doubling it
```

Full reconciliation: [book-deviations.md #13](book-deviations.md#13).

## This stop is a *soft* stop

`check_exits()` runs inside your Python loop. **If the bot is not running, nothing
fires.** For protective orders that live at the broker and execute even when your
API connection drops, use ch08's bracket pattern. See
[06-multi-agent.md](06-multi-agent.md).

## Failure modes

| Symptom | Cause |
|---|---|
| `calculate_position_size` keeps returning `(0, 0)` | no live quote (pre-market/after-hours, or your data tier doesn't cover the ticker). **The `(0,0)` is intentional: skip the trade rather than price it at $0.** |
| Alpaca rejects orders | check `paper=True` and `ALPACA_BASE_URL` |
| `403` from UW | tier limit. Trial $50/wk minimum. |
| Same sweep traded twice | the dedup key includes the timestamp; split sweeps register separately. Group by ticker+strike+expiry within a 2-minute window. |

## Cost

~780 UW REST calls per session at a 30-second poll, but only **20-40 Anthropic
calls**: Claude is called on *qualifying events*, not on every poll. Roughly
**$2-$8 per active trading week of Anthropic spend**. The UW tier cost is flat and
separate.

If you're hitting Anthropic's rate limit, **your filter is too loose.** Tighten
`MIN_PREMIUM`, don't slow the poll.

## The prompt

[`prompts/04_flow_trader.md`](../prompts/04_flow_trader.md)

---

*Illustrative results on synthetic sample data. Not indicative of real or historical performance. Educational software. Not financial advice. See [DISCLAIMER.md](../DISCLAIMER.md).*
