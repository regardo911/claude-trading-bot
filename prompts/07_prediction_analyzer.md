# 07 — Build the prediction-market analyzer

> **Source:** Chapter 7 (The Code: prediction_analyzer.py) · `ch07.md:57`
> Quoted **verbatim** from the manuscript; do not edit the prompt body below.

## The prompt

Open Claude Code in your project directory (`cd ~/ai-trading-bot && claude`) and
paste:

```text
"Build me a prediction-market **analyzer** (read-only; it never submits a bet) for Polymarket and Kalshi.

1. Fetch active Polymarket contracts via the **Gamma Markets API** (`https://gamma-api.polymarket.com/markets?active=true&closed=false&limit=100`); Gamma is the canonical discovery endpoint per Polymarket's developer docs (`docs.polymarket.com/developers/gamma-markets-api`), the CLOB at `clob.polymarket.com` is for orderbook/trading after a market is selected. Public read endpoints don't need auth. Note: Gamma expects string `"true"`/`"false"` for the boolean query params, not Python booleans. The response is a JSON array of market objects with fields `question`, `outcomePrices` (array of stringified floats, index 0 = YES, index 1 = NO), `volume` (stringified float), `clobTokenIds`, `conditionId`, `endDate`, `active`, `closed`. There is **no `current_price` field**; derive the YES probability from `outcomePrices[0]`. For real Polymarket trading you'd use the official `py-clob-client` library (`pip install py-clob-client`) but for read-only analysis a plain `requests.get` works.
2. Filter to 'analyzable' contracts: economic indicators, corporate events, political events with polling data, financial market levels. Skip weather, celebrity gossip, pure-randomness markets.
3. For each contract, ask Claude (in this session, model `claude-sonnet-4-6`) to estimate the true probability **from training-data base rates and structural reasoning ONLY**. This script has no web search, no live polls, no current news; the prompt must explicitly tell Claude "you have no live data, reason only from base rates" and force `confidence="LOW"` on any clearly time-sensitive question (CPI prints, weekly Bitcoin closes, breaking-news political contracts). Return JSON with: estimated_probability, confidence (HIGH/MEDIUM/LOW), reasoning (2-3 sentences explicitly anchored to base rates), key_data_points.
4. Calculate expected value of buying YES vs NO at the current market price. Flag opportunities where the probability gap between Claude's estimate and the market price is >= 10% AND Claude's confidence is HIGH or MEDIUM.
5. Rank by expected value, print the top opportunities, save to `prediction/opportunities_YYYYMMDD.json`. **Do NOT submit any orders.** The script writes the ranked list and exits; I place bets manually through Polymarket's UI (post-KYC) or through `py-clob-client` if I've wired the Polygon wallet myself.

Important context for the build: Polymarket relaunched in the US as a CFTC Designated Contract Market. US users now go through KYC and approved brokers; the no-minimum-bet, log-in-with-crypto-wallet model is gone for US accounts. The CLOB API still serves public market data without auth, but actual trading requires a Polygon-chain wallet with USDC funded through the broker layer; the analyzer reads, it doesn't transact.

Save as `prediction/prediction_analyzer.py` and run it.

Then write `prediction/calibration.py`: a small tracker that records each prediction and its actual outcome, then prints calibration buckets every 30+ resolved contracts."
```

## Expected output schema

```json
{"question": "...", "market_price": 0.22, "estimated_probability": 0.71,
 "confidence": "MEDIUM", "reasoning": "...", "key_data_points": ["..."]}
```
`confidence` is forced to `LOW` on any clearly time-sensitive question (a CPI
print, a weekly Bitcoin close, a breaking-news political contract), because the
saved script has no web search and no live data.

## How deterministic code consumes it

`prediction/prediction_analyzer.py`. `estimate_probability()` parses this;
`calculate_expected_value()` scores it; the opportunity gate needs
`side != SKIP` **and** `abs(gap) >= 0.10` **and** `confidence in [HIGH, MEDIUM]`.

**The script never submits an order and never will.** "The book is not going to
ship an unauthenticated trading bot for a CFTC-regulated venue" (ch07.md:39), and
the build prompt itself says "**Do NOT submit any orders.**" A test in this repo
enforces it.

## Offline behaviour in this repo

Routed to `fixtures/claude_responses/prediction.json`, keyed by the question.
`fixtures/gamma_markets.json` carries `outcomePrices` in **both** shapes (a real
array *and* a JSON-encoded string), so `parse_outcome_prices()` is exercised on
both. It also carries two sub-$10K-volume markets, which the `MIN_VOLUME` filter
(deviation **#1**) drops.

## Cost notes

1 filter call + 1 estimate call per analyzable contract. Pennies to a couple of
dimes per run. The Gamma discovery endpoint is free and needs no auth.

---

*Educational software. Not financial advice. Trading carries substantial risk of
loss. See [DISCLAIMER.md](../DISCLAIMER.md).*
