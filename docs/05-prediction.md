# 5. Prediction markets: where Claude's edge is widest (Chapter 7)

![Scatter plot of Claude's probability estimate against the market-implied probability, with a 45-degree parity line and a shaded ±10-percentage-point no-bet band. One green highlighted point sits far above the band (a Supreme Court ruling contract priced at 22% that Claude estimates at 71%), annotated BUY YES, bet $24.50. Hollow grey points are LOW-confidence time-sensitive contracts, excluded. Solid blue points sit inside the band and are not bet.](images/05-prediction.png)

*Computed by running `prediction_analyzer.py`'s real functions against the bundled synthetic Gamma fixture (regenerate with `python tools/generate_docs_charts.py`).*

## ⚠️ Read-only. It never submits a bet. It never will.

> "The book is not going to ship an unauthenticated trading bot for a
> CFTC-regulated venue." (ch07.md:39)
>
> "**Do NOT submit any orders.**" (ch07.md:64, the build prompt itself)

This repo honors that refusal. `prediction_analyzer.py` imports nothing that can
place an order, contains no `submit_order` / `requests.post` / CLOB write path, and
[a test](../tests/test_safety.py) enforces that it never grows one.

The analyzer decides **where the edge is**. *You* place the bet, through
Polymarket's UI after KYC, or via `py-clob-client` if you wired a Polygon wallet
yourself. Check your state's legal status first.

## Why Claude wins here

In stock trading, Claude competes against hedge funds running their own AI. In
prediction markets, it competes against people who bet $50 based on a tweet they
read at lunch. **The edge is wider, the competition is weaker, and the data
advantage is enormous.**

Three specific advantages: **data processing** (most contracts have objectively
analyzable components), **bias correction** (people bet on what they *want* to
happen; Claude has no team), and **multi-source synthesis**.

## The rules

| Constant | Value |
|---|---|
| `POLYMARKET_GAMMA` | `https://gamma-api.polymarket.com` (**discovery**, no auth) |
| `MIN_PROBABILITY_GAP` | `0.10` |
| `MAX_BET_SIZE` | `50` (**a coefficient, not a cap. See the erratum.**) |
| `MIN_VOLUME` | `10000` (**enforced here; a dead constant in the book**) |
| opportunity gate | `side != SKIP` **AND** `abs(gap) >= 0.10` **AND** `confidence in [HIGH, MEDIUM]` |

**Expected value:** `ev_yes = (prob × 1.0) − price` · `ev_no = ((1 − prob) × 1.0) − (1 − price)`

**Gamma, not CLOB.** Gamma at `gamma-api.polymarket.com` is the canonical
*discovery* endpoint. The CLOB at `clob.polymarket.com` is for orderbook and
trading. **Mixing the two is the number-one Polymarket integration error.**

**There is no `current_price` field.** The YES probability is `outcomePrices[0]`,
and `outcomePrices` arrives as a **JSON-encoded string** in the docs and as a **real
array** in live responses. `parse_outcome_prices()` handles both, and the bundled
fixture contains both shapes so it's actually exercised.

Gamma expects string `"true"`/`"false"` for boolean query params, not Python
booleans, and returns a **JSON array directly**, not a `{"data": [...]}` wrapper.

## Two deviations

**[#1](book-deviations.md#1): `MIN_VOLUME` is declared in the chapter and
referenced by nothing.** Appendix B lists it as a live tunable. This repo actually
filters on it; without it the analyzer scores $0-volume markets you could never get
filled in.

**[#9](book-deviations.md#9): `suggested_bet` is a three-way contradiction** between
the code, the prose, and the two printed examples. **No single formula produces both
printed examples.** This repo ships the code as printed: the only formula that
reproduces any printed output exactly.

> ### The erratum you need to know
>
> `suggested_bet = min(MAX_BET_SIZE, MAX_BET_SIZE * abs(gap))`
>
> The `min()` binds **only at a 100% gap**. So **`MAX_BET_SIZE` is a scaling
> coefficient, not a cap**, contradicting both its own comment and the word "cap" in
> the prose. A qualifying **10% gap sizes a $5 bet**, not the $25 the prose promises.
> A realistically large 49% gap sizes $24.50. The $50 is unreachable in practice.

## How to run it

```bash
python prediction/prediction_analyzer.py
python prediction/calibration.py           # after 30+ resolved contracts
```

## Worked example (offline, real output)

```
Found 11 active markets.
Dropped 2 market(s) below the $10,000 volume floor.
Kept 7 analyzable contracts.

============================================================
PREDICTION MARKET OPPORTUNITIES (base-rate reasoning only)
============================================================

1. Will the Supreme Court issue a ruling in Case X before the end of this
   Market: 22% | Our estimate: 71% | Gap: +49%
   Side: BUY YES | EV: $0.49/share | Confidence: MEDIUM
   Reasoning: The historical base rate for the Court issuing a ruling on a case
   granted certiorari within the same term is very high... The market price
   appears to confuse "ruling issued" with "ruling in the petitioner's favor";
   the question text only requires the former.
   Suggested bet: $24.50

This script does not place bets.
```

## "No contracts found with sufficient edge today" is a **pass**, not a failure

The saved script has **no web search, no live polls, and no current news.** It
reasons from training-data base rates and structural factors only, and the prompt
**forces `confidence="LOW"`** on anything clearly time-sensitive: a CPI print, a
weekly Bitcoin close, a breaking-news political contract.

So most days the correct output is *nothing*. Watch the offline run: the CPI, the
Bitcoin close and the S&P Friday contracts all get LOW and drop out. **Without live
data, the model has no business pretending to know the current state.**

A coherent passing opportunity cites a **base rate**, names a **structural factor**,
and explains *why* the market is mispriced. If the reasoning says "the gap is noise",
that is a LOW-confidence judgment dressed up as MEDIUM, and the filter should have
dropped it.

## For live-data estimates: use Claude Code interactively

The standalone script is the always-on **filter**. The interactive session is the
always-current **researcher**.

1. The script writes `prediction/markets.json`.
2. Open Claude Code and paste
   [`prompts/09_live_data_estimates.md`](../prompts/09_live_data_estimates.md).
   Claude Code has web search: it fetches real sources and writes
   `prediction/estimates.json` with **cited, dated** references.
3. `rank_estimates_file()` runs the same EV math over it.

**Do not paste that prompt into a `claude.messages.create()` call.** The vanilla
Messages API has no web search, and Claude will fabricate the citations.

## Where the edge actually is

| Tier | Category | Edge |
|---|---|---|
| **1** | Economic data (CPI, jobs, GDP, Fed) | **8-15pp** |
| **2** | Corporate earnings beats/misses | 5-10pp |
| **3** | Political events with polling | 3-20pp (wildly variable) |
| **4** | Crypto price targets | 2-5pp at best |
| **—** | Weather, gossip, sports without models | **none. Skip entirely.** |

## Kalshi

`prediction/kalshi_client.py` implements the RSA-PSS auth flow: payload
`{timestamp_ms}{METHOD}{path}` concatenated with **no separator**, signed RSA-PSS /
SHA-256 / MGF1-SHA256 / salt = digest length, sent as `KALSHI-ACCESS-KEY`,
`KALSHI-ACCESS-SIGNATURE` (base64) and `KALSHI-ACCESS-TIMESTAMP` (ms).

If you've seen an older guide with a `kalshi_login(email, password)` POST, that
pattern is **obsolete and returns 401**.

`place_kalshi_order()` exists because the chapter's prompt names it, and it
**refuses to run** unless you have edited code and called
`set_live_mode(True, confirm="I_HAVE_REVIEWED_THIS")`. The analyzer does not import
it. **No PEM file is ever committed to this repo**: the test suite generates a
throwaway keypair in-process.

## Position sizing

Your maximum loss is always the amount you bet. No margin calls, no overnight gap
risk, no stop-loss needed. **This makes prediction markets ideal for learning:** bet
$10-$50 across 5-10 contracts and a total wipeout costs $100-$500.

## Regulatory

Polymarket relaunched in the US as a **CFTC Designated Contract Market**. US users
complete KYC and trade through approved brokers. The no-minimum-bet,
log-in-with-a-crypto-wallet model is gone for US accounts. **Nevada, Tennessee and
Massachusetts have open legal actions.** Check your state before depositing.

Kalshi has been a CFTC DCM since 2021. KYC required, $1 minimum deposit.

## The prompts

* [`prompts/07_prediction_analyzer.md`](../prompts/07_prediction_analyzer.md)
* [`prompts/08_kalshi_client.md`](../prompts/08_kalshi_client.md)
* [`prompts/09_live_data_estimates.md`](../prompts/09_live_data_estimates.md)

---

*Illustrative results on synthetic sample data. Not indicative of real or historical performance. Educational software. Not financial advice. See [DISCLAIMER.md](../DISCLAIMER.md).*
