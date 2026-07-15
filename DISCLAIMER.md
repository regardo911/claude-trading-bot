# Disclaimer

> ## ⚠️ Not financial advice.
>
> This repository is **educational software** that accompanies the book *Use
> Claude to Build an AI Trading Bot*. It is provided for learning and research
> only. Nothing here is financial, investment, or trading advice, and nothing
> here is a recommendation to buy, sell, or trade any security, option,
> contract, or event contract. Trading carries **substantial risk of loss**, and
> you can lose more than you deposit. Any figures produced by this code on
> synthetic sample data do **not** predict real results and are **not**
> indicative of any real or historical performance. The authors and contributors
> make **no warranty** of any kind and accept **no liability** for any loss
> arising from use of this software. **The software defaults to paper (simulated)
> mode; enabling any live behavior is entirely at your own risk.** You are solely
> responsible for your own decisions and for complying with the laws,
> regulations, and third-party terms that apply to you, including, where
> relevant, pattern-day-trading rules and the state-by-state legality of event
> contracts. Consult a licensed financial professional before acting.

## The book says it more bluntly

> "Trading is risky. Bots fail. Past results don't predict future ones. This book
> is for educational purposes only and is not financial advice."
> (ch01)

> "I'm a technologist who builds trading systems, not a licensed financial
> advisor."
> (ch01)

## What "synthetic" means here

Every number this repository prints (every win rate, every Sharpe ratio, every
Monte Carlo percentile, every chart in `docs/images/`) is computed by this
repository's own code against **committed synthetic fixtures**. The fixtures are
invented. The tickers are real, but the prices, the flow events, and the outcomes
are not. Nothing in this repo was ever traded, on paper or otherwise.

Every generated figure carries the stamp *"synthetic sample data — illustrative
mechanics only"*, and every run that touches the fixtures announces itself on
stderr. If you ever see a number here presented as a real or historical result,
that is a bug. Please open an issue.

The repo also does **not** reprint the book's own illustrative Monte Carlo figures
as if this code produced them. See [`docs/book-deviations.md`](docs/book-deviations.md).

## What is paper, and what is not

* **Everything is paper by default.** `paper=True` on every broker client. With no
  `.env` at all, the code cannot reach a broker: it talks to an in-memory stub.
* Setting `CTB_OFFLINE=0` points the code at the **live read APIs** (market data,
  the Anthropic Messages API). It does **not** enable live trading, and it cannot.
* Live, real-money trading requires an explicit **code-level** opt-in that you have
  to write yourself:

  ```python
  from utils.offline import set_live_mode
  set_live_mode(True, confirm="I_HAVE_REVIEWED_THIS")
  ```

  There is deliberately no environment variable and no command-line flag for this.
  An env var is one stray `export` away from trading your savings.

* The **prediction-market analyzer has no order-submission path at all** and never
  will. The book refuses to ship an unauthenticated trading bot for a
  CFTC-regulated venue, and this repo honors that refusal. A test enforces it.

## Regulatory notes you are responsible for

* **Pattern Day Trader.** FINRA's new intraday margin rule replaces the old PDT framework on June 4,
  2026. Brokers have until October 20, 2027 to fully switch over. Your broker may continue applying the old
  $25,000 restriction during the transition. **Check your specific broker.**
* **Event contracts.** Polymarket relaunched in the US as a CFTC Designated
  Contract Market; US users complete KYC and trade through approved brokers.
  Nevada, Tennessee and Massachusetts have open legal actions. **Check your state's
  current status before depositing.**
* **Taxes.** Bots trade the same tickers repeatedly and will trigger wash sales.
  Talk to a CPA who works with active traders before you go live.

## Before you risk a dollar

Finish the 90-day ladder in Chapter 10. Thirty days of paper trading that clears
the Phase-1 gate. Then **$500**, not $5,000. Then the capital ladder, with a
two-week observation period at each step.

The people who post "I lost everything to my trading bot" are almost never the
people whose strategy was wrong. They are the people who skipped this part.
