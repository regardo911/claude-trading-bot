# Architecture

## The one thing the book repeats more than any other: **two flows, not one**

There are exactly two ways to get live market data into Claude in this book, and
they are not interchangeable. There is also a **third pattern that looks like it
works and doesn't**: it returns confident, well-formatted, completely invented
JSON, which is the worst possible failure mode for a trading bot.

If you internalize nothing else from this page, internalize the struck-through
lane.

```mermaid
flowchart LR
    subgraph A["FLOW 1 — Interactive Claude Code (ad-hoc questions)"]
        direction LR
        A1["You paste a prompt<br/>into Claude Code"] --> A2["Claude Code dispatches<br/>through the registered<br/><b>UW MCP server</b>"]
        A2 --> A3["Live options flow"]
        A3 --> A4["Claude analyzes"]
        A4 --> A5["You (or Claude Code)<br/>place a trade"]
    end

    subgraph B["FLOW 2 — Saved standalone script (everything this repo ships)"]
        direction LR
        B1["python flow_trader.py"] --> B2["<b>UW REST</b><br/>/api/option-trades/flow-alerts<br/>Authorization: Bearer"]
        B2 --> B3["Claude, via the<br/>Anthropic SDK<br/>(messages.create)"]
        B3 --> B4["Alpaca<br/>(paper=True)"]
    end

    subgraph C["FLOW 3 — THE TRAP. Does not work."]
        direction LR
        C1["python my_bot.py"] -.-> C2["messages.create(<br/>'Using Unusual Whales<br/>MCP, get the flow...')"]
        C2 -.-> C3["<s>live data</s><br/><b>HALLUCINATED JSON</b><br/>fake tickers, fake premiums,<br/>confidently formatted"]
    end

    style C fill:#fdecea,stroke:#d03b3b,stroke-width:2px,stroke-dasharray: 6 4
    style C3 fill:#fdecea,stroke:#d03b3b,stroke-width:2px
    style A fill:#eaf2fc,stroke:#2a78d6
    style B fill:#e9f7f1,stroke:#1baf7a
```

**Why Flow 3 fails:** the vanilla Anthropic Messages API has **no MCP connection**.
MCP is dispatched by the *client* (Claude Code), not by the model. A saved script
calling `messages.create()` with a prompt that says "Using Unusual Whales MCP…"
gets a model with no tool to call. Ask it for JSON it can't fetch, and it invents
JSON instead. It will look right. It will be wrong.

**Every saved script in this repo uses Flow 2**, deliberately, which is why they
all run standalone.

> There is deliberately **no `mcp_config.json`** anywhere in this repository.
> The `pip install unusual-whales-mcp` + config-file pattern you'll find in some
> community write-ups is not how the official UW MCP works. That PyPI package is
> a **community fork**. The official server is Node-based, runs via `npx`, and is
> registered with Claude Code through `claude mcp add`. `claude mcp list` is the
> source of truth. (ch02.md:353)

---

## What this repo actually is

```mermaid
flowchart TB
    subgraph EXT["External surfaces — every one of them keyed or paid"]
        UW["Unusual Whales REST<br/><i>$50/wk floor</i>"]
        ANT["Anthropic Messages API<br/><i>per-token</i>"]
        ALP["Alpaca<br/><i>account required</i>"]
        YF["yfinance<br/><i>free, fragile</i>"]
        GAM["Polymarket Gamma<br/><i>free, public</i>"]
        KAL["Kalshi<br/><i>RSA-PSS key</i>"]
    end

    SWITCH{{"<b>utils/offline.py</b><br/>THE OFFLINE SWITCH<br/>default: ON"}}

    subgraph FIX["fixtures/ — deterministic, seeded, synthetic"]
        F1["uw_flow_alerts.json"]
        F2["claude_responses/*.json"]
        F3["alpaca_state.json"]
        F4["yfinance_prices.json<br/>yfinance_sectors.json"]
        F5["gamma_markets.json"]
        F6["historical_flow.csv<br/><i>423 trades</i>"]
    end

    subgraph BOTS["The eight catalog items"]
        S["setup/ — the 4/4 gate (ch02)"]
        SC["screener/ (ch04)"]
        FT["flow_trader/ (ch05)"]
        BT["backtester/ (ch06)"]
        PR["prediction/ (ch07)"]
        MA["multi_agent/ (ch08)"]
        RM["risk/ (ch09)"]
        TR["tracking/ (ch10)"]
    end

    BOTS --> SWITCH
    SWITCH -->|"default — no keys, no network"| FIX
    SWITCH -.->|"CTB_OFFLINE=0 + real keys"| EXT

    SC --> RM
    FT --> RM
    MA --> RM
    RM -->|"APPROVED / REDUCED only"| ALP

    style SWITCH fill:#fff4d9,stroke:#eda100,stroke-width:3px
    style FIX fill:#e9f7f1,stroke:#1baf7a
    style EXT fill:#fdecea,stroke:#d03b3b
    style RM fill:#eaf2fc,stroke:#2a78d6,stroke-width:2px
```

**Every artifact in this book touches a keyed or paid surface.** That is not a
criticism of the book. It is honest about the $50/week Unusual Whales floor from
page one. But it means a companion repo that only runs when you hold all four
credentials would be useless to almost everyone who buys it.

So the default is inverted: **offline is on unless you turn it off.** Each stub
answers the exact request/response schema the book's code expects, so the code
paths that run against fixtures are the same code paths that run against the live
APIs.

---

## The risk module is a gatekeeper, not a bot

Notice where `risk/` sits in the diagram above. It is not a strategy. It is the
thing that stands between **every** bot's decision and Alpaca's order API
(ch09.md:423). The screener, the flow trader and the multi-agent system all route
through it, and it can say no to any of them.

It makes **no Claude calls at all**. Every check is math or public data:

| Rule | Source of truth |
|---|---|
| Position sizing (quarter-Kelly, 2% cap, zero floor) | arithmetic |
| Daily loss limit | Alpaca account value |
| Stop-loss at entry | arithmetic |
| Sector concentration | `yfinance.Ticker(s).info['sector']` |
| Earnings blackout | `yf.Ticker(s).calendar` |

Asking Claude "what sector is NVDA in?" costs real money on every multi-agent
cycle for an answer yfinance gives free. Asking Claude "does NVDA have earnings in
three days?" is worse: the vanilla Messages API has **no live earnings calendar**,
so it either refuses or guesses from training data that is months stale by
publication.

---

## Two protective-stop mechanisms, and they are not the same

| | ch05 `flow_trader` | ch08 `multi_agent` |
|---|---|---|
| Mechanism | **soft stop in code** | **Alpaca bracket order** |
| Lives where | in your Python loop | at the broker |
| Fires when the bot is offline? | **No** | **Yes** |
| Fires when your API connection drops? | **No** | **Yes** |

ch05 is explicit about this: its stop is "a *soft stop in code*, not a hard stop
order placed with the broker" (ch05.md:491). If the bot is not running, nothing
fires.

ch08's Executor submits a single `MarketOrderRequest` with
`order_class=OrderClass.BRACKET`, and Alpaca creates the parent, the take-profit
child and the stop-loss child on fill. The protective legs are with the broker from
the moment the trade opens.

ch11 recommends bracket orders as the fix for the "API goes down during a crash"
failure mode, and mis-cites them to "Chapter 9". **They are ch08's.** (See
[book-deviations.md #15](book-deviations.md#15).)

---

## Data flow through one screener run

```mermaid
sequenceDiagram
    participant You
    participant Screener as screener.py
    participant UW as UW REST (or fixture)
    participant Claude as Claude (or stub)
    participant Ch3 as utils/signals.py

    You->>Screener: python screener/screener.py
    Screener->>UW: GET /api/option-trades/flow-alerts<br/>min_premium=200000, min_volume_oi_ratio=3.0
    UW-->>Screener: flow alerts
    Note over Screener: Python-side filter:<br/>has_sweep OR has_floor
    loop one call per surviving event
        Screener->>Claude: the event JSON + the 5-dimension prompt
        Claude-->>Screener: {direction, confidence, dark_pool_read, reasoning}
        Screener->>Ch3: adjust_confidence(...)
        Note over Ch3: ADV floor (block)<br/>geopolitical −15<br/>Tier1/Tier2 conflict −20
        Ch3-->>Screener: adjusted score, or BLOCKED
    end
    Note over Screener: rank, cut at 65, print top 10
    Screener-->>You: watchlist_YYYYMMDD.json
```

The `utils/signals.py` step is this repo's addition. Chapter 3 states three rules
its bots run; **no code the book prints implements any of them.** See
[book-deviations.md #14](book-deviations.md#14).

---

## Repository layout

```
claude-trading-bot/
├── setup/          ch02   the 4/4 gate before you build anything
├── screener/       ch04   scan the flow, rank a watchlist
├── flow_trader/    ch05   poll, analyze, decide, execute
├── backtester/     ch06   Monte Carlo + overfit check. NO LLM, by design.
├── prediction/     ch07   Polymarket/Kalshi analyzer. READ-ONLY, forever.
├── multi_agent/    ch08   Monitor → Analyst → Risk → Executor
├── risk/           ch09   five hard rules. The gatekeeper.
├── tracking/       ch10   the 90-day go-live ladder
├── utils/
│   ├── offline.py         THE OFFLINE SWITCH + every deterministic stub
│   └── signals.py         ch03's analysis contract, as code
├── prompts/        the 12 verbatim PASTE TO CLAUDE CODE blocks
├── templates/      Appendix B — 5 strategy templates + the cheat sheet
├── fixtures/       deterministic, seeded, synthetic. Zero keys.
├── examples/       one runnable offline demo per catalog item
├── tests/          every CHECKPOINT in the book, as an assertion
├── tools/          generate_docs_charts.py · demo.py
└── docs/           you are here
```

`ai-trading-bot/` (the tree ch02 has you build) is **your own local project
directory**, not this repo. This repo is the reference implementation you compare
against.

---

*Educational software. Not financial advice. See [DISCLAIMER.md](../DISCLAIMER.md).*
