# 04 — Build the options-flow trading bot

> **Source:** Chapter 5 (The Code: flow_trader.py) · `ch05.md:59`
> Quoted **verbatim** from the manuscript; do not edit the prompt body below.

## The prompt

Open Claude Code in your project directory (`cd ~/ai-trading-bot && claude`) and
paste:

```text
"Build me a real-time-ish options flow trading bot. Architecture:

1. Poll Unusual Whales' REST endpoint `GET /api/option-trades/flow-alerts` every 30 seconds with `requests.get()` and `Authorization: Bearer $UW_API_KEY`. Pass query params `min_premium=500000`, `min_volume_oi_ratio=3.0`, `max_dte=14`, and `is_sweep=true`. The response carries fields `ticker`, `strike`, `expiry`, `type`, `volume`, `open_interest`, `volume_oi_ratio`, `total_premium`, `has_sweep`, `has_floor`, `has_multileg`; use those exact names when filtering and when building the event JSON.
2. For each new event, send the event JSON to Claude (`claude-sonnet-4-6`) for rapid 5-signal analysis using the same approach as Chapter 4 (interpret the event + use training-data knowledge of the ticker; do not claim live data Claude can't reach). Get a confidence score 0-100.
3. If confidence >= 70%, place a paper trade on Alpaca **in shares of the underlying**; this bot uses options flow as a directional signal but executes as stock. Claude's `suggested_action` must be one of `BUY_SHARES`, `SELL_SHORT`, or `NO_TRADE`. BUY_SHARES → `OrderSide.BUY`; SELL_SHORT → `OrderSide.SELL` (Alpaca paper allows shorting). NO_TRADE skips the order. Position size 2% of portfolio value, plain `MarketOrderRequest` with `TimeInForce.DAY`. Get the current price for sizing from Alpaca's `StockHistoricalDataClient.get_stock_latest_quote()`, NOT from a Claude prompt (Claude has no live market data via the SDK).
4. Log every event to `flow_trader/trade_log.json` (whether traded or passed) with timestamp, ticker, direction, confidence, reasoning, and order details.
5. Deduplicate events using ticker+strike+timestamp so the same sweep doesn't trigger multiple trades within consecutive poll windows.

Important: do NOT use the vanilla `client.messages.create('Using Unusual Whales MCP, …')` pattern for the data fetch. That pattern doesn't actually invoke MCP through the Anthropic Messages API and returns hallucinated JSON. Use UW REST directly. Handle 403 (tier limit) gracefully.

Use model `claude-sonnet-4-6`. Use alpaca-py with `paper=True`. Save as `flow_trader/flow_trader.py`.

Then write `flow_trader/check_positions.py`: a small script that prints my current Alpaca paper positions with P&L.

Run `flow_trader.py` and let it poll for one cycle so I can see the startup banner and the empty-poll output. Don't leave it running."
```

## Expected output schema

```json
{"ticker": "NVDA", "direction": "BULLISH", "confidence": 84,
 "reasoning": "...", "suggested_action": "BUY_SHARES"}
```
`suggested_action` is one of `BUY_SHARES` / `SELL_SHORT` / `NO_TRADE`. The bot
trades **shares of the underlying**: the options flow is the signal, the stock
is the execution.

## How deterministic code consumes it

`flow_trader/flow_trader.py`. `analyze_flow_event()` parses this; `execute_trade()`
maps `BUY_SHARES -> OrderSide.BUY` and `SELL_SHORT -> OrderSide.SELL`; the trade
only fires at `confidence >= 70`. Every decision is logged to
`flow_trader/trade_log.json`, traded or not.

## Offline behaviour in this repo

Routed to `fixtures/claude_responses/flow_trader.json`. The offline UW stub applies
`min_premium` / `min_volume_oi_ratio` / `max_dte` server-side, exactly as UW
would, and the fixture deliberately contains rows that fail each filter (plus one
timestamped before 9:35 AM ET) so every filter is provably exercised.

## Cost notes

~780 UW REST calls per 6.5-hour session at a 30-second poll, but only ~20-40
Anthropic calls: Claude is called on *qualifying events*, not on every poll.
Roughly **$2-$8 per active trading week of Anthropic spend**. The UW tier cost is
flat and separate.

---

*Educational software. Not financial advice. Trading carries substantial risk of
loss. See [DISCLAIMER.md](../DISCLAIMER.md).*
