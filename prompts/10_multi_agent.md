# 10 — Build the 4-agent system

> **Source:** Chapter 8 (The Code: multi_agent.py) · `ch08.md:43`
> Quoted **verbatim** from the manuscript; do not edit the prompt body below.

## The prompt

Open Claude Code in your project directory (`cd ~/ai-trading-bot && claude`) and
paste:

```text
"Build me a 4-agent multi-agent trading system. Architecture:

1. The orchestrator runs in sequence (not free-form debate): Monitor → Analyst → Risk Manager → Executor.
2. Each agent is a separate call to `client.messages.create` with model `claude-sonnet-4-6`. The Analyst and Risk Manager get role-specific system instructions. The Executor places orders on Alpaca paper. The Monitor checks portfolio health.
3. The Risk Manager has hard rules it enforces in-prompt: max 2% position, max 40% sector concentration, block all buys if today's P&L is below -3%. It can APPROVE, REDUCE, or REJECT each Analyst recommendation with a logged reason. (Earnings blackout is enforced by ch09's hard `risk_manager.py` module, not the agent; the agent has no live calendar.)
4. The Executor places each approved trade as an Alpaca **bracket order**; a single `MarketOrderRequest` with `order_class=OrderClass.BRACKET`, `take_profit=TakeProfitRequest(limit_price=...)`, and `stop_loss=StopLossRequest(stop_price=...)`. The Analyst's `direction` ("BUY" or "SELL") is carried through every Risk decision and consumed by the Executor: BUY orders place a long bracket (stop below entry, take-profit above); SELL orders place a short bracket (`side=OrderSide.SELL`, stop above entry, take-profit below) on Alpaca paper. Alpaca creates the parent + take-profit child + stop-loss child on fill, and auto-cancels the unfilled child when either side triggers; so protective exits are with the broker the moment the trade opens, not waiting on the bot to be running. Fetch the current quote from Alpaca's `StockHistoricalDataClient.get_stock_latest_quote()` to compute the bracket prices from the Risk Manager's `stop_loss_pct` and `profit_target_pct` percentages. This keeps long/short parity with ch05's single-bot `BUY_SHARES` / `SELL_SHORT` enum.
5. Log every cycle (Monitor + Analyst + Risk + Executor outputs) to `multi_agent/cycle_log.json`.

For the Analyst's signal-fetching, add a shared `get_recent_flow()` helper that calls UW REST `GET /api/option-trades/flow-alerts` once per cycle with `requests.get()` and `Authorization: Bearer $UW_API_KEY`. Pass query params `min_premium=300000`, `min_volume_oi_ratio=3.0`, and `is_sweep=true`. The response uses the documented UW fields (`ticker`, `total_premium`, `volume_oi_ratio`, `has_sweep`, `has_floor`, `type`, `expiry`). Pass the dataset into the Analyst's prompt as `market_data`. The Analyst reasons over real flow, not pretends to fetch it. (Same data-layer pattern as the shared `get_portfolio_state()`; fetch once, share across agents.)

Important: do NOT use the vanilla `client.messages.create('Using Unusual Whales MCP, …')` pattern for the data fetch. That pattern doesn't actually invoke MCP through the Anthropic Messages API and returns hallucinated JSON, same warning as ch04/ch05/ch06.

Save as `multi_agent/multi_agent.py`.

Run one full cycle for me so I can see all 4 agents execute in sequence. The most interesting moment is when the Risk Manager overrides the Analyst, try to surface that disagreement."
```

## Expected output schema

Four schemas, one per agent:

```json
{"status": "HEALTHY|WARNING|CRITICAL", "alerts": [], "actions_needed": []}
{"recommendations": [{"ticker","direction","confidence","suggested_shares","reasoning","signals"}]}
{"decisions": [{"ticker","direction","action":"APPROVE|REDUCE|REJECT","approved_shares","stop_loss_pct":3.0,"profit_target_pct":6.0,"reasoning"}]}
```
The Executor produces no model output; it places bracket orders.

## How deterministic code consumes it

`multi_agent/multi_agent.py`. Monitor -> Analyst -> Risk -> Executor, in sequence,
no loopback. Four API calls per cycle, not fifteen.

Deviation **#4**: every one of these parsers can return `None`, and the printed
orchestrator calls `.get()` on the result without checking. ch04, ch05 and ch07
all guard it; ch08 does not. This repo guards it.

## Offline behaviour in this repo

Routed to `fixtures/claude_responses/multi_agent.json`. The canned cycle reproduces
the chapter's headline moment: the Risk Manager **APPROVEs one, REDUCEs one, and
REJECTs one** of the Analyst's three recommendations, on the sector concentration
the fixture portfolio actually has.

## Cost notes

4-6 API calls per cycle; ~32 cycles per active trading week at 30-minute intervals.
Single-digit dollars per active trading week of Anthropic spend at Sonnet 4.6.
Enabling the revision loop roughly doubles it.

---

*Educational software. Not financial advice. Trading carries substantial risk of
loss. See [DISCLAIMER.md](../DISCLAIMER.md).*
