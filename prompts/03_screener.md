# 03 — Build the stock screener

> **Source:** Chapter 4 (The Code: screener.py). Restated verbatim at appendices.md:558-566. · `ch04.md:31`
> Quoted **verbatim** from the manuscript; do not edit the prompt body below.

## The prompt

Open Claude Code in your project directory (`cd ~/ai-trading-bot && claude`) and
paste:

```text
"Build me a stock screener bot using Claude + Unusual Whales' REST API. The bot should:

1. Pull today's unusual options flow by calling UW REST `GET /api/option-trades/flow-alerts` directly with `requests.get()` and `Authorization: Bearer $UW_API_KEY`. Pass query params `min_premium=200000`, `min_volume_oi_ratio=3.0`, and `is_sweep=true`. The response carries fields `ticker`, `strike`, `expiry`, `type`, `volume`, `open_interest`, `volume_oi_ratio`, `total_premium`, `has_sweep`, `has_floor`, `has_multileg`; use those exact field names when filtering and when building the event JSON you send to Claude.
2. For each filtered event, send the event JSON to Claude (`claude-sonnet-4-6`) for multi-signal analysis: interpret the options flow, infer dark pool and IV implications from the event, weigh sector and macro context from training-data knowledge. Return a confidence score 0-100 with a one-paragraph reasoning. Require 3+ converging signals before assigning 70+ confidence.
3. Rank by confidence and print the top 10 to the terminal, plus save the full result as `screener/watchlist_YYYYMMDD.json`.

Important: do NOT use the vanilla `client.messages.create('Using Unusual Whales MCP, …')` pattern for the data fetch. That pattern doesn't actually invoke MCP through the Anthropic Messages API and returns hallucinated JSON. Use the REST API directly. Use Claude only for the per-event analysis.

Use model `claude-sonnet-4-6` for the analysis calls. Add a fallback for Claude returning JSON wrapped in markdown code blocks. Handle 403 (UW tier limit) gracefully.

Save the script as `screener/screener.py` and run it once to verify. Show me the watchlist output."
```

## Expected output schema

```json
{"ticker": "NVDA", "direction": "BULLISH", "confidence": 84, "reasoning": "..."}
```
One object per filtered flow event. Ranked by `confidence`; top 10 printed; the
full set saved to `screener/watchlist_YYYYMMDD.json`.

## How deterministic code consumes it

`screener/screener.py`:

* `get_unusual_flow()` fetches UW REST `/option-trades/flow-alerts` and filters.
* `analyze_signal()` sends one event per call and parses the JSON, tolerating a
  markdown code fence (`parse_claude_json`).
* `run_screener()` ranks, applies the ch03 post-filters, prints, and saves.

The repo's version adds one field to the schema, `dark_pool_read`, which feeds
ch03's Tier1/Tier2 conflict rule. It is optional: an absent or `UNKNOWN` value
means no penalty, so a response in the book's exact printed schema still works.

## Offline behaviour in this repo

`utils/offline.py` routes any prompt containing "unusual options flow event" to
`fixtures/claude_responses/screener.json`, keyed by ticker. One fixture row
(`AMD`) is returned wrapped in a ```json fence on purpose, which exercises the
markdown-fallback parser at ch04.md:159-165.

## Cost notes

1 UW REST call + 1 Anthropic call per filtered event. On a typical day with 15-25
qualifying events, roughly $0.10-$0.30 per run at Sonnet 4.6 pricing ($3 in /
$15 out per MTok). Costs scale linearly if you lower the filters. Keep the
premium floor at $200K.

---

*Educational software. Not financial advice. Trading carries substantial risk of
loss. See [DISCLAIMER.md](../DISCLAIMER.md).*
