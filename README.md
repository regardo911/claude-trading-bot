# claude-trading-bot

**The companion code to *Use Claude to Build an AI Trading Bot*.** A screener, an
options-flow trader, a Monte Carlo backtester, a prediction-market analyzer, a
4-agent system, and the risk module that keeps them all alive, one per chapter,
each runnable **offline with zero API keys**.

From [youcanbuildthings.com](https://youcanbuildthings.com/books/ai-trading-bot).

[![CI](https://github.com/regardo911/claude-trading-bot/actions/workflows/ci.yml/badge.svg)](https://github.com/regardo911/claude-trading-bot/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Default: paper mode](https://img.shields.io/badge/default-paper--mode-1baf7a)](#going-live-safely)
![⚠ Not financial advice](https://img.shields.io/badge/%E2%9A%A0%20not-financial%20advice-d03b3b)

---

> ### ⚠️ Educational software. Not financial advice.
>
> This is a **teaching companion, not a production trading system.** Trading carries
> **substantial risk of loss.** Every number this repository prints is computed on
> **synthetic sample data** and predicts nothing about real markets. The code is
> **paper-mode by default**, and no flag or environment variable can change that.
> **Read [DISCLAIMER.md](DISCLAIMER.md) before you run anything.**

---

## → New here? [START_HERE.md](START_HERE.md)

This repo is meant to be read **alongside the book, one chapter at a time**, not
installed and toured like a framework. The learner path is the front door; the full
reference implementation sits behind it.

```bash
git clone https://github.com/regardo911/claude-trading-bot.git
cd claude-trading-bot
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

make check      # environment + imports only — proves the install works
make demo       # the diagnostic: watch the backtester tell 3 strategies apart
```

`make demo` runs the backtester on three synthetic strategies (**no edge**,
**overfit**, and an **edge candidate**) so the first thing you see is the tool
*diagnosing*, not a single green verdict. A trading tool that only ever says "EDGE
CONFIRMED" teaches the wrong reflex.

Then open the lab for the chapter you're on:

**[chapters/](chapters/)**: ch02-setup · ch03-signals · ch04-screener ·
ch05-flow-trader · ch06-backtester · ch07-prediction-markets · ch08-multi-agent ·
ch09-risk · ch10-go-live. Each lab is one page: the prompt → the file Claude
generates → the command → the expected output → the one thing to inspect.

## Why this repo runs offline

Every artifact in the book touches something you pay for: the Anthropic API,
Unusual Whales (a **$50/week floor**), an Alpaca account, a Kalshi private key. A
companion that only ran with all four credentials would be useless to almost
everyone who buys the book, so the default is **inverted**:

**Offline is on unless you turn it off.** Deterministic, seeded, synthetic fixtures
are served by default; each stub answers the exact schema the book's code expects,
and the code paths that run against fixtures are the same ones that run against the
live APIs. Real keys are a lazy opt-in (`CTB_OFFLINE=0`). Live *trading* is a
separate, deliberately awkward, **code-level** opt-in. See below.

## The catalog (the reference implementation)

Behind the labs, each chapter's artifact is a top-level Python module, kept at the
exact path the book prints, so `python screener/screener.py` runs verbatim.

| Item | Ch | What it does | Lab |
|---|---|---|---|
| **Setup** | 02 | Four connections, one script. The 4/4 gate. | [ch02](chapters/ch02-setup/) |
| **Screener** | 04 | Scans the options market → a ranked watchlist | [ch04](chapters/ch04-screener/) |
| **Flow trader** | 05 | Polls flow every 30s; trades only at 70+ confidence | [ch05](chapters/ch05-flow-trader/) |
| **Backtester** | 06 | 1,000 Monte Carlo sims + an overfit check. **No LLM.** | [ch06](chapters/ch06-backtester/) |
| **Prediction** | 07 | Polymarket/Kalshi mispricings. **Read-only. Never bets.** | [ch07](chapters/ch07-prediction-markets/) |
| **Multi-agent** | 08 | Monitor → Analyst → Risk → Executor, with bracket orders | [ch08](chapters/ch08-multi-agent/) |
| **Risk** | 09 | Five hard rules. Quarter-Kelly. A zero floor. **The gatekeeper.** | [ch09](chapters/ch09-risk/) |
| **Go-live** | 10 | The 90-day ladder and its two gates | [ch10](chapters/ch10-go-live/) |

Full map, architecture, and cross-references: **[reference/README.md](reference/README.md)**.
Plus the **[12 verbatim prompts](prompts/)** the book uses as its delivery mechanism
and **[Appendix B's strategy templates](templates/)**.

## Going live safely

**Nothing here trades real money by accident.** It takes three deliberate steps.

1. **Finish the 90-day ladder** ([ch10 lab](chapters/ch10-go-live/)). Thirty days of
   paper trading that clears the Phase-1 gate. Then **$500**, not $5,000. Then the
   capital ladder, with a two-week observation period at each step.
2. **Point the code at the live APIs**: `CTB_OFFLINE=0`, with real keys. This is a
   **data** switch. It does **not** enable trading.
3. **Edit code** and call:
   ```python
   from utils.offline import set_live_mode
   set_live_mode(True, confirm="I_HAVE_REVIEWED_THIS")
   ```

> 🚩 **There is no environment variable and no command-line flag that enables live
> trading. This is intentional.** A test asserts that no flag and no env var can flip
> it. **The prediction-market analyzer has no order-submission path at all**: the
> book refuses to ship an unauthenticated bot for a CFTC-regulated venue, and a test
> enforces it.

## Where this repo differs from the book

**The book is a fixed snapshot; this repo is live.** When they disagree,
**[ERRATA.md](ERRATA.md) is the tie-breaker**: corrections to the printed book
(including bugs in the current printing) and book↔repo reconciliation, each with the
one-line fix. For the full arithmetic behind each one, **[docs/book-deviations.md](docs/book-deviations.md)**
documents every deviation with its chapter cite, pinned by a regression test and
**tagged with a status** (the page tracks the **2nd edition**, manuscript snapshot
2026-07-13; machine-readable: [deviation-manifest.json](docs/deviation-manifest.json)).
Repo changes since launch are in [CHANGELOG.md](CHANGELOG.md); the pitfalls that bit
while building it are in [GOTCHAS.md](GOTCHAS.md).

Still current in the book, and worth your time:

* **The sector cap ignores the position you're about to open** (ch09): its own
  worked example approves a $66,600 NVDA position on a $100K account.
* **Rule 4 promises to *reduce* an oversized position; the code only *blocks* it**
  (ch09). This repo ships the `REDUCE` path.
* **The gatekeeper can't take a custom stop width** (ch09), so the chapter's own
  "widen TSLA to 5%" advice is unreachable through it.
* Plus the three Chapter 3 rules that exist in no code, the dead `MIN_VOLUME`
  constant, and the `suggested_bet` formula that contradicts itself three ways.

**Two former critical bugs (the Monte Carlo sampler and `check_exits()` covering
shorts) are now resolved in the 2nd edition**, and this repo already matched. They
stay on the page as historical notes, marked *resolved in book*.

## Configuration

**Every variable is optional. None are required for `make check`, `make demo`, the
tests, or CI.** `CTB_OFFLINE=0` swaps in the live read APIs; `ANTHROPIC_API_KEY`,
`UW_API_KEY` (paid, $50/wk floor), `ALPACA_*`, and `KALSHI_*` each turn on their
own live surface. See [`.env.example`](.env.example). `.env` is gitignored;
**no PEM file is ever committed**: the Kalshi tests generate a throwaway keypair
in-process. Install profiles (`.[live]`, `.[viz]`, `.[all]`) are in
[reference/README.md](reference/README.md).

## Testing & CI

```bash
make test     # full suite, offline, no keys
make lint     # ruff
make tour     # every bot end to end, clearly synthetic
```

CI runs on Python 3.11 / 3.12 / 3.13, installs **core deps only** (which is how the
zero-key claim is proven on every push), then lints, runs the full suite, and
smoke-tests both `make demo` and the full tour. **No secrets in CI.** The suite
includes a no-network guard, a "safe mode cannot be flipped by a flag" test, the
book's worked examples as assertions, the Kalshi signature against a throwaway
keypair, and a regression test for every deviation.

## Contributing

**Fixes are very welcome. New features are out of scope.** This repo mirrors the book
on purpose: if it grows a bot the book doesn't have, it stops being a companion. A
**new** contradiction between the book and its own code is the most valuable issue
you can open. See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT. See [LICENSE](LICENSE).

---

*Educational software for learning and research. Not financial advice, not an offer,
and not a recommendation to trade anything. Trading carries substantial risk of loss.
Any figures produced by this code run on synthetic sample data and do not predict
real results. Paper mode is the default. Consult a licensed financial professional
before acting.*
