# 6. Multi-agent: your AI hedge fund on a laptop (Chapter 8)

![Funnel diagram of one multi-agent cycle. The Analyst produces 3 recommendations; the Risk Manager approves one, reduces one and rejects one, leaving 2; the Executor fills 2 bracket orders. Annotations above show REJECTED META (sector concentration) and REDUCED AMD (15 shares approved of the 40 requested). Below: 80 shares requested, 37 shares actually bought.](images/06-multi-agent.png)

*Computed by running one real `run_multi_agent_cycle()` against the bundled synthetic fixtures (regenerate with `python tools/generate_docs_charts.py`).*

## What it is

Four specialized Claude instances with different jobs and **adversarial
incentives**, run in sequence.

| Agent | Job | Authority |
|---|---|---|
| **Monitor** | portfolio health, alerts, circuit-breaker conditions | can halt the cycle |
| **Analyst** | find opportunities in real flow | recommends. **Does not size. Does not trade.** |
| **Risk Manager** | evaluate every recommendation against the portfolio | **APPROVE / REDUCE / REJECT** |
| **Executor** | place approved trades as Alpaca bracket orders | executes only what Risk approved |

**Monitor → Analyst → Risk → Executor. Sequential. No loopback.**

> "The Risk Manager gets the last word. Period." (ch08.md:603)

## Why sequential, and why four

Free-form debate produces circular arguments ("but the signal is strong" / "but the
concentration is too high" / "but this is a once-a-week setup") and costs **10-15 API
calls per decision**. Sequential processing with no loopback forces a decision in one
pass and costs **exactly 4**: one per agent.

Seven agents is overkill for these strategies, and every agent you add increases cost
and latency. **Four is the minimum viable hedge fund.**

The portfolio snapshot is fetched **once** per cycle and threaded through every agent.
Re-introducing per-agent `get_portfolio_state()` calls is the easiest way to silently
quadruple your Alpaca request rate without buying anything for it. A test enforces
the single fetch.

## The headline moment

```bash
python multi_agent/multi_agent.py
```

```
[MONITOR] Status: WARNING
[MONITOR] ALERT: NVDA is down 3.0% and is sitting on its stop-loss threshold.
[MONITOR] ALERT: Technology exposure is 30.8% of portfolio value across NVDA and MU.

[ANALYST] Found 3 recommendations.
[ANALYST] NVDA: BUY | Confidence: 84% | Shares: 25
[ANALYST] AMD: BUY | Confidence: 76% | Shares: 40
[ANALYST] META: SELL | Confidence: 71% | Shares: 15

[RISK] APPROVED: NVDA (22 shares)
[RISK] REDUCED: AMD to 15 shares (Portfolio is already 30.8% technology. The
       Analyst's 40 shares would push the sector past the 40% cap once NVDA fills.)
[RISK] REJECTED: META (the portfolio would be over 40% technology after NVDA and
       AMD and this cycle has already spent its risk budget.)

[EXECUTOR] Placing 2 bracket order(s)...
[EXECUTOR] FILLED (BUY): NVDA (22 shares @ ~$911.80) | order_class=bracket |
           Stop @ $884.45 (-3.0%) | Target @ $966.51 (+6.0%)
[EXECUTOR] FILLED (BUY): AMD (15 shares @ ~$168.00) | order_class=bracket |
           Stop @ $162.96 (-3.0%) | Target @ $178.08 (+6.0%)
```

**All three of the Analyst's recommendations were individually sound.** Together they
would have built dangerous sector concentration. The Analyst doesn't track portfolio
composition. The Risk Manager doesn't evaluate trade quality. **Only the combination
produces the right answer.**

That is why multi-agent systems outperform single agents. Not because they're
smarter, because they have specialized knowledge and **adversarial incentives**.

## Bracket orders: the protective legs live at the broker

One `MarketOrderRequest` with `order_class=OrderClass.BRACKET`,
`take_profit=TakeProfitRequest(limit_price=...)` and
`stop_loss=StopLossRequest(stop_price=...)`. Alpaca creates the parent, the
take-profit child and the stop-loss child on fill, and auto-cancels the unfilled
child when either side triggers.

**So the protective exits are with the broker the moment the trade opens.** They fire
even when the bot is offline, and even when your API connection drops during a crash,
which is exactly the ch11 failure mode they exist to survive.

* **Long:** stop *below* entry, take-profit *above*.
* **Short:** mirrored. Stop above, take-profit below.
* `time_in_force` **must** be `DAY` or `GTC`. A bracket is rejected with anything else.

**The bracket-order checkpoint:** after a cycle fills, open the Alpaca paper
dashboard → Orders, and confirm **three orders** in the same family. If you see only
the parent, the bracket silently downgraded: most likely `order_class` got dropped
or the TIF is wrong. A test asserts `result.order_class == "bracket"`.

> ch11 mis-cites bracket orders to "Chapter 9". **They are ch08's.**
> ([book-deviations.md #15](book-deviations.md#15))

## The rules

| Constant | Value |
|---|---|
| `CYCLE_INTERVAL` | `1800` (30 minutes) |
| `MAX_RECOMMENDATIONS` | `3` (the Analyst returns top 3 max) |
| `RISK_OVERRIDE_THRESHOLD` | `0.40` (sector cap) |
| `DAILY_LOSS_HALT` | `0.06` |
| `MONITOR_ALERT_THRESHOLD` | `0.03` |
| `REVISION_ENABLED` | `False` (the revision loop doubles the API calls) |
| `MODEL` | `claude-sonnet-4-6` |

`get_recent_flow(min_premium=300_000, min_volume_oi_ratio=3.0, is_sweep=True)`, capped
at `flow[:50]` to keep the Analyst prompt tight.

**Optional production upgrade:** swap the Analyst and Risk Manager to
`claude-opus-4-7`. Roughly 1.7x the cost, noticeably tighter on edge-case risk
evaluations. Default to Sonnet; upgrade selectively.

## Deviation #4: the crash the printed orchestrator has coming

Every one of the four agents' JSON parsers can return `None`. The printed
`run_multi_agent_cycle()` then calls `.get()` on it → `AttributeError: 'NoneType'
object has no attribute 'get'`.

ch04, ch05 and ch07 **all** guard this. ch08 does not. This repo does.

**If the Risk Manager cannot speak, nothing trades.** That is the correct failure mode
for an agent whose entire job is to say no.
([book-deviations.md #4](book-deviations.md#4))

## Debugging a bad trade

1. **Read `multi_agent/cycle_log.json`.** Every agent's full output, in order.
2. **Check the Analyst's reasoning** against the flow JSON. It cannot hallucinate the
   dataset (`get_recent_flow()` fetched it), but it can misinterpret it. If the
   signals were real and the stock still went the wrong way, that's just a losing
   trade. It happens.
3. **Check the Risk Manager.** The most common bug is **stale portfolio data**.
4. **Check for prompt leakage.** The Analyst's enthusiasm can infect the Risk
   Manager's evaluation. The fix is in the prompt: *"Ignore the Analyst's confidence
   score. Evaluate purely on portfolio risk metrics."* Keep the roles adversarial.
5. **Compare to a single agent.** If a single agent would have made the same bad
   trade, the problem is the analysis, not the architecture.

## Cost

4-6 API calls per cycle; ~32 cycles per active trading week at 30-minute intervals.
**Single-digit dollars per active trading week** of Anthropic spend at Sonnet 4.6.
The first month, while you're tuning prompts and re-running cycles to debug, expect a
noticeably higher tab.

Enabling `REVISION_ENABLED` roughly doubles it.

## The prompt

[`prompts/10_multi_agent.md`](../prompts/10_multi_agent.md)

---

*Illustrative results on synthetic sample data. Not indicative of real or historical performance. Educational software. Not financial advice. See [DISCLAIMER.md](../DISCLAIMER.md).*
