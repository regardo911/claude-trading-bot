# 09 — Live-data estimates (interactive Claude Code)

> **Source:** Chapter 7 (For Live-Data Estimates: Use Claude Code Interactively) · `ch07.md:420`
> Quoted **verbatim** from the manuscript; do not edit the prompt body below.

## The prompt

Open Claude Code in your project directory (`cd ~/ai-trading-bot && claude`) and
paste:

```text
"Read `prediction/markets.json`. Each entry is a Polymarket Gamma market object; the YES probability is `float(outcomePrices[0])` (note `outcomePrices` may be a JSON-encoded string or a real array; handle both). For each contract, use your web search tool to look up the most recent relevant data (polls, economic releases, news, prediction-market history). Then estimate the true probability the way the script's prompt does; but you actually have live data, so reasoning can cite specific dated sources. Write the result to `prediction/estimates.json` with one entry per contract: `question`, `market_price` (the YES probability you computed from outcomePrices), `estimated_probability`, `confidence` (HIGH/MEDIUM/LOW), `reasoning` with cited sources, and `key_data_points`. Skip contracts where you can't find live data. Don't invent."
```

## Expected output schema

`prediction/estimates.json`: one entry per contract with `question`,
`market_price`, `estimated_probability`, `confidence`, `reasoning` **with cited
dated sources**, and `key_data_points`.

## How deterministic code consumes it

`prediction/prediction_analyzer.py::rank_estimates_file()` reads it and runs the
same EV math the standalone script uses.

This is the honest split the chapter makes: the saved script is the always-on
filter, and it says LOW on anything time-sensitive because the vanilla Messages
API has no web search. The interactive session is the always-current researcher.
Do **not** paste this prompt into a `claude.messages.create()` call. It has no
web search and Claude will fabricate the citations.

## Offline behaviour in this repo

Not reproducible offline: it exists precisely to fetch live data. The repo ships
the *consumer* (`rank_estimates_file()`) and tests it against a synthetic
`estimates.json`.

## Cost notes

Claude Code session cost (Pro $20/mo minimum) plus web-search tool calls. No
Anthropic API key needed: this runs inside Claude Code.

---

*Educational software. Not financial advice. Trading carries substantial risk of
loss. See [DISCLAIMER.md](../DISCLAIMER.md).*
