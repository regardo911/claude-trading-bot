# Reference implementation

This is the layer **behind** the [chapter labs](../chapters/). You do not need to
read it to get your first win. Start with [START_HERE.md](../START_HERE.md) and the
labs. Come here when you want the whole picture: how a module is built, why a
constant is what it is, or where the repo and the book diverge.

## The eight modules

Each catalog item is a top-level Python package (kept at the exact path the book
prints, so `python screener/screener.py` and friends work verbatim):

| Module | Ch | Reference doc |
|---|---|---|
| [`setup/`](../setup/) | 02 | [docs/01-setup.md](../docs/01-setup.md) |
| [`screener/`](../screener/) | 04 | [docs/02-screener.md](../docs/02-screener.md) |
| [`flow_trader/`](../flow_trader/) | 05 | [docs/03-flow-trader.md](../docs/03-flow-trader.md) |
| [`backtester/`](../backtester/) | 06 | [docs/04-backtester.md](../docs/04-backtester.md) |
| [`prediction/`](../prediction/) | 07 | [docs/05-prediction.md](../docs/05-prediction.md) |
| [`multi_agent/`](../multi_agent/) | 08 | [docs/06-multi-agent.md](../docs/06-multi-agent.md) |
| [`risk/`](../risk/) | 09 | [docs/07-risk.md](../docs/07-risk.md) |
| [`tracking/`](../tracking/) | 10 | [docs/08-going-live.md](../docs/08-going-live.md) |

Shared plumbing: [`utils/`](../utils/), the offline switch (`utils/offline.py`),
the signal rules (`utils/signals.py`), and path helpers.

## Cross-cutting references

- **[docs/architecture.md](../docs/architecture.md)**: the two data-flow lanes (MCP
  vs saved-script REST) and the third that only *looks* like it works.
- **[docs/book-deviations.md](../docs/book-deviations.md)**: every place this repo
  differs from the book, each tagged with a status (resolved in book / still current
  / repo improvement / not a bug). Machine-readable:
  [deviation-manifest.json](../docs/deviation-manifest.json).
- **[docs/glossary.md](../docs/glossary.md)**: the vocabulary.
- **[docs/troubleshooting.md](../docs/troubleshooting.md)**: when something breaks.
- **[docs/prompts.md](../docs/prompts.md)**: the 12 prompts, indexed.

## How it stays honest

- **Offline-first:** every module degrades to a deterministic synthetic fixture when
  its paid API is absent. The default path opens no socket. CI installs core deps
  only, so the zero-key claim is proven on every push, not asserted.
- **Every figure is computed** by importing these real modules and running the actual
  functions the docs teach, never hand-drawn.
- **Every deviation is pinned** by a regression test in
  [`tests/`](../tests/), so a future "fix" back to the book's printed code goes red.
