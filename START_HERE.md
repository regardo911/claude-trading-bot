# Start here

This repo is the companion to *Use Claude to Build an AI Trading Bot*. It is built
to be **read alongside the book, one chapter at a time**, not installed and toured
like a framework.

The book's model is simple: you paste a prompt into Claude Code, Claude writes the
Python, you run it, you read the output, you learn. This repo gives you, for each
chapter, the finished artifact so you can check yours against a working one, and
run it **offline, with zero API keys**, so you can learn the mechanics before you
pay for a single data feed.

## The 15-minute path

```bash
git clone https://github.com/regardo911/claude-trading-bot.git
cd claude-trading-bot
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

make check      # 1. environment + imports only — proves the install works
make demo       # 2. the diagnostic: watch the backtester tell 3 strategies apart
```

Then open the lab for whichever chapter you're on:

| You're on… | Open |
|---|---|
| Ch 2: setup & connections | [chapters/ch02-setup](chapters/ch02-setup/) |
| Ch 3: the signal hierarchy | [chapters/ch03-signals](chapters/ch03-signals/) |
| Ch 4: the screener | [chapters/ch04-screener](chapters/ch04-screener/) |
| Ch 5: the flow trader | [chapters/ch05-flow-trader](chapters/ch05-flow-trader/) |
| Ch 6: the backtester | [chapters/ch06-backtester](chapters/ch06-backtester/) |
| Ch 7: prediction markets | [chapters/ch07-prediction-markets](chapters/ch07-prediction-markets/) |
| Ch 8: the multi-agent system | [chapters/ch08-multi-agent](chapters/ch08-multi-agent/) |
| Ch 9: risk management | [chapters/ch09-risk](chapters/ch09-risk/) |
| Ch 10: going live | [chapters/ch10-go-live](chapters/ch10-go-live/) |

Each lab is one page: **the prompt → the file Claude generates → the command → the
expected output → the one thing to inspect.** Nothing more to hold in your head.

## What's where

- **[chapters/](chapters/)**: the learner path. Start here, follow the book.
- **[prompts/](prompts/)**: the 12 `PASTE TO CLAUDE CODE` prompts, verbatim.
- **[examples/](examples/)**: short runnable examples that isolate a single idea.
- **[reference/](reference/README.md)**: the full reference implementation and its
  docs. You do **not** need to read the whole package to get your first win.
- **[ERRATA.md](ERRATA.md)**: the book-vs-repo tie-breaker: corrections to the
  printed book (including bugs in the current printing) and the one-line fix for each.
  Read it the moment something you typed from the book doesn't behave.
  ([docs/book-deviations.md](docs/book-deviations.md) has the full arithmetic.)
- **[GOTCHAS.md](GOTCHAS.md)**: the pitfalls that actually bit while building this.

## Two things to know before you run anything

1. **Offline is the default.** No key, no `.env`, no network, no broker account:
   `make check` and `make demo` still work. Every number is computed on synthetic
   fixtures and **predicts nothing about real markets.**
2. **Nothing trades real money by accident.** Live trading is a deliberate,
   code-level opt-in that no flag or environment variable can trigger. Read
   [DISCLAIMER.md](DISCLAIMER.md) before you go anywhere near a real account.

*Educational software. Not financial advice.*
