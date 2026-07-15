# Glossary

The book's Appendix D, 33 terms, with a note where a term touches this repo's code.

**Ask**: The lowest price a seller is willing to accept. When you buy at market, you pay the ask.

**Backtest**: Running a trading strategy against historical data to measure how it would have performed. → [`backtester/`](../backtester/backtester.py)

**Bid**: The highest price a buyer is willing to pay. When you sell at market, you receive the bid.

**Block trade**: A large options or stock transaction executed as a single order, typically by institutional investors.

**Bracket order**: A single submission that opens three orders on fill: the entry, a take-profit limit, and a stop-loss stop. The protective legs live **at the broker**, so they fire even when your bot is offline. → ch08's Executor, **not** ch09 ([#15](book-deviations.md#15)).

**Circuit breaker**: An automated rule that halts trading when predefined loss thresholds are exceeded. This repo ships three: 6% daily loss, 5 consecutive losses, 3 consecutive unparseable model responses.

**CLOB**: Central Limit Order Book. Polymarket's CLOB API at `clob.polymarket.com` exposes orderbook snapshots and order placement; market **discovery** goes through the separate **Gamma** API at `gamma-api.polymarket.com`. **Mixing the two is the most common Polymarket integration error.**

**Dark pool**: A private exchange where institutions trade large blocks without displaying the orders publicly. Prints **above** VWAP suggest accumulation; **below**, distribution. This is Tier 2 in ch03's signal hierarchy.

**DCM (Designated Contract Market)**: A CFTC-regulated venue authorized to list event contracts in the US. Polymarket received DCM status in late 2025; Kalshi has been one since 2021.

**Delta**: How much an option's price changes for a $1 move in the underlying. A delta of 0.5 means the option moves $0.50 for every $1 the stock moves.

**Expected value (EV)**: The average outcome of a bet if repeated many times. Positive EV means profitable long-term. → `calculate_expected_value()` in [`prediction/`](../prediction/prediction_analyzer.py)

**Gamma**: The rate of change of delta. High gamma means the option's sensitivity to the stock price is changing rapidly. *(Not to be confused with Polymarket's Gamma Markets API. Same word, unrelated.)*

**Implied volatility (IV)**: The market's forecast of how much a stock will move, derived from options prices. High IV means expensive options. Tier 3 in the signal hierarchy: **IV is context, not direction.**

**IV percentile**: Where current implied volatility sits relative to the last 52 weeks. An IV percentile of 20 means IV is lower than 80% of the past year.

**Kelly Criterion**: A formula for optimal bet sizing from your win rate and payoff ratio: `Kelly % = W − (1−W)/R`. This repo uses **quarter-Kelly with a 2% hard cap and a zero floor**. → [`risk/`](../risk/risk_manager.py)

**MCP (Model Context Protocol)**: A standard from Anthropic that lets Claude connect to external tools and data. **A vanilla `messages.create()` prompt that says "Using MCP, …" does NOT actually invoke MCP**: it returns hallucinated JSON. The real path is registering servers with Claude Code via `claude mcp add`. → [architecture.md](architecture.md)

**Monte Carlo simulation**: Running thousands of randomized scenarios to estimate the range of possible outcomes for a strategy. It only works if you resample **with** replacement (a bootstrap); permuting the same trades collapses every run to the identical value. The 2nd-edition book and this repo both get this right. See [#6](book-deviations.md#6) for why it is a subtle trap.

**Open interest (OI)**: The total number of outstanding options contracts that haven't been exercised or expired. The **volume/OI ratio** is the screener's primary filter: above 3x means today's activity is at least three times the existing position.

**Overfitting**: Tuning a strategy's parameters so precisely to historical data that it fails on new data. You aren't finding a pattern; you're fitting noise. Caught by the in-sample/out-of-sample split.

**Paper trading**: Trading with simulated money. **The default everywhere in this repo**, and it cannot be turned off by a flag or an environment variable.

**PDT (Pattern Day Trader)**: A FINRA designation for accounts making 4+ day trades within 5 business days. The historical $25,000 minimum-equity requirement applied when an account was so designated. FINRA's new **intraday margin framework** replaces the old day-trading margin rule with one tied to actual market exposure. It takes effect June 4, 2026, and brokers have until October 20, 2027 to transition. **Your broker may continue applying the old framework during the transition. Check.**

**Profit factor**: **Two different formulas in this book, under one name.** ch06 (and Kelly) uses *average* win / *average* loss. ch10 and Appendix D use *sum* of wins / *sum* of losses. This repo names the second one **`gross_profit_factor`** so one name never carries two formulas. → [#7](book-deviations.md#7)

**RSA-PSS**: A digital-signature scheme. Kalshi's API signs `{timestamp_ms}{METHOD}{path}` (**no separator**) with RSA-PSS / SHA-256 / MGF1-SHA256 / salt = digest length, and sends three headers. Older guides showing an email/password login are **obsolete and return 401**. → [`prediction/kalshi_client.py`](../prediction/kalshi_client.py)

**Sharpe ratio**: Risk-adjusted return. Above 1.0 is good; above 1.5 is excellent. **Caveat:** the book applies `√252` (a *daily* annualizer) to *per-trade* 5-day returns, which is wrong in kind and inflates the number. The repo transcribes the formula as printed and tells you why → [#8](book-deviations.md#8).

**Slippage**: The difference between the expected price of a trade and the actual fill. Under $0.05/share on mega-caps; $0.10-$0.30 on mid-caps. **Your backtested returns have to survive it.**

**Stop-loss**: An order that sells a position when it reaches a specified loss level. **ch05's is a *soft* stop in code; if the bot isn't running, nothing fires.** ch08's bracket order is a *hard* stop at the broker.

**Sweep**: An aggressive options order that hits multiple exchanges simultaneously to get filled fast, often signaling urgency. **Tier 1** in the signal hierarchy, the strongest signal in the book.

**Theta**: The rate at which an option loses value each day as it approaches expiration. Time decay.

**Tier (Anthropic API)**: Anthropic organizes API access into usage tiers. Tier 1 (new accounts) starts around **50 RPM** on the Messages API. Higher tiers raise the caps automatically as your spend grows.

**Trailing stop**: A stop-loss that follows the price up but never down, locking in profits. Set one after a position reaches **+2%**. `trail_percent=3.0`, `TimeInForce.GTC`.

**VWAP (Volume-Weighted Average Price)**: The average price weighted by volume traded at each level. The institutional benchmark for execution quality, and the reference point for reading dark-pool prints.

**Walk-forward validation**: Training and testing on rolling time windows to avoid overfitting. Three equal windows; flag any test window that underperforms its training period by more than 10 percentage points. → `walk_forward_validation()` in [`backtester/`](../backtester/backtester.py)

**Wash sale**: Selling a security at a loss and repurchasing it within 30 days, which disallows the tax deduction. **Your bot will absolutely trigger these**: it trades the same tickers repeatedly. Keep a log and give it to your CPA.

---

*Educational software. Not financial advice. See [DISCLAIMER.md](../DISCLAIMER.md).*
